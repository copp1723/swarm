"""Enhanced Multi-Agent Executor with resilience patterns"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from services.multi_agent_executor import MultiAgentExecutor
from utils.circuit_breaker import circuit_manager, CircuitOpenError
from utils.retry_handler import RetryHandler
from utils.dead_letter_queue import DeadLetterQueue
from utils.logging_config import get_logger
from models.core import db

logger = get_logger(__name__)


class EnhancedMultiAgentExecutor(MultiAgentExecutor):
    """
    Enhanced executor with circuit breakers, retries, and dead letter queue
    """
    
    def __init__(self):
        super().__init__()
        self.dlq = DeadLetterQueue()
        self.fallback_agents = {
            'coder_01': 'product_01',
            'bug_01': 'tester_01',
            'tester_01': 'bug_01'
        }
        
    def get_circuit_breaker_name(self, agent_id: str) -> str:
        """Get circuit breaker name for an agent"""
        return f"agent_{agent_id}"
    
    async def execute_agent_with_resilience(self, 
                                          agent_id: str,
                                          task: str,
                                          task_id: str,
                                          context: Optional[Dict] = None,
                                          priority: str = 'normal') -> Dict[str, Any]:
        """
        Execute agent task with full resilience stack
        
        Args:
            agent_id: Agent to execute
            task: Task description
            task_id: Unique task ID
            context: Optional context
            priority: Task priority
            
        Returns:
            Execution result
        """
        circuit_breaker = circuit_manager.get_or_create(
            self.get_circuit_breaker_name(agent_id),
            failure_threshold=3,
            recovery_timeout=30
        )
        
        # Define retry strategy
        @RetryHandler.async_retry(
            max_attempts=3,
            base_delay=2,
            max_delay=10,
            jitter=True,
            on_retry=lambda attempt, error, delay: logger.warning(
                f"Retrying agent {agent_id} (attempt {attempt}): {error}"
            )
        )
        async def execute_with_retry():
            try:
                # Execute through circuit breaker
                return await circuit_breaker.call_async(
                    self._execute_agent_task,
                    agent_id,
                    task,
                    context
                )
            except CircuitOpenError:
                # Try fallback agent if circuit is open
                fallback = self.fallback_agents.get(agent_id)
                if fallback:
                    logger.warning(
                        f"Circuit open for {agent_id}, trying fallback {fallback}"
                    )
                    fallback_breaker = circuit_manager.get_or_create(
                        self.get_circuit_breaker_name(fallback),
                        failure_threshold=3,
                        recovery_timeout=30
                    )
                    return await fallback_breaker.call_async(
                        self._execute_agent_task,
                        fallback,
                        task,
                        context
                    )
                raise
        
        try:
            # Execute with full resilience
            result = await execute_with_retry()
            return result
            
        except Exception as e:
            # Add to dead letter queue
            logger.error(f"Agent {agent_id} failed all retries for task {task_id}: {e}")
            
            await self.dlq.add_failed_task(
                task_id=task_id,
                agent_id=agent_id,
                task_data={
                    'task': task,
                    'context': context
                },
                error=e,
                attempt_count=3,
                priority=priority
            )
            
            # Return error result
            return {
                'success': False,
                'error': str(e),
                'agent': agent_id,
                'dlq_id': task_id
            }
    
    async def _execute_agent_task(self, agent_id: str, task: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Internal method to execute agent task"""
        # This would be the actual agent execution logic
        # For now, simulate with the parent class method
        
        # Map to role format expected by parent class
        role = agent_id.split('_')[0]  # Extract role from agent_id
        
        # Use parent class execution (simplified)
        messages = []
        if context:
            messages.append({
                "role": "system",
                "content": f"Context: {context}"
            })
        
        messages.append({
            "role": "user",
            "content": task
        })
        
        # Simulate execution (in real implementation, this would call the actual agent)
        return {
            'success': True,
            'agent': agent_id,
            'response': f"Task executed by {agent_id}",
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def process_dlq_tasks(self, max_tasks: int = 10):
        """Process tasks from the dead letter queue"""
        logger.info(f"Processing up to {max_tasks} tasks from DLQ")
        
        failed_tasks = await self.dlq.retry_failed_tasks(max_tasks)
        results = []
        
        for task_info in failed_tasks:
            try:
                # Retry the task
                result = await self.execute_agent_with_resilience(
                    agent_id=task_info['agent_id'],
                    task=task_info['task_data']['task'],
                    task_id=task_info['task_id'],
                    context=task_info['task_data'].get('context'),
                    priority=task_info.get('priority', 'normal')
                )
                
                results.append({
                    'task_id': task_info['task_id'],
                    'success': result.get('success', False),
                    'result': result
                })
                
                # If still failing after max attempts, mark as abandoned
                if not result.get('success') and task_info['attempt_count'] >= 5:
                    await self.dlq.mark_task_abandoned(
                        task_info['id'],
                        "Maximum retry attempts exceeded"
                    )
                    
            except Exception as e:
                logger.error(f"Failed to process DLQ task {task_info['task_id']}: {e}")
                results.append({
                    'task_id': task_info['task_id'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status including circuit breakers and DLQ"""
        health = {
            'executor': 'enhanced',
            'timestamp': datetime.utcnow().isoformat(),
            'circuit_breakers': circuit_manager.get_all_status(),
            'dlq_stats': asyncio.run(self.dlq.get_dlq_stats()),
            'active_tasks': len(self.task_storage)
        }
        
        # Determine overall health
        open_circuits = sum(
            1 for breaker in health['circuit_breakers'].values()
            if breaker['state'] == 'open'
        )
        
        if open_circuits > len(health['circuit_breakers']) / 2:
            health['status'] = 'degraded'
            health['message'] = f"{open_circuits} circuit breakers are open"
        elif health['dlq_stats']['total_failed'] > 100:
            health['status'] = 'warning'
            health['message'] = f"{health['dlq_stats']['total_failed']} tasks in DLQ"
        else:
            health['status'] = 'healthy'
            health['message'] = 'All systems operational'
        
        return health
    
    async def execute_with_auto_recovery(self, agents: List[str], task: str, task_id: str) -> Dict[str, Any]:
        """
        Execute task with automatic fallback and recovery
        
        Args:
            agents: List of agents to try in order
            task: Task to execute
            task_id: Task ID
            
        Returns:
            First successful result or final error
        """
        errors = []
        
        for agent_id in agents:
            try:
                result = await self.execute_agent_with_resilience(
                    agent_id=agent_id,
                    task=task,
                    task_id=task_id,
                    priority='high'
                )
                
                if result.get('success'):
                    return result
                else:
                    errors.append(f"{agent_id}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                errors.append(f"{agent_id}: {str(e)}")
                logger.error(f"Agent {agent_id} failed: {e}")
        
        # All agents failed
        return {
            'success': False,
            'error': 'All agents failed',
            'details': errors,
            'task_id': task_id
        }


# Global enhanced executor instance
enhanced_executor = None

def get_enhanced_executor() -> EnhancedMultiAgentExecutor:
    """Get or create the enhanced executor instance"""
    global enhanced_executor
    if enhanced_executor is None:
        enhanced_executor = EnhancedMultiAgentExecutor()
    return enhanced_executor