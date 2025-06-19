"""
Memory-Optimized Multi-Agent Executor
"""
import asyncio
import gc
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque
import psutil
import os

from services.multi_agent_executor import (
    MultiAgentExecutor as BaseExecutor,
    TaskStatus,
    AgentMessage
)
from services.chat_history_storage import get_chat_history_storage

logger = logging.getLogger(__name__)


class MemoryOptimizedMultiAgentExecutor(BaseExecutor):
    """
    Enhanced executor with memory optimization and persistent chat history
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Memory optimization settings
        self.max_chat_history_per_agent = 100  # Limit in-memory history
        self.max_active_tasks = 50  # Limit concurrent tasks
        self.task_cleanup_interval = 300  # 5 minutes
        
        # Use persistent storage for chat history
        self.chat_storage = get_chat_history_storage()
        
        # Memory monitoring
        self.memory_threshold_mb = 500  # Trigger cleanup if over 500MB
        self.last_memory_check = datetime.now()
        self.last_cleanup = datetime.now()
        
        # Replace in-memory chat storage with limited deques
        self._agent_chats = {}
        
        # Start background cleanup task
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task for memory cleanup"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(60)  # Check every minute
                    self._check_memory_usage()
                    self._cleanup_old_tasks()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        # Create task in background
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(cleanup_loop())
        except RuntimeError:
            # No event loop, skip background task
            pass
    
    def _check_memory_usage(self):
        """Check and log memory usage"""
        try:
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            logger.info(f"Memory usage: {memory_mb:.1f} MB")
            
            if memory_mb > self.memory_threshold_mb:
                logger.warning(f"High memory usage detected: {memory_mb:.1f} MB")
                self._emergency_cleanup()
                
        except Exception as e:
            logger.error(f"Failed to check memory: {e}")
    
    def _emergency_cleanup(self):
        """Emergency cleanup when memory is high"""
        logger.info("Starting emergency memory cleanup...")
        
        # Clear old agent chats
        agents_to_clear = []
        for agent_id, messages in self._agent_chats.items():
            if len(messages) > 50:
                # Keep only last 50 messages
                self._agent_chats[agent_id] = list(messages)[-50:]
                agents_to_clear.append(agent_id)
        
        # Clear completed tasks older than 1 hour
        current_time = datetime.now()
        tasks_to_remove = []
        
        for task_id, task in self.storage._tasks.items():
            if isinstance(task, TaskStatus):
                if task.status in ['completed', 'error']:
                    if task.end_time and (current_time - task.end_time).seconds > 3600:
                        tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.storage._tasks[task_id]
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
        
        # Force garbage collection
        gc.collect()
        
        logger.info(f"Emergency cleanup completed: cleared {len(agents_to_clear)} agent chats, "
                   f"removed {len(tasks_to_remove)} old tasks")
    
    def _cleanup_old_tasks(self):
        """Regular cleanup of old tasks"""
        current_time = datetime.now()
        
        # Only cleanup every interval
        if (current_time - self.last_cleanup).seconds < self.task_cleanup_interval:
            return
        
        self.last_cleanup = current_time
        
        # Remove completed tasks older than 2 hours
        tasks_to_remove = []
        for task_id in list(self._running_tasks.keys()):
            if task_id not in self._running_tasks:
                continue
                
            task = self.storage.get_task(task_id)
            if task and task.status in ['completed', 'error']:
                if task.end_time and (current_time - task.end_time).seconds > 7200:
                    tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            logger.debug(f"Cleaned up old task: {task_id}")
    
    def start_agent_chat(self, agent_id: str, initial_message: str, model: str = None, enhance_prompt: bool = True) -> Dict[str, Any]:
        """Start agent chat with persistent storage"""
        result = super().start_agent_chat(agent_id, initial_message, model, enhance_prompt)
        
        # Store in persistent storage
        if result.get('success'):
            self.chat_storage.add_message(agent_id, 'user', initial_message)
            self.chat_storage.add_message(agent_id, 'assistant', result.get('response', ''))
        
        return result
    
    def get_agent_chat_history(self, agent_id: str) -> List[Dict]:
        """Get chat history from persistent storage"""
        # First check if we have recent messages in memory
        if agent_id in self._agent_chats:
            memory_messages = self._agent_chats[agent_id]
            if memory_messages:
                return memory_messages
        
        # Load from persistent storage
        history = self.chat_storage.get_history(agent_id)
        
        # Convert to expected format
        formatted_history = []
        for msg in history:
            formatted_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Cache recent messages in memory
        if formatted_history:
            if agent_id not in self._agent_chats:
                self._agent_chats[agent_id] = deque(maxlen=self.max_chat_history_per_agent)
            
            # Add to deque (automatically limits size)
            for msg in formatted_history[-self.max_chat_history_per_agent:]:
                self._agent_chats[agent_id].append(msg)
        
        return formatted_history
    
    def clear_agent_chat_history(self, agent_id: str) -> None:
        """Clear chat history from both memory and persistent storage"""
        # Clear from memory
        if agent_id in self._agent_chats:
            del self._agent_chats[agent_id]
        
        # Clear from persistent storage
        self.chat_storage.clear_history(agent_id)
        
        logger.info(f"Cleared all chat history for agent {agent_id}")
    
    async def _add_conversation_entry(self, task_id: str, agent_name: str, content: str):
        """Add conversation entry with memory management"""
        await super()._add_conversation_entry(task_id, agent_name, content)
        
        # Limit conversation size in task
        task = self.storage.get_task(task_id)
        if task and len(task.conversations) > 100:
            # Keep only last 50 conversations
            task.conversations = task.conversations[-50:]
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        chat_stats = self.chat_storage.get_memory_usage()
        
        return {
            "memory_usage_mb": memory_info.rss / 1024 / 1024,
            "active_tasks": len(self._running_tasks),
            "total_tasks": len(self.storage._tasks) if hasattr(self.storage, '_tasks') else 0,
            "agents_in_memory": len(self._agent_chats),
            "chat_storage": chat_stats,
            "max_limits": {
                "max_chat_history_per_agent": self.max_chat_history_per_agent,
                "max_active_tasks": self.max_active_tasks,
                "memory_threshold_mb": self.memory_threshold_mb
            }
        }
    
    def execute_task(self, *args, **kwargs):
        """Execute task with active task limiting"""
        # Check if we're at the limit
        if len(self._running_tasks) >= self.max_active_tasks:
            # Try to cleanup first
            self._cleanup_old_tasks()
            
            if len(self._running_tasks) >= self.max_active_tasks:
                return {
                    "success": False,
                    "error": f"Too many active tasks ({len(self._running_tasks)}). Please wait for some to complete."
                }
        
        return super().execute_task(*args, **kwargs)