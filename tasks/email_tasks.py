"""
Celery tasks for email processing
All tasks are synchronous - no async/await
"""

from celery import shared_task
from datetime import datetime
import json
from typing import Dict, Any, Optional

from models.agent_task import AgentTask
from services.email_parser import EmailParser
from services.task_dispatcher import task_dispatcher
from utils.logging_config import get_logger, log_email_task, LogContext

logger = get_logger(__name__)


@shared_task(bind=True, max_retries=3)
def process_email_event(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process email webhook event in background
    This is called after webhook validation
    
    Args:
        email_data: Validated email data from webhook
        
    Returns:
        Processing result with task details
    """
    try:
        with LogContext(message_id=email_data.get('message_id', 'unknown')):
            logger.info("Processing email event")
        
        # Parse email into structured task
        parser = EmailParser()
        agent_task = parser.parse_email(email_data)
        
        log_email_task(agent_task.task_id, "created", title=agent_task.title)
        
        # Store in Supermemory
        memory_id = store_email_in_memory.apply_async(
            args=[email_data, agent_task.to_dict()],
            countdown=1  # Small delay to ensure task is created
        ).id
        
        # Dispatch to agents if it's an actionable task
        if agent_task.agent_assignment and agent_task.priority.value in ["urgent", "high"]:
            dispatch_result = dispatch_email_task.apply_async(
                args=[agent_task.to_dict()],
                countdown=2
            ).id
            logger.info("High priority task dispatched", dispatch_task_id=dispatch_result)
        else:
            dispatch_result = None
            logger.info("Task queued for manual review", task_id=agent_task.task_id)
        
        # Send notification about new email task
        notify_email_processed.apply_async(
            args=[agent_task.to_dict(), "success"],
            countdown=3
        )
        
        return {
            "status": "success",
            "task_id": agent_task.task_id,
            "email_message_id": email_data.get("message_id"),
            "task_type": agent_task.task_type.value,
            "priority": agent_task.priority.value,
            "assigned_to": agent_task.agent_assignment.primary_agent if agent_task.agent_assignment else None,
            "memory_task_id": memory_id,
            "dispatch_task_id": dispatch_result,
            "processed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to process email event", error=str(e), message_id=email_data.get('message_id'))
        
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        self.retry(exc=e, countdown=countdown)


@shared_task(bind=True, max_retries=3)
def store_email_in_memory(self, email_data: Dict[str, Any], task_data: Dict[str, Any]) -> str:
    """
    Store email and parsed task in Supermemory
    
    Args:
        email_data: Original email data
        task_data: Parsed task data
        
    Returns:
        Memory ID
    """
    try:
        # Import here to avoid circular imports
        from services.supermemory_service import get_supermemory_service, Memory
        
        memory_service = get_supermemory_service()
        
        # Create memory object
        memory = Memory(
            content=f"Email Task: {task_data.get('title', 'Untitled')}\n\n{task_data.get('description', '')}",
            metadata={
                'type': 'email_task',
                'email_data': email_data,
                'task_data': task_data,
                'from': email_data.get('from'),
                'subject': email_data.get('subject'),
                'message_id': email_data.get('message_id'),
                'task_id': task_data.get('task_id'),
                'priority': task_data.get('priority'),
                'task_type': task_data.get('task_type')
            },
            agent_id='email_agent',
            conversation_id=f"email_tasks_{datetime.now().strftime('%Y%m%d')}",
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Store synchronously (Supermemory service should handle any async internally)
        result = memory_service.add_memory_sync(memory)
        memory_id = result.get('id', 'unknown')
        
        logger.info(f"Stored email task in memory: {memory_id}")
        return memory_id
        
    except Exception as e:
        logger.error(f"Failed to store in Supermemory: {str(e)}")
        # Retry with backoff
        self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def dispatch_email_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch parsed email task to agents
    
    Args:
        task_data: Task dictionary
        
    Returns:
        Dispatch result
    """
    try:
        # Reconstruct AgentTask from data
        from models.agent_task import AgentTask, TaskType, TaskPriority, AgentAssignment
        
        # Create task with required fields
        agent_task = AgentTask(
            task_id=task_data.get('task_id'),
            title=task_data.get('title', 'Email Task'),
            description=task_data.get('description', ''),
            task_type=TaskType[task_data.get('task_type', 'GENERAL')],
            priority=TaskPriority[task_data.get('priority', 'MEDIUM')]
        )
        
        # Set agent assignment if present
        if task_data.get('agent_assignment'):
            assignment_data = task_data['agent_assignment']
            agent_task.agent_assignment = AgentAssignment(
                primary_agent=assignment_data.get('primary_agent'),
                supporting_agents=assignment_data.get('supporting_agents', []),
                reason=assignment_data.get('reason', '')
            )
        
        # Dispatch the task
        result = task_dispatcher.dispatch_task(agent_task)
        
        logger.info(f"Task {agent_task.task_id} dispatched: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to dispatch task: {str(e)}")
        self.retry(exc=e, countdown=60)


@shared_task
def notify_email_processed(task_data: Dict[str, Any], status: str) -> bool:
    """
    Send notification about processed email
    
    Args:
        task_data: Parsed task data
        status: Processing status
        
    Returns:
        Success boolean
    """
    try:
        # Import notification service
        from services.notification_service import NotificationService
        
        notifier = NotificationService()
        
        # Create notification message
        if status == "success":
            title = f"📧 New Email Task: {task_data.get('priority', 'MEDIUM')} Priority"
            message = (
                f"Task: {task_data.get('title', 'Untitled')}\n"
                f"Type: {task_data.get('task_type', 'Unknown')}\n"
                f"Assigned to: {task_data.get('agent_assignment', {}).get('primary_agent', 'Unassigned')}\n"
                f"Task ID: {task_data.get('task_id', 'Unknown')}"
            )
        else:
            title = "❌ Email Processing Failed"
            message = f"Failed to process email task: {task_data.get('task_id', 'Unknown')}"
        
        # Send notification
        notifier.send_sync(
            title=title,
            message=message,
            priority=task_data.get('priority', 'medium').lower(),
            tags=['email', 'task', status]
        )
        
        logger.info(f"Notification sent for task {task_data.get('task_id')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")
        return False


@shared_task
def search_email_tasks(query: str, filters: Optional[Dict[str, Any]] = None) -> list:
    """
    Search for email tasks in Supermemory
    
    Args:
        query: Search query
        filters: Optional filters
        
    Returns:
        List of matching tasks
    """
    try:
        from services.supermemory_service import get_supermemory_service
        
        memory_service = get_supermemory_service()
        
        # Build search filters
        search_filters = {
            'agent_id': 'email_agent',
            'metadata.type': 'email_task'
        }
        
        if filters:
            if 'priority' in filters:
                search_filters['metadata.priority'] = filters['priority']
            if 'task_type' in filters:
                search_filters['metadata.task_type'] = filters['task_type']
            if 'date_from' in filters:
                search_filters['timestamp_gte'] = filters['date_from']
        
        # Search synchronously
        results = memory_service.search_memories_sync(
            query=query,
            filters=search_filters,
            limit=filters.get('limit', 20) if filters else 20
        )
        
        # Extract task data from memories
        tasks = []
        for memory in results:
            task_data = memory.get('metadata', {}).get('task_data', {})
            if task_data:
                tasks.append(task_data)
        
        logger.info(f"Found {len(tasks)} email tasks matching query: {query}")
        return tasks
        
    except Exception as e:
        logger.error(f"Email task search failed: {str(e)}")
        return []


@shared_task
def cleanup_old_email_tasks(days: int = 30) -> Dict[str, int]:
    """
    Clean up old email tasks from memory
    
    Args:
        days: Tasks older than this many days will be archived
        
    Returns:
        Cleanup statistics
    """
    try:
        from services.supermemory_service import get_supermemory_service
        from datetime import timedelta
        
        memory_service = get_supermemory_service()
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Search for old tasks
        old_tasks = memory_service.search_memories_sync(
            query="",
            filters={
                'agent_id': 'email_agent',
                'metadata.type': 'email_task',
                'timestamp_lt': cutoff_date
            },
            limit=1000
        )
        
        archived_count = 0
        error_count = 0
        
        for memory in old_tasks:
            try:
                # Archive or delete based on your policy
                memory_id = memory.get('id')
                if memory_id:
                    # For now, just log - implement actual archival based on your needs
                    logger.info(f"Would archive memory: {memory_id}")
                    archived_count += 1
            except Exception as e:
                logger.error(f"Failed to process memory for archival: {str(e)}")
                error_count += 1
        
        logger.info(f"Cleanup complete: {archived_count} archived, {error_count} errors")
        
        return {
            "archived": archived_count,
            "errors": error_count,
            "total_processed": len(old_tasks)
        }
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        return {"error": str(e)}