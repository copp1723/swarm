"""
Zen + Memory Enhanced Multi-Agent Executor
Combines Supermemory persistence with Zen MCP's multi-model capabilities
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from services.memory_enhanced_executor import MemoryEnhancedExecutor
from services.zen_mcp_service import get_zen_service
from services.supermemory_service import Memory

logger = logging.getLogger(__name__)

class ZenMemoryExecutor(MemoryEnhancedExecutor):
    """Enhanced executor with both Zen MCP and Supermemory capabilities"""
    
    def __init__(self):
        super().__init__()
        self.zen_service = get_zen_service()
        self.zen_enabled = self.zen_service.enabled
        
    async def execute_with_zen_enhancement(
        self,
        agent_id: str,
        task: str,
        model: Optional[str] = None,
        working_directory: Optional[str] = None,
        use_zen: bool = True
    ) -> Dict[str, Any]:
        """Execute a task with both memory and Zen enhancements"""
        task_id = f"zen_task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # First, enhance with memories
            memory_enhanced_task = await self.enhance_prompt_with_memories(
                agent_id=agent_id,
                original_prompt=task,
                task_id=task_id
            )
            
            # Then, if Zen is available and requested, get multi-model insights
            if use_zen and self.zen_enabled and await self.zen_service.is_available():
                zen_insights = await self.zen_service.multi_model_query(memory_enhanced_task)
                
                if 'error' not in zen_insights:
                    # Add Zen insights to the context
                    enhanced_task = f"""Based on multi-model analysis:
{zen_insights.get('consensus', zen_insights.get('response', ''))}

Your specific task: {memory_enhanced_task}"""
                    
                    # Store the Zen insights as a memory
                    await self.memory_service.add_memory(Memory(
                        content=f"Zen insights for task: {task[:100]}...\n{zen_insights.get('consensus', '')}",
                        metadata={
                            "type": "zen_insight",
                            "task_id": task_id,
                            "models_used": len(zen_insights.get('individual_responses', []))
                        },
                        agent_id=agent_id,
                        conversation_id=task_id,
                        timestamp=datetime.now().isoformat()
                    ))
                else:
                    enhanced_task = memory_enhanced_task
            else:
                enhanced_task = memory_enhanced_task
            
            # Execute the task
            result = await self.execute_single_agent_task(
                agent_id=agent_id,
                task=enhanced_task,
                model=model
            )
            
            # Store the response
            if result.get('success') and result.get('response'):
                await self.store_agent_response(
                    agent_id=agent_id,
                    task_id=task_id,
                    prompt=task,
                    response=result['response'],
                    metadata={
                        "model": model,
                        "working_directory": working_directory,
                        "memory_enhanced": memory_enhanced_task != task,
                        "zen_enhanced": use_zen and self.zen_enabled
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing task with Zen enhancement: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def code_review_with_memory(
        self,
        agent_id: str,
        code_path: str,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform code review using Zen and store insights in memory"""
        try:
            # Check for previous reviews of this file
            past_reviews = await self.memory_service.search_memories(
                query=f"code review {code_path}",
                agent_id=agent_id,
                limit=3
            )
            
            # Perform Zen code review
            if self.zen_enabled and await self.zen_service.is_available():
                review_result = await self.zen_service.code_review(code_path, focus_areas)
                
                if 'error' not in review_result:
                    # Store the review in memory
                    await self.memory_service.add_memory(Memory(
                        content=f"Code review of {code_path}: {review_result.get('summary', '')}",
                        metadata={
                            "type": "code_review",
                            "file_path": code_path,
                            "issues_found": review_result.get('issues_count', 0),
                            "suggestions": review_result.get('suggestions', [])
                        },
                        agent_id=agent_id,
                        timestamp=datetime.now().isoformat()
                    ))
                    
                    # Add context from past reviews
                    if past_reviews:
                        review_result['past_reviews'] = [
                            {
                                "date": r.get('metadata', {}).get('timestamp'),
                                "summary": r.get('content', '')[:200]
                            } for r in past_reviews
                        ]
                    
                    return review_result
                else:
                    return review_result
            else:
                return {
                    "error": "Zen code review not available",
                    "suggestion": "Enable Zen MCP for advanced code review capabilities"
                }
                
        except Exception as e:
            logger.error(f"Error in code review with memory: {str(e)}")
            return {"error": str(e)}
    
    async def debug_with_context(
        self,
        agent_id: str,
        error_message: str,
        code_context: str,
        stack_trace: Optional[str] = None
    ) -> Dict[str, Any]:
        """Debug an error using Zen and relevant memories"""
        try:
            # Search for similar errors in memory
            similar_errors = await self.memory_service.search_memories(
                query=error_message,
                agent_id=agent_id,
                limit=5
            )
            
            # Build enhanced context
            enhanced_context = code_context
            if similar_errors:
                enhanced_context += "\n\nSimilar errors encountered before:\n"
                for error in similar_errors:
                    enhanced_context += f"- {error.get('content', '')[:100]}...\n"
            
            # Use Zen for debugging
            if self.zen_enabled and await self.zen_service.is_available():
                debug_result = await self.zen_service.debug(
                    error_message=error_message,
                    code_context=enhanced_context,
                    stack_trace=stack_trace
                )
                
                if 'error' not in debug_result:
                    # Store the debugging session
                    await self.memory_service.add_memory(Memory(
                        content=f"Debug session: {error_message}\nRoot cause: {debug_result.get('root_cause', 'Unknown')}",
                        metadata={
                            "type": "debug_session",
                            "error": error_message,
                            "solution": debug_result.get('solution', ''),
                            "prevention": debug_result.get('prevention', '')
                        },
                        agent_id=agent_id,
                        timestamp=datetime.now().isoformat()
                    ))
                    
                    return debug_result
                else:
                    return debug_result
            else:
                # Fallback to memory-based debugging
                if similar_errors:
                    return {
                        "similar_errors_found": len(similar_errors),
                        "suggestions": [e.get('metadata', {}).get('solution', '') for e in similar_errors if e.get('metadata', {}).get('solution')],
                        "note": "Enable Zen MCP for advanced debugging capabilities"
                    }
                else:
                    return {
                        "error": "No debugging insights available",
                        "suggestion": "Enable Zen MCP for root cause analysis"
                    }
                    
        except Exception as e:
            logger.error(f"Error in debug with context: {str(e)}")
            return {"error": str(e)}
    
    async def collaborative_planning(
        self,
        task_description: str,
        agent_ids: List[str],
        requirements: List[str],
        constraints: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a collaborative plan using multiple agents, Zen, and shared memories"""
        try:
            task_id = f"collab_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Get relevant memories from all participating agents
            agent_contexts = {}
            for agent_id in agent_ids:
                memories = await self.memory_service.search_memories(
                    query=task_description,
                    agent_id=agent_id,
                    limit=3
                )
                agent_contexts[agent_id] = memories
            
            # Use Zen planner if available
            if self.zen_enabled and await self.zen_service.is_available():
                plan_result = await self.zen_service.planner(
                    project_description=task_description,
                    requirements=requirements,
                    constraints=constraints
                )
                
                if 'error' not in plan_result:
                    # Get agent perspectives on the plan
                    agent_perspectives = []
                    for agent_id in agent_ids:
                        agent_response = await self.execute_with_zen_enhancement(
                            agent_id=agent_id,
                            task=f"Review this plan and provide your expertise: {plan_result.get('plan', '')}",
                            use_zen=False  # Avoid recursive Zen calls
                        )
                        
                        if agent_response.get('success'):
                            agent_perspectives.append({
                                "agent": agent_id,
                                "perspective": agent_response.get('response', '')
                            })
                    
                    # Build consensus on the plan
                    if agent_perspectives and self.zen_enabled:
                        consensus = await self.zen_service.consensus(
                            question=f"Based on these perspectives, what's the best approach for: {task_description}",
                            perspectives=agent_perspectives
                        )
                        
                        final_plan = {
                            "initial_plan": plan_result,
                            "agent_perspectives": agent_perspectives,
                            "consensus": consensus.get('result', ''),
                            "task_id": task_id
                        }
                    else:
                        final_plan = plan_result
                    
                    # Share the plan as memory across all agents
                    await self.memory_service.share_memory_across_agents(
                        content=f"Collaborative plan for: {task_description}\n{final_plan.get('consensus', plan_result.get('plan', ''))}",
                        source_agent="planner",
                        target_agents=agent_ids,
                        metadata={
                            "type": "collaborative_plan",
                            "task_id": task_id,
                            "requirements": requirements
                        }
                    )
                    
                    return final_plan
                else:
                    return plan_result
            else:
                # Fallback to memory-based planning
                return await self.create_executive_summary_with_memory(
                    task_id=task_id,
                    task_description=f"Create a plan for: {task_description}",
                    agent_responses={
                        agent_id: f"Based on experience: {agent_contexts[agent_id]}"
                        for agent_id in agent_ids
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in collaborative planning: {str(e)}")
            return {"error": str(e)}
    
    async def get_enhanced_agent_profile(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive agent profile with expertise and capabilities"""
        try:
            # Get basic expertise from memory
            expertise = await self.get_agent_expertise(agent_id)
            
            # Get agent configuration
            from config.agents import AGENT_PROFILES
            agent_config = AGENT_PROFILES.get(agent_id, {})
            
            # Determine Zen tool availability for this agent
            zen_tools = []
            if self.zen_enabled:
                role = agent_config.get('role', '')
                if role == 'coder':
                    zen_tools = ['codereview', 'refactor', 'analyze', 'tracer']
                elif role == 'bug':
                    zen_tools = ['debug', 'tracer']
                elif role == 'product':
                    zen_tools = ['planner', 'consensus', 'thinkdeep']
                elif role == 'devops':
                    zen_tools = ['analyze', 'debug']
                else:
                    zen_tools = ['chat', 'thinkdeep']
            
            return {
                "agent_id": agent_id,
                "name": agent_config.get('name', agent_id),
                "role": agent_config.get('role', 'general'),
                "description": agent_config.get('description', ''),
                "memory_profile": expertise,
                "capabilities": agent_config.get('capabilities', []),
                "tools": {
                    "standard": agent_config.get('tools', []),
                    "zen": zen_tools,
                    "memory": ["search", "store", "share"]
                },
                "interaction_style": agent_config.get('interaction_style', ''),
                "enhancements": {
                    "memory_enabled": self.memory_enabled,
                    "zen_enabled": self.zen_enabled and len(zen_tools) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting enhanced agent profile: {str(e)}")
            return {
                "agent_id": agent_id,
                "error": str(e)
            }


# Create enhanced executor instance
zen_memory_executor = None

def get_zen_memory_executor() -> ZenMemoryExecutor:
    """Get or create the Zen + Memory enhanced executor instance"""
    global zen_memory_executor
    if zen_memory_executor is None:
        zen_memory_executor = ZenMemoryExecutor()
    return zen_memory_executor