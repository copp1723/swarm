import logging
from typing import Dict, List, Optional, Any
from services.memory_optimized_executor import MemoryOptimizedMultiAgentExecutor
from services.multi_agent_executor import InMemoryTaskStorage
from services.database_task_storage import DatabaseTaskStorage

logger = logging.getLogger(__name__)

class MultiAgentTaskService:
    """Service that handles multi-agent task execution with memory optimization."""
    
    def __init__(self, use_database: bool = True):
        """Initialize with memory-optimized executor"""
        # Use database storage by default for persistence
        if use_database:
            try:
                self.storage = DatabaseTaskStorage()
                logger.info("Using database storage for multi-agent tasks")
            except Exception as e:
                logger.warning(f"Failed to initialize database storage: {e}. Falling back to in-memory storage")
                self.storage = InMemoryTaskStorage()
        else:
            self.storage = InMemoryTaskStorage()
            logger.info("Using in-memory storage for multi-agent tasks")
        
        # Use memory-optimized executor
        self.executor = MemoryOptimizedMultiAgentExecutor(self.storage)
        logger.info("Multi-agent task service initialized with memory-optimized executor")
    
    def execute_repository_task(
        self,
        task_description: str,
        agent_roles: List[Any],
        working_directory: str,
        conversation_id: int = 1,
        enable_real_time: bool = True
    ) -> Dict[str, Any]:
        """Execute a multi-agent task on a specific repository."""
        if not task_description or not agent_roles:
            return {"success": False, "error": "Task description and agent roles are required"}
        if not working_directory:
            return {"success": False, "error": "Working directory is required"}
        
        # Convert string agent roles to config format
        agent_configs = []
        for agent in agent_roles:
            if isinstance(agent, str):
                # Convert string to agent config
                agent_configs.append({
                    "agent_id": f"{agent}_01",
                    "agent_name": agent.title() + " Agent",
                    "model": "openai/gpt-4"
                })
            else:
                # Already a dict config
                agent_configs.append(agent)
        
        return self.executor.execute_task(
            task_description=task_description,
            agent_configs=agent_configs,
            working_directory=working_directory,
            conversation_id=conversation_id,
            enable_real_time=enable_real_time
        )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task."""
        return self.executor.get_task_status(task_id)
    
    def get_task_conversation(self, task_id: str, offset: int = 0) -> Optional[Dict[str, Any]]:
        """Get the conversation history for a task."""
        return self.executor.get_task_conversation(task_id, offset)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        return self.executor.get_memory_stats()

# Global service instance
_service_instance = None

def get_multi_agent_service() -> MultiAgentTaskService:
    """Get or create the global multi-agent service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = MultiAgentTaskService()
    return _service_instance

def execute_concrete_repository_task(
    task_description: str,
    agent_roles: List[Dict],
    working_directory: str,
    conversation_id: int = 1,
    model: str = "openai/gpt-4",
    enable_real_time: bool = True
) -> Dict[str, Any]:
    """Convenience function to execute a repository task."""
    service = get_multi_agent_service()
    return service.execute_repository_task(
        task_description=task_description,
        agent_roles=agent_roles,
        working_directory=working_directory,
        conversation_id=conversation_id,
        enable_real_time=enable_real_time
    )