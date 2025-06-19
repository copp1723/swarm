"""
Task Dispatcher Service
Routes parsed email tasks to appropriate agents via the multi-agent service
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio

from models.agent_task import AgentTask, AgentAssignment
from utils.service_container import get_service

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """
    Dispatches tasks from emails to the appropriate agents
    """
    
    def __init__(self):
        self.dispatch_queue = []
        self.dispatch_history = []
        
    def dispatch_task(self, agent_task: AgentTask, 
                     working_directory: str = "./",
                     enable_real_time: bool = True) -> Dict[str, Any]:
        """
        Dispatch a parsed email task to the appropriate agents
        
        Args:
            agent_task: The structured task to dispatch
            working_directory: Working directory for the task
            enable_real_time: Enable real-time updates
            
        Returns:
            Dict containing dispatch result
        """
        try:
            # Validate task
            if not agent_task.agent_assignment:
                raise ValueError("Task has no agent assignment")
                
            # Get the multi-agent service
            multi_agent_service = get_service('multi_agent_service')
            
            # Prepare agent list
            agents = [agent_task.agent_assignment.primary_agent]
            if agent_task.agent_assignment.supporting_agents:
                agents.extend(agent_task.agent_assignment.supporting_agents)
            
            # Create task description with context
            task_description = self._create_task_description(agent_task)
            
            logger.info(f"Dispatching task {agent_task.task_id} to agents: {agents}")
            
            # Execute the task
            result = multi_agent_service.execute_repository_task(
                task_description=task_description,
                agent_roles=agents,
                working_directory=working_directory,
                enable_real_time=enable_real_time
            )
            
            # Update task status
            agent_task.status = "dispatched"
            agent_task.processed = True
            agent_task.processing_notes.append(
                f"Dispatched at {datetime.utcnow().isoformat()} to {', '.join(agents)}"
            )
            
            # Record dispatch
            dispatch_record = {
                "task_id": agent_task.task_id,
                "email_message_id": agent_task.email_metadata.message_id if agent_task.email_metadata else None,
                "agents": agents,
                "dispatched_at": datetime.utcnow().isoformat(),
                "multi_agent_task_id": result.get("task_id"),
                "status": result.get("status", "unknown")
            }
            self.dispatch_history.append(dispatch_record)
            
            return {
                "success": True,
                "task_id": agent_task.task_id,
                "multi_agent_task_id": result.get("task_id"),
                "agents": agents,
                "message": f"Task dispatched to {len(agents)} agents",
                "dispatch_record": dispatch_record
            }
            
        except Exception as e:
            logger.error(f"Failed to dispatch task {agent_task.task_id}: {str(e)}")
            
            # Update task with error
            agent_task.status = "failed"
            agent_task.processing_notes.append(f"Dispatch failed: {str(e)}")
            
            return {
                "success": False,
                "task_id": agent_task.task_id,
                "error": str(e),
                "message": "Failed to dispatch task"
            }
    
    def dispatch_collaborative_task(self, agent_task: AgentTask,
                                  sequential: bool = False,
                                  enhance_prompt: bool = True) -> Dict[str, Any]:
        """
        Dispatch a task as a collaborative effort between multiple agents
        
        Args:
            agent_task: The task to dispatch
            sequential: Whether agents should work sequentially
            enhance_prompt: Whether to enhance the prompt
            
        Returns:
            Dict containing dispatch result
        """
        try:
            # Get multi-agent service
            multi_agent_service = get_service('multi_agent_service')
            
            # Prepare tagged agents
            tagged_agents = [agent_task.agent_assignment.primary_agent]
            if agent_task.agent_assignment.supporting_agents:
                tagged_agents.extend(agent_task.agent_assignment.supporting_agents)
            
            # Create collaborative task description
            task_description = self._create_collaborative_description(agent_task)
            
            logger.info(f"Dispatching collaborative task {agent_task.task_id} to {len(tagged_agents)} agents")
            
            # Execute collaborative task
            result = multi_agent_service.executor.execute_collaborative_task(
                task_description=task_description,
                tagged_agents=tagged_agents,
                working_directory="./",
                sequential=sequential,
                enhance_prompt=enhance_prompt
            )
            
            # Update task status
            agent_task.status = "dispatched_collaborative"
            agent_task.processed = True
            agent_task.processing_notes.append(
                f"Collaborative dispatch at {datetime.utcnow().isoformat()}"
            )
            
            return {
                "success": True,
                "task_id": agent_task.task_id,
                "collaborative_task_id": result.get("task_id"),
                "agents": tagged_agents,
                "mode": "sequential" if sequential else "parallel",
                "message": f"Collaborative task dispatched to {len(tagged_agents)} agents"
            }
            
        except Exception as e:
            logger.error(f"Failed to dispatch collaborative task: {str(e)}")
            return {
                "success": False,
                "task_id": agent_task.task_id,
                "error": str(e)
            }
    
    def queue_task(self, agent_task: AgentTask) -> str:
        """
        Queue a task for later dispatch
        
        Args:
            agent_task: Task to queue
            
        Returns:
            Queue position
        """
        self.dispatch_queue.append(agent_task)
        position = len(self.dispatch_queue)
        
        logger.info(f"Queued task {agent_task.task_id} at position {position}")
        
        agent_task.status = "queued"
        agent_task.processing_notes.append(
            f"Queued at position {position} on {datetime.utcnow().isoformat()}"
        )
        
        return f"Position {position} in queue"
    
    def process_queue(self, max_tasks: int = 5) -> List[Dict[str, Any]]:
        """
        Process queued tasks
        
        Args:
            max_tasks: Maximum number of tasks to process
            
        Returns:
            List of dispatch results
        """
        results = []
        tasks_to_process = min(max_tasks, len(self.dispatch_queue))
        
        logger.info(f"Processing {tasks_to_process} tasks from queue")
        
        for _ in range(tasks_to_process):
            if not self.dispatch_queue:
                break
                
            task = self.dispatch_queue.pop(0)
            result = self.dispatch_task(task)
            results.append(result)
        
        return results
    
    def get_dispatch_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the dispatch status for a task
        
        Args:
            task_id: The task ID to check
            
        Returns:
            Dispatch record if found
        """
        for record in self.dispatch_history:
            if record["task_id"] == task_id:
                return record
        return None
    
    def _create_task_description(self, agent_task: AgentTask) -> str:
        """Create a detailed task description for agents"""
        parts = [agent_task.get_task_prompt()]
        
        # Add email context if available
        if agent_task.email_metadata:
            parts.append(f"\n--- Email Context ---")
            parts.append(f"From: {agent_task.email_metadata.sender}")
            parts.append(f"Subject: {agent_task.email_metadata.subject}")
            
            if agent_task.context.get("referenced_urls"):
                parts.append(f"\nReferenced URLs:")
                for url in agent_task.context["referenced_urls"]:
                    parts.append(f"- {url}")
        
        # Add any special instructions based on task type
        if agent_task.task_type.value == "code_review":
            parts.append("\nPlease provide detailed code review feedback including:")
            parts.append("- Code quality and best practices")
            parts.append("- Potential bugs or issues")
            parts.append("- Performance considerations")
            parts.append("- Security concerns")
            
        elif agent_task.task_type.value == "bug_report":
            parts.append("\nPlease investigate this bug report and provide:")
            parts.append("- Root cause analysis")
            parts.append("- Steps to reproduce")
            parts.append("- Proposed fix with code changes")
            parts.append("- Testing recommendations")
        
        return "\n".join(parts)
    
    def _create_collaborative_description(self, agent_task: AgentTask) -> str:
        """Create a description optimized for collaborative work"""
        base_description = self._create_task_description(agent_task)
        
        # Add collaboration instructions
        collab_parts = [
            base_description,
            "\n--- Collaborative Instructions ---",
            f"Primary Agent (@{agent_task.agent_assignment.primary_agent}): Take the lead on this task.",
        ]
        
        if agent_task.agent_assignment.supporting_agents:
            collab_parts.append("Supporting Agents:")
            for agent in agent_task.agent_assignment.supporting_agents:
                if "test" in agent:
                    collab_parts.append(f"- @{agent}: Provide testing and validation")
                elif "code" in agent:
                    collab_parts.append(f"- @{agent}: Assist with implementation")
                elif "product" in agent:
                    collab_parts.append(f"- @{agent}: Ensure requirements are met")
                else:
                    collab_parts.append(f"- @{agent}: Provide domain expertise")
        
        collab_parts.append("\nPlease coordinate your efforts and provide a comprehensive solution.")
        
        return "\n".join(collab_parts)


# Global dispatcher instance
task_dispatcher = TaskDispatcher()