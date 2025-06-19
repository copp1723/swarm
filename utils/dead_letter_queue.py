"""Dead Letter Queue (DLQ) for handling failed tasks"""
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from models.core import db
from sqlalchemy import Column, String, DateTime, Integer, JSON, Text, Boolean
from utils.logging_config import get_logger
from utils.notification_service import NotificationService

logger = get_logger(__name__)


@dataclass
class FailedTaskInfo:
    """Information about a failed task"""
    task_id: str
    agent_id: str
    task_data: Dict[str, Any]
    error: str
    attempt_count: int
    failed_at: datetime
    status: str = 'failed'
    priority: str = 'normal'
    retry_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class FailedTask(db.Model):
    """Database model for failed tasks"""
    __tablename__ = 'failed_tasks'
    
    id = Column(String(50), primary_key=True)
    task_id = Column(String(50), nullable=False)
    agent_id = Column(String(50), nullable=False)
    task_data = Column(JSON, nullable=False)
    error = Column(Text, nullable=False)
    attempt_count = Column(Integer, default=1)
    failed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='failed')  # failed, retrying, abandoned
    priority = Column(String(20), default='normal')
    retry_at = Column(DateTime)
    task_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'task_data': self.task_data,
            'error': self.error,
            'attempt_count': self.attempt_count,
            'failed_at': self.failed_at.isoformat() if self.failed_at else None,
            'status': self.status,
            'priority': self.priority,
            'retry_at': self.retry_at.isoformat() if self.retry_at else None,
            'metadata': self.task_metadata
        }


class DeadLetterQueue:
    """
    Dead Letter Queue for handling failed tasks
    
    Provides persistent storage and retry capabilities for failed tasks
    """
    
    def __init__(self, redis_client=None):
        """
        Initialize DLQ with optional Redis for fast access
        
        Args:
            redis_client: Optional Redis client for caching
        """
        self.redis = redis_client
        self.use_redis = redis_client is not None
        self.notification_service = NotificationService()
        self.dlq_key_prefix = "dlq:"
        
    async def add_failed_task(self,
                             task_id: str,
                             agent_id: str,
                             task_data: Dict[str, Any],
                             error: Exception,
                             attempt_count: int = 1,
                             priority: str = 'normal',
                             metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a failed task to the DLQ
        
        Args:
            task_id: Original task ID
            agent_id: Agent that failed to process the task
            task_data: Original task data
            error: The exception that caused the failure
            attempt_count: Number of attempts made
            priority: Task priority (critical, high, normal, low)
            metadata: Additional metadata
            
        Returns:
            DLQ entry ID
        """
        try:
            # Create failed task info
            failed_task_info = FailedTaskInfo(
                task_id=task_id,
                agent_id=agent_id,
                task_data=task_data,
                error=str(error),
                attempt_count=attempt_count,
                failed_at=datetime.utcnow(),
                priority=priority,
                metadata=metadata
            )
            
            # Generate unique ID for DLQ entry
            dlq_id = f"dlq_{task_id}_{datetime.utcnow().timestamp()}"
            
            # Store in Redis for quick access
            if self.use_redis:
                try:
                    # Store in Redis list for FIFO processing
                    await self.redis.lpush(
                        f"{self.dlq_key_prefix}failed_tasks",
                        json.dumps(asdict(failed_task_info), default=str)
                    )
                    
                    # Also store by priority for priority-based processing
                    await self.redis.lpush(
                        f"{self.dlq_key_prefix}priority:{priority}",
                        dlq_id
                    )
                    
                    # Set TTL for Redis entries (7 days)
                    await self.redis.expire(f"{self.dlq_key_prefix}failed_tasks", 604800)
                except Exception as redis_error:
                    logger.error(f"Failed to store in Redis: {redis_error}")
            
            # Store in database for persistence
            db_task = FailedTask(
                id=dlq_id,
                task_id=task_id,
                agent_id=agent_id,
                task_data=task_data,
                error=str(error),
                attempt_count=attempt_count,
                failed_at=failed_task_info.failed_at,
                status='failed',
                priority=priority,
                task_metadata=metadata
            )
            
            db.session.add(db_task)
            db.session.commit()
            
            logger.warning(
                f"Task {task_id} added to DLQ after {attempt_count} attempts. "
                f"Error: {error}"
            )
            
            # Send alert for critical tasks
            if priority == 'critical':
                await self._send_critical_failure_alert(failed_task_info)
            
            return dlq_id
            
        except Exception as e:
            logger.error(f"Failed to add task to DLQ: {e}")
            raise
    
    async def retry_failed_tasks(self, 
                                max_tasks: int = 10,
                                priority_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve failed tasks for retry
        
        Args:
            max_tasks: Maximum number of tasks to retrieve
            priority_filter: Optional priority filter
            
        Returns:
            List of failed tasks
        """
        tasks = []
        
        # Try Redis first for better performance
        if self.use_redis:
            try:
                key = (f"{self.dlq_key_prefix}priority:{priority_filter}" 
                      if priority_filter 
                      else f"{self.dlq_key_prefix}failed_tasks")
                
                # Get tasks from Redis
                for _ in range(max_tasks):
                    task_json = await self.redis.rpop(key)
                    if task_json:
                        try:
                            task_data = json.loads(task_json)
                            tasks.append(task_data)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in DLQ: {task_json}")
                    else:
                        break
                
                if tasks:
                    return tasks
                    
            except Exception as redis_error:
                logger.error(f"Redis error in DLQ: {redis_error}")
        
        # Fallback to database
        query = FailedTask.query.filter_by(status='failed')
        
        if priority_filter:
            query = query.filter_by(priority=priority_filter)
        
        # Get tasks that are ready for retry
        query = query.filter(
            db.or_(
                FailedTask.retry_at.is_(None),
                FailedTask.retry_at <= datetime.utcnow()
            )
        )
        
        db_tasks = query.order_by(
            FailedTask.priority.desc(),
            FailedTask.failed_at.asc()
        ).limit(max_tasks).all()
        
        # Update status to retrying
        for task in db_tasks:
            task.status = 'retrying'
            tasks.append(task.to_dict())
        
        if db_tasks:
            db.session.commit()
        
        return tasks
    
    async def mark_task_abandoned(self, dlq_id: str, reason: str = "Max retries exceeded"):
        """
        Mark a task as abandoned (won't be retried)
        
        Args:
            dlq_id: DLQ entry ID
            reason: Reason for abandonment
        """
        task = FailedTask.query.get(dlq_id)
        if task:
            task.status = 'abandoned'
            task.task_metadata = task.task_metadata or {}
            task.task_metadata['abandoned_reason'] = reason
            task.task_metadata['abandoned_at'] = datetime.utcnow().isoformat()
            db.session.commit()
            
            logger.error(f"Task {task.task_id} abandoned: {reason}")
    
    async def get_dlq_stats(self) -> Dict[str, Any]:
        """Get statistics about the DLQ"""
        stats = {
            'total_failed': FailedTask.query.filter_by(status='failed').count(),
            'total_retrying': FailedTask.query.filter_by(status='retrying').count(),
            'total_abandoned': FailedTask.query.filter_by(status='abandoned').count(),
            'by_priority': {},
            'by_agent': {},
            'oldest_task': None
        }
        
        # Count by priority
        for priority in ['critical', 'high', 'normal', 'low']:
            stats['by_priority'][priority] = FailedTask.query.filter_by(
                status='failed', priority=priority
            ).count()
        
        # Count by agent
        agent_counts = db.session.query(
            FailedTask.agent_id, db.func.count(FailedTask.id)
        ).filter_by(status='failed').group_by(FailedTask.agent_id).all()
        
        stats['by_agent'] = dict(agent_counts)
        
        # Get oldest task
        oldest = FailedTask.query.filter_by(status='failed').order_by(
            FailedTask.failed_at.asc()
        ).first()
        
        if oldest:
            stats['oldest_task'] = {
                'task_id': oldest.task_id,
                'failed_at': oldest.failed_at.isoformat(),
                'age_hours': (datetime.utcnow() - oldest.failed_at).total_seconds() / 3600
            }
        
        return stats
    
    async def _send_critical_failure_alert(self, failed_task: FailedTaskInfo):
        """Send alert for critical task failure"""
        try:
            message = (
                f"🚨 Critical Task Failed\n\n"
                f"Task ID: {failed_task.task_id}\n"
                f"Agent: {failed_task.agent_id}\n"
                f"Attempts: {failed_task.attempt_count}\n"
                f"Error: {failed_task.error}\n"
                f"Time: {failed_task.failed_at.isoformat()}"
            )
            
            await self.notification_service.send_alert(
                "Critical Task Failure",
                message,
                severity="critical"
            )
            
        except Exception as e:
            logger.error(f"Failed to send critical alert: {e}")
    
    def cleanup_old_entries(self, days: int = 30):
        """Clean up old DLQ entries"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted = FailedTask.query.filter(
            FailedTask.created_at < cutoff_date,
            FailedTask.status.in_(['abandoned', 'resolved'])
        ).delete()
        
        db.session.commit()
        
        logger.info(f"Cleaned up {deleted} old DLQ entries")
        return deleted


# Global DLQ instance
dlq = None

def init_dlq(app, redis_client=None):
    """Initialize the global DLQ instance"""
    global dlq
    dlq = DeadLetterQueue(redis_client)
    return dlq