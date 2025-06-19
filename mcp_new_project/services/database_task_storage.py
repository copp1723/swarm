"""
Database Task Storage Implementation
Provides persistent storage for multi-agent tasks using SQLAlchemy
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from models.task_storage import TaskStorage
from models.core import db


class DatabaseTaskStorage:
    """Database-backed storage for multi-agent tasks"""
    
    def __init__(self):
        self.logger = logger.bind(component="DatabaseTaskStorage")
        self.logger.info("Initialized database task storage")
    
    def store_task(self, task_id: str, task_status) -> None:
        """Store a task in the database (compatible with executor interface)"""
        try:
            # Convert TaskStatus object to dict if needed
            if hasattr(task_status, 'to_dict'):
                task_data = task_status.to_dict()
            else:
                task_data = task_status
            
            # Extract relevant fields
            task = TaskStorage.create_task(
                task_id=task_id,
                task_description=task_data.get('task_description') or task_data.get('results', {}).get('task_description'),
                agents=task_data.get('agents_working', []) or task_data.get('results', {}).get('agents', []),
                working_directory=task_data.get('results', {}).get('working_directory'),
                sequential=task_data.get('results', {}).get('sequential', False)
            )
            
            # Set status fields
            task.status = task_data.get('status', 'pending')
            task.progress = task_data.get('progress', 0)
            task.current_phase = task_data.get('current_phase')
            
            # Set conversation data
            task.conversations = task_data.get('conversations', [])
            task.all_communications = task_data.get('all_communications', [])
            task.messages = task_data.get('messages', [])
            task.results = task_data.get('results', {})
            
            # Set timestamps
            if task_data.get('start_time'):
                # Convert string to datetime if necessary
                start_time = task_data['start_time']
                if isinstance(start_time, str):
                    from dateutil import parser
                    task.created_at = parser.parse(start_time)
                elif hasattr(start_time, 'isoformat'):  # datetime object
                    task.created_at = start_time
                else:
                    task.created_at = datetime.utcnow()
            
            db.session.commit()
            self.logger.info(f"Stored task {task_id} in database")
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to store task {task_id}: {str(e)}")
            raise
    
    def get_task(self, task_id: str):
        """Retrieve a task from the database (returns TaskStatus-like object)"""
        try:
            task = TaskStorage.get_task(task_id)
            if task:
                # Import here to avoid circular dependency
                from services.multi_agent_executor import TaskStatus
                
                # Convert database model to TaskStatus object
                task_dict = task.to_dict()
                status = TaskStatus(
                    task_id=task_id,
                    status=task_dict['status'],
                    progress=task_dict['progress'],
                    current_phase=task_dict['current_phase'] or "",
                    agents_working=task_dict.get('agents', []),
                    conversations=task_dict.get('conversations', []),
                    results=task_dict.get('results', {})
                )
                
                # Set timestamps if available
                if task.created_at:
                    status.start_time = task.created_at
                if task.completed_at:
                    status.end_time = task.completed_at
                
                # Set agent messages from all_communications
                if task_dict.get('all_communications'):
                    # TODO: Convert communications to AgentMessage objects if needed
                    pass
                
                return status
            return None
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {str(e)}")
            return None
    
    def update_task(self, task_id: str, **updates):
        """Update a task in the database (compatible with executor interface)"""
        try:
            # Handle special case for completed status
            if updates.get('status') == 'completed' and 'completed_at' not in updates:
                updates['completed_at'] = datetime.utcnow()
            
            task = TaskStorage.update_task(task_id, **updates)
            if task:
                self.logger.debug(f"Updated task {task_id} with {list(updates.keys())}")
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update task {task_id}: {str(e)}")
    
    def store_message(self, task_id: str, message: Dict[str, Any]):
        """Store a message for a task (compatible with executor interface)"""
        try:
            task = TaskStorage.get_task(task_id)
            if not task:
                self.logger.warning(f"Task {task_id} not found for message storage")
                return
            
            # Append to messages
            messages = task.messages or []
            messages.append({
                **message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Also append to all_communications for compatibility
            all_comms = task.all_communications or []
            all_comms.append({
                **message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            TaskStorage.update_task(
                task_id,
                messages=messages,
                all_communications=all_comms
            )
            
            self.logger.debug(f"Stored message for task {task_id}")
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to store message for task {task_id}: {str(e)}")
    
    def create_task(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task in the database"""
        try:
            task = TaskStorage.create_task(
                task_id=task_id,
                task_description=task_data.get('task_description'),
                agents=task_data.get('agents', []),
                working_directory=task_data.get('working_directory'),
                sequential=task_data.get('sequential', False)
            )
            
            # Set initial status and progress
            task.status = task_data.get('status', 'pending')
            task.progress = task_data.get('progress', 0)
            task.current_phase = task_data.get('current_phase')
            
            # Initialize empty collections
            task.conversations = []
            task.all_communications = []
            task.messages = []
            task.results = {}
            
            db.session.commit()
            
            self.logger.info(f"Created task {task_id} in database")
            return task.to_dict()
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create task {task_id}: {str(e)}")
            raise
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task from the database"""
        try:
            task = TaskStorage.get_task(task_id)
            if task:
                return task.to_dict()
            return None
        except Exception as e:
            self.logger.error(f"Failed to get task {task_id}: {str(e)}")
            return None
    
    def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a task in the database"""
        try:
            # Handle special case for completed status
            if updates.get('status') == 'completed' and 'completed_at' not in updates:
                updates['completed_at'] = datetime.utcnow()
            
            task = TaskStorage.update_task(task_id, **updates)
            if task:
                self.logger.debug(f"Updated task {task_id} with {list(updates.keys())}")
                return task.to_dict()
            return None
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update task {task_id}: {str(e)}")
            return None
    
    def add_conversation(self, task_id: str, agent_id: str, message: str, response: str):
        """Add a conversation to a task"""
        try:
            task = TaskStorage.get_task(task_id)
            if not task:
                self.logger.warning(f"Task {task_id} not found for conversation update")
                return
            
            # Append to conversations
            conversations = task.conversations or []
            conversations.append({
                'agent_id': agent_id,
                'message': message,
                'response': response,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Append to all_communications
            all_comms = task.all_communications or []
            all_comms.extend([
                {'agent': 'user', 'content': message, 'timestamp': datetime.utcnow().isoformat()},
                {'agent': agent_id, 'content': response, 'timestamp': datetime.utcnow().isoformat()}
            ])
            
            # Update task
            TaskStorage.update_task(
                task_id,
                conversations=conversations,
                all_communications=all_comms
            )
            
            self.logger.debug(f"Added conversation to task {task_id} for agent {agent_id}")
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to add conversation to task {task_id}: {str(e)}")
    
    def add_message(self, task_id: str, message: Dict[str, Any]):
        """Add a message to a task"""
        try:
            task = TaskStorage.get_task(task_id)
            if not task:
                self.logger.warning(f"Task {task_id} not found for message update")
                return
            
            messages = task.messages or []
            messages.append({
                **message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            TaskStorage.update_task(task_id, messages=messages)
            self.logger.debug(f"Added message to task {task_id}")
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to add message to task {task_id}: {str(e)}")
    
    def update_results(self, task_id: str, agent_id: str, result: Any):
        """Update results for a specific agent in a task"""
        try:
            task = TaskStorage.get_task(task_id)
            if not task:
                self.logger.warning(f"Task {task_id} not found for results update")
                return
            
            results = task.results or {}
            results[agent_id] = result
            
            TaskStorage.update_task(task_id, results=results)
            self.logger.debug(f"Updated results for task {task_id}, agent {agent_id}")
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update results for task {task_id}: {str(e)}")
    
    def get_all_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all tasks, optionally filtered by status"""
        try:
            query = TaskStorage.query
            if status:
                query = query.filter_by(status=status)
            
            tasks = query.order_by(TaskStorage.created_at.desc()).all()
            return [task.to_dict() for task in tasks]
            
        except Exception as e:
            self.logger.error(f"Failed to get all tasks: {str(e)}")
            return []
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the database"""
        try:
            task = TaskStorage.get_task(task_id)
            if task:
                db.session.delete(task)
                db.session.commit()
                self.logger.info(f"Deleted task {task_id}")
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to delete task {task_id}: {str(e)}")
            return False
    
    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Clean up tasks older than specified days"""
        try:
            count = TaskStorage.delete_old_tasks(days)
            self.logger.info(f"Cleaned up {count} old tasks")
            return count
        except Exception as e:
            self.logger.error(f"Failed to cleanup old tasks: {str(e)}")
            return 0