"""
Database Task Storage Service
Replaces in-memory TASKS dictionary with persistent database storage
"""

import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from threading import Lock

from flask import current_app
from models.core import db
from models.task_storage import (
    CollaborationTask, ConversationHistory, AuditLog,
    create_task, get_task, update_task_status, add_conversation, log_action,
    get_task_conversations, get_agent_history
)
from utils.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseTaskStorage:
    """
    Database-backed task storage service
    Drop-in replacement for TASKS dictionary
    """
    
    def __init__(self):
        self._lock = Lock()
        self._cache = {}  # Optional in-memory cache for performance
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    def create_task(self, task_id: str, description: str, agents: List[str], 
                   session_id: str = None, **kwargs) -> Dict[str, Any]:
        """Create a new task in database"""
        try:
            # Create task in database
            task = create_task(
                description=description,
                session_id=session_id or f"session_{int(time.time())}",
                task_id=task_id,
                agents_involved=agents,
                agents=agents,  # Legacy field
                status='running',
                created_at=datetime.utcnow(),
                **kwargs
            )
            
            # Log action
            log_action(
                action_type='task_created',
                action_description=f'Created task: {description}',
                agent_id='system',
                task_id=task_id,
                session_id=session_id,
                metadata={'agents': agents}
            )
            
            # Update cache
            task_dict = task.to_dict()
            with self._lock:
                self._cache[task_id] = {
                    'data': task_dict,
                    'timestamp': time.time()
                }
            
            return task_dict
            
        except Exception as e:
            logger.error(f"Failed to create task {task_id}: {e}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID from database"""
        # Check cache first
        with self._lock:
            cached = self._cache.get(task_id)
            if cached and (time.time() - cached['timestamp'] < self._cache_ttl):
                return cached['data']
        
        # Fetch from database
        task = get_task(task_id)
        if not task:
            return None
        
        task_dict = task.to_dict()
        
        # Update cache
        with self._lock:
            self._cache[task_id] = {
                'data': task_dict,
                'timestamp': time.time()
            }
        
        return task_dict
    
    def update_task(self, task_id: str, **updates) -> Optional[Dict[str, Any]]:
        """Update task in database"""
        try:
            # Handle special fields
            status = updates.pop('status', None)
            progress = updates.pop('progress', None)
            current_phase = updates.pop('current_phase', None)
            
            # Update in database
            task = get_task(task_id)
            if not task:
                return None
            
            # Update status with phase and progress
            if status:
                task.update_status(status, phase=current_phase, progress=progress)
            elif current_phase or progress is not None:
                task.current_phase = current_phase or task.current_phase
                task.progress = progress if progress is not None else task.progress
            
            # Update other fields
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            task.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Invalidate cache
            with self._lock:
                if task_id in self._cache:
                    del self._cache[task_id]
            
            # Log update
            log_action(
                action_type='task_updated',
                action_description=f'Updated task {task_id}',
                agent_id='system',
                task_id=task_id,
                metadata={'updates': updates}
            )
            
            return task.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            db.session.rollback()
            raise
    
    def add_message(self, task_id: str, agent_id: str, content: str, 
                   role: str = 'assistant', **metadata) -> bool:
        """Add message to task conversation history"""
        try:
            # Get task to ensure it exists
            task = get_task(task_id)
            if not task:
                return False
            
            # Add to conversation history
            conv = add_conversation(
                task_id=task_id,
                agent_id=agent_id,
                role=role,
                content=content,
                phase=task.current_phase,
                metadata=metadata
            )
            
            # Update task messages (legacy field)
            if task.messages is None:
                task.messages = []
            
            task.messages.append({
                'agent_id': agent_id,
                'content': content,
                'timestamp': time.time(),
                'role': role,
                **metadata
            })
            
            # Update conversation count
            task.total_messages = (task.total_messages or 0) + 1
            
            db.session.commit()
            
            # Invalidate cache
            with self._lock:
                if task_id in self._cache:
                    del self._cache[task_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add message to task {task_id}: {e}")
            db.session.rollback()
            return False
    
    def get_all_tasks(self, session_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Get all tasks, optionally filtered"""
        query = CollaborationTask.query
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        if status:
            query = query.filter_by(status=status)
        
        tasks = query.order_by(CollaborationTask.created_at.desc()).all()
        return [task.to_dict() for task in tasks]
    
    def get_task_conversations(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a task"""
        conversations = get_task_conversations(task_id)
        return [conv.to_dict() for conv in conversations]
    
    def get_agent_history(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history for an agent"""
        history = get_agent_history(agent_id, limit)
        return [conv.to_dict() for conv in history]
    
    def clear_cache(self):
        """Clear the in-memory cache"""
        with self._lock:
            self._cache.clear()
    
    def cleanup_old_tasks(self, days: int = 30):
        """Remove old tasks from database"""
        return CollaborationTask.delete_old_tasks(days)

# Global instance
_task_storage = None

def get_task_storage() -> DatabaseTaskStorage:
    """Get or create the global task storage instance"""
    global _task_storage
    if _task_storage is None:
        _task_storage = DatabaseTaskStorage()
    return _task_storage

# Compatibility layer for TASKS dictionary access
class TasksDictProxy:
    """
    Proxy class that mimics dictionary behavior but uses database
    Provides compatibility for code expecting TASKS dictionary
    """
    
    def __init__(self):
        self.storage = get_task_storage()
    
    def __getitem__(self, task_id: str) -> Dict[str, Any]:
        task = self.storage.get_task(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found")
        return task
    
    def __setitem__(self, task_id: str, task_data: Dict[str, Any]):
        # Create or update task
        if self.storage.get_task(task_id):
            self.storage.update_task(task_id, **task_data)
        else:
            self.storage.create_task(
                task_id=task_id,
                description=task_data.get('task_description', ''),
                agents=task_data.get('agents', []),
                **task_data
            )
    
    def get(self, task_id: str, default=None) -> Optional[Dict[str, Any]]:
        task = self.storage.get_task(task_id)
        return task if task else default
    
    def __contains__(self, task_id: str) -> bool:
        return self.storage.get_task(task_id) is not None
    
    def update(self, task_id: str, **updates):
        """Update task with new data"""
        self.storage.update_task(task_id, **updates)
    
    def keys(self):
        """Get all task IDs"""
        tasks = self.storage.get_all_tasks()
        return [t['task_id'] for t in tasks]
    
    def values(self):
        """Get all tasks"""
        return self.storage.get_all_tasks()
    
    def items(self):
        """Get all task ID/task pairs"""
        tasks = self.storage.get_all_tasks()
        return [(t['task_id'], t) for t in tasks]

# Create global TASKS proxy for compatibility
TASKS = TasksDictProxy()