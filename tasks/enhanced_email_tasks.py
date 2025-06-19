"""
Enhanced Celery tasks for email processing with agent integration
Connects email processing to multi-agent workflow
"""

from celery import shared_task, Task
from datetime import datetime
import json
from typing import Dict, Any, Optional, List

from services.email_agent_integration import get_email_integration
from services.db_task_storage import get_task_storage, log_action
from services.multi_agent_executor import MultiAgentExecutor
from utils.logging_config import get_logger, log_email_task, LogContext

logger = get_logger(__name__)

class EmailAgentTask(Task):
    """Base task class with database connection management"""
    _email_integration = None
    _task_storage = None
    
    @property
    def email_integration(self):
        if self._email_integration is None:
            self._email_integration = get_email_integration()
        return self._email_integration
    
    @property
    def task_storage(self):
        if self._task_storage is None:
            self._task_storage = get_task_storage()
        return self._task_storage

@shared_task(bind=True, base=EmailAgentTask, max_retries=3)
def process_email_task(self, task_id: str, email_data: Dict[str, Any], 
                      parsed_task: Dict[str, Any], agents: List[str]) -> Dict[str, Any]:
    """
    Process email through multi-agent workflow
    This is the main task that orchestrates the entire email → agent → response pipeline
    
    Args:
        task_id: Database task ID
        email_data: Original email data
        parsed_task: Parsed task information
        agents: List of agent IDs to involve
        
    Returns:
        Processing result with agent responses
    """
    try:
        with LogContext(task_id=task_id, email_from=email_data.get('from')):
            logger.info("Starting email agent workflow")
        
        # Update task status
        self.task_storage.update_task(
            task_id,
            status='running',
            current_phase='Initializing agent workflow'
        )
        
        # 1. Prepare agent request
        task_description = parsed_task.get('description', email_data.get('subject', ''))
        context = {
            'source': 'email',
            'sender': email_data.get('from'),
            'subject': email_data.get('subject'),
            'priority': parsed_task.get('priority', 'medium'),
            'requirements': parsed_task.get('requirements', []),
            'deadline': parsed_task.get('deadline'),
            'email_body': email_data.get('body_plain', email_data.get('body', ''))
        }
        
        # 2. Execute agents sequentially
        executor = MultiAgentExecutor()
        agent_results = []
        
        for idx, agent_id in enumerate(agents):
            try:
                # Update phase
                self.task_storage.update_task(
                    task_id,
                    current_phase=f'Processing with {agent_id}',
                    progress=int((idx / len(agents)) * 80)  # 0-80% for agents
                )
                
                # Call agent
                logger.info(f"Calling agent {agent_id} for task {task_id}")
                
                # Get agent response (simulated for now - replace with actual agent call)
                agent_response = call_agent_for_email.apply_async(
                    args=[agent_id, task_description, context, task_id],
                    queue=f'agent_{agent_id}'  # Route to specific agent queue if available
                ).get(timeout=60)  # Wait up to 60 seconds
                
                agent_results.append({
                    'agent_id': agent_id,
                    'response': agent_response,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                # Store conversation
                from services.db_task_storage import add_conversation
                add_conversation(
                    task_id=task_id,
                    agent_id=agent_id,
                    role='assistant',
                    content=agent_response.get('content', ''),
                    metadata=agent_response.get('metadata', {})
                )
                
            except Exception as e:
                logger.error(f"Agent {agent_id} failed: {e}")
                agent_results.append({
                    'agent_id': agent_id,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # 3. Generate summary
        self.task_storage.update_task(
            task_id,
            current_phase='Generating summary',
            progress=85
        )
        
        summary = generate_email_summary.apply_async(
            args=[task_id, agent_results]
        ).get(timeout=30)
        
        # 4. Generate and send response
        self.task_storage.update_task(
            task_id,
            current_phase='Sending response',
            progress=95
        )
        
        response_result = send_email_response.apply_async(
            args=[task_id, email_data, summary, agent_results]
        ).get(timeout=30)
        
        # 5. Complete task
        self.task_storage.update_task(
            task_id,
            status='completed',
            progress=100,
            current_phase='Complete',
            summary=summary,
            results={
                'agents_called': len(agents),
                'agents_responded': len([r for r in agent_results if 'response' in r]),
                'response_sent': response_result.get('success', False),
                'email_id': response_result.get('email_id')
            }
        )
        
        log_email_task(task_id, "completed", 
                      message=f"Email processed with {len(agents)} agents")
        
        return {
            'success': True,
            'task_id': task_id,
            'agents_involved': agents,
            'summary': summary,
            'response_sent': response_result.get('success', False)
        }
        
    except Exception as e:
        logger.error(f"Email task failed: {e}")
        
        # Update task with error
        self.task_storage.update_task(
            task_id,
            status='error',
            error_message=str(e),
            current_phase='Failed'
        )
        
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        self.retry(exc=e, countdown=countdown)

@shared_task(bind=True, base=EmailAgentTask)
def call_agent_for_email(self, agent_id: str, task_description: str, 
                        context: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """
    Call a specific agent for email processing
    
    Args:
        agent_id: ID of the agent to call
        task_description: Task description
        context: Email context information
        task_id: Parent task ID
        
    Returns:
        Agent response
    """
    try:
        # Log agent call
        log_action(
            action_type='agent_call',
            action_description=f'Calling {agent_id} for email task',
            agent_id=agent_id,
            task_id=task_id,
            metadata={'context': context}
        )
        
        # Build agent prompt
        prompt = f"""You are processing an email-based request.

Email Context:
- From: {context.get('sender', 'Unknown')}
- Subject: {context.get('subject', 'No subject')}
- Priority: {context.get('priority', 'medium')}

Task: {task_description}

Email Content:
{context.get('email_body', 'No content')}

Please provide a helpful response addressing the email sender's request."""

        # Call agent via OpenRouter or your agent system
        # This is a placeholder - integrate with your actual agent system
        from scripts.start_with_api import call_openrouter_api, AGENTS
        
        agent_config = AGENTS.get(agent_id, {})
        system_prompt = agent_config.get('system_prompt', f'You are {agent_id}, a helpful AI assistant.')
        model = agent_config.get('model', 'openai/gpt-4')
        
        response = call_openrouter_api(
            message=prompt,
            agent_context=system_prompt,
            model=model
        )
        
        return {
            'agent_id': agent_id,
            'content': response,
            'model_used': model,
            'metadata': {
                'context': context,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Agent {agent_id} call failed: {e}")
        raise

@shared_task(bind=True, base=EmailAgentTask)
def generate_email_summary(self, task_id: str, agent_results: List[Dict]) -> str:
    """
    Generate executive summary from agent responses
    
    Args:
        task_id: Task ID
        agent_results: List of agent responses
        
    Returns:
        Summary text
    """
    try:
        # Extract successful responses
        responses = []
        for result in agent_results:
            if 'response' in result and result['response'].get('content'):
                responses.append({
                    'agent': result['agent_id'],
                    'content': result['response']['content']
                })
        
        if not responses:
            return "No agent responses were generated for this email."
        
        # Build summary prompt
        summary_prompt = "Based on the following agent responses to an email request, provide a concise executive summary:\n\n"
        
        for resp in responses:
            summary_prompt += f"Agent {resp['agent']}:\n{resp['content'][:500]}...\n\n"
        
        summary_prompt += "Provide a brief, actionable summary that could be sent as an email response."
        
        # Generate summary
        from scripts.start_with_api import call_openrouter_api
        
        summary = call_openrouter_api(
            message=summary_prompt,
            agent_context="You are an executive assistant summarizing team responses.",
            model="openai/gpt-4"
        )
        
        # Store summary in conversation history
        from services.db_task_storage import add_conversation
        add_conversation(
            task_id=task_id,
            agent_id='summary_agent',
            role='assistant',
            content=summary,
            metadata={'type': 'executive_summary'}
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return "Summary generation failed."

@shared_task(bind=True, base=EmailAgentTask)
def send_email_response(self, task_id: str, email_data: Dict[str, Any], 
                       summary: str, agent_results: List[Dict]) -> Dict[str, Any]:
    """
    Send email response based on agent results
    
    Args:
        task_id: Task ID
        email_data: Original email data
        summary: Executive summary
        agent_results: Agent responses
        
    Returns:
        Send result
    """
    try:
        # Check if we should send a response
        if email_data.get('no_reply', False):
            logger.info("No-reply flag set, skipping response")
            return {'success': True, 'skipped': True}
        
        # Build response email
        sender_email = email_data.get('from', '')
        sender_name = sender_email.split('<')[0].strip() if '<' in sender_email else 'there'
        
        response_body = f"""Hi {sender_name},

Thank you for your email. Our team has reviewed your request and here's our response:

{summary}

Best regards,
The AI Assistant Team

---
This is an automated response generated by our AI assistant system.
Task Reference: {task_id}"""

        # Send via email service
        from services.email_service import EmailService
        email_service = EmailService()
        
        send_result = email_service.send_email_sync(
            to=email_data.get('from'),
            subject=f"Re: {email_data.get('subject', 'Your request')}",
            body=response_body,
            reply_to_message_id=email_data.get('message_id'),
            tags=['auto_response', f'task_{task_id}']
        )
        
        # Log response sent
        log_action(
            action_type='email_response_sent',
            action_description=f'Sent response to {sender_email}',
            agent_id='email_agent',
            task_id=task_id,
            metadata={
                'email_id': send_result.get('id'),
                'recipient': sender_email
            }
        )
        
        return {
            'success': True,
            'email_id': send_result.get('id'),
            'recipient': sender_email
        }
        
    except Exception as e:
        logger.error(f"Failed to send email response: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@shared_task
def cleanup_completed_email_tasks(days: int = 7) -> Dict[str, int]:
    """
    Clean up completed email tasks older than specified days
    
    Args:
        days: Number of days to keep completed tasks
        
    Returns:
        Cleanup statistics
    """
    try:
        from models.task_storage import CollaborationTask
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Find old completed email tasks
        old_tasks = CollaborationTask.query.filter(
            CollaborationTask.status == 'completed',
            CollaborationTask.created_at < cutoff_date,
            CollaborationTask.task_metadata['source'].astext == 'email'
        ).all()
        
        archived_count = 0
        for task in old_tasks:
            try:
                # Archive task data (implement your archival strategy)
                logger.info(f"Archiving email task: {task.task_id}")
                # task.status = 'archived'  # Or delete if preferred
                archived_count += 1
            except Exception as e:
                logger.error(f"Failed to archive task {task.task_id}: {e}")
        
        # Commit changes
        from models.core import db
        db.session.commit()
        
        return {
            'archived': archived_count,
            'total_processed': len(old_tasks)
        }
        
    except Exception as e:
        logger.error(f"Email task cleanup failed: {e}")
        return {'error': str(e)}