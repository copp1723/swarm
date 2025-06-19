"""Enhanced Multi-Agent Executor with resilience patterns"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.multi_agent_executor import MultiAgentExecutor as BaseExecutor
from utils.circuit_breaker import circuit_manager, CircuitOpenError
from utils.retry_handler import RetryHandler, RetryConfig
from utils.error_catalog import ErrorCodes, format_error_response

logger = logging.getLogger(__name__)


class ResilientMultiAgentExecutor(BaseExecutor):
    """
    Enhanced Multi-Agent Executor with circuit breakers, retry logic, and fallback strategies
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configure retry policies for different scenarios
        self.agent_retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True,
            exceptions=(ConnectionError, TimeoutError, Exception)
        )
        
        self.api_retry_config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True,
            exceptions=(ConnectionError, TimeoutError)
        )
        
        # Agent fallback chains
        self.agent_fallbacks = {
            'coder_01': ['general_01'],  # Fallback to general if coder fails
            'bug_01': ['tester_01', 'general_01'],  # Try tester then general
            'product_01': ['general_01'],
            'tester_01': ['bug_01', 'general_01']
        }
    
    async def _get_agent_response_with_resilience(self, agent_id: str, model: str) -> str:
        """Get agent response with circuit breaker and retry logic"""
        
        # Get or create circuit breaker for this agent
        breaker = circuit_manager.get_or_create(
            f"agent_{agent_id}",
            failure_threshold=3,
            recovery_timeout=60
        )
        
        try:
            # Try the primary agent with circuit breaker
            @RetryHandler.retry(self.agent_retry_config)
            async def call_agent():
                async def agent_call():
                    return await super(ResilientMultiAgentExecutor, self)._get_agent_response(agent_id, model)
                
                return await breaker.call_async(agent_call)
            
            return await call_agent()
            
        except CircuitOpenError as e:
            logger.warning(f"Circuit breaker open for agent {agent_id}: {e}")
            
            # Try fallback agents
            fallback_agents = self.agent_fallbacks.get(agent_id, ['general_01'])
            for fallback_id in fallback_agents:
                try:
                    logger.info(f"Attempting fallback to agent {fallback_id}")
                    fallback_breaker = circuit_manager.get_or_create(
                        f"agent_{fallback_id}",
                        failure_threshold=3,
                        recovery_timeout=60
                    )
                    
                    @RetryHandler.retry(self.agent_retry_config)
                    async def call_fallback():
                        # Use the parent class method to avoid recursion
                        return await super(ResilientMultiAgentExecutor, self)._get_agent_response(fallback_id, model)
                    
                    response = await fallback_breaker.call_async(call_fallback)
                    return f"[Via fallback agent {fallback_id}]\n{response}"
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback agent {fallback_id} also failed: {fallback_error}")
                    continue
            
            # All fallbacks failed
            raise Exception(f"All agents failed for {agent_id}. Primary error: {e}")
            
        except Exception as e:
            logger.error(f"Error getting response from agent {agent_id}: {e}")
            
            # Try fallback agents for other errors too
            fallback_agents = self.agent_fallbacks.get(agent_id, ['general_01'])
            for fallback_id in fallback_agents:
                try:
                    logger.info(f"Attempting fallback to agent {fallback_id} after error")
                    response = await self._get_agent_response_with_resilience(fallback_id, model)
                    return f"[Via fallback agent {fallback_id} due to error: {str(e)[:50]}...]\n{response}"
                except Exception as fallback_error:
                    logger.error(f"Fallback agent {fallback_id} failed: {fallback_error}")
                    continue
            
            # Re-raise if all fallbacks failed
            raise
    
    async def _execute_agent_analysis(self, agent_name: str, model: str, task_description: str,
                                      repo_analysis: Dict, working_directory: str, task_id: str) -> str:
        """Execute agent analysis with enhanced error handling"""
        
        # Create structured prompt (reuse parent logic)
        prompt = await super()._execute_agent_analysis(
            agent_name, model, task_description, repo_analysis, working_directory, task_id
        )
        
        # If that was just preparing prompt, we need to actually call the agent
        # Let's override the actual API call part
        try:
            # Get agent ID for this agent name
            agent_id = self._get_agent_id_by_name(agent_name) or agent_name
            
            # Use resilient version
            if agent_id not in self._agent_chats:
                from routes.agents import AGENT_PROFILES
                agent_config = next(
                    (profile for profile in AGENT_PROFILES.values() if profile['agent_id'] == agent_id),
                    None
                )
                if agent_config:
                    self._agent_chats[agent_id] = [
                        {"role": "system", "content": agent_config.get("default_prompt", "You are an AI assistant.")}
                    ]
            
            # Call with resilience
            response = await self._get_agent_response_with_resilience(agent_id, model)
            
            # Store in chat history
            if agent_id in self._agent_chats:
                self._agent_chats[agent_id].append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            logger.error(f"All attempts failed for agent {agent_name}: {e}")
            # Return error message that can be parsed
            return f"ERROR: Agent {agent_name} failed after all retry attempts and fallbacks: {str(e)}"
    
    async def _analyze_repository_structure_with_retry(self, working_directory: str) -> Dict[str, Any]:
        """Analyze repository with retry logic"""
        
        @RetryHandler.retry(
            max_attempts=3,
            base_delay=1.0,
            exceptions=(OSError, PermissionError, Exception)
        )
        async def analyze():
            return await super()._analyze_repository_structure(working_directory)
        
        try:
            return await analyze()
        except Exception as e:
            logger.error(f"Failed to analyze repository after retries: {e}")
            # Return minimal structure so execution can continue
            return {
                "error": str(e),
                "total_files": 0,
                "file_categories": {"code": []},
                "priority_files": [],
                "warning": "Repository analysis failed, continuing with limited context"
            }
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers"""
        return circuit_manager.get_all_status()
    
    def reset_circuit_breakers(self):
        """Reset all circuit breakers (useful for admin endpoints)"""
        circuit_manager.reset_all()
        logger.info("All circuit breakers have been reset")
    
    async def _execute_structured_task(self, task_id: str, task_description: str,
                                       agent_configs: List[Dict], working_directory: str,
                                       enable_real_time: bool, sequential: bool = False) -> None:
        """Execute task with enhanced error recovery"""
        try:
            # Phase 1: Repository Analysis with retry
            await self._update_task_progress(task_id, 10, "Analyzing Repository Structure")
            repo_analysis = await self._analyze_repository_structure_with_retry(working_directory)
            
            # Continue with parent implementation but use resilient agent calls
            # Store original method reference
            original_get_response = super()._get_agent_response
            
            # Temporarily override to use resilient version
            self._get_agent_response = self._get_agent_response_with_resilience
            
            try:
                # Call parent's structured task execution
                await super()._execute_structured_task(
                    task_id, task_description, agent_configs, 
                    working_directory, enable_real_time, sequential
                )
            finally:
                # Restore original method
                self._get_agent_response = original_get_response
                
        except Exception as e:
            logger.error(f"Task {task_id} failed with enhanced error handling: {e}")
            await self._error_task(task_id, f"Task failed after retry attempts: {str(e)}")
        finally:
            self._running_tasks.pop(task_id, None)


# Export the enhanced executor as the default
MultiAgentExecutor = ResilientMultiAgentExecutor