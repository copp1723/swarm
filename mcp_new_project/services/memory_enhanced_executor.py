"""
Memory-Enhanced Multi-Agent Executor
Integrates Supermemory capabilities into the multi-agent system
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from services.multi_agent_executor import MultiAgentExecutor, TaskStatus
from services.supermemory_service import get_supermemory_service, Memory

logger = logging.getLogger(__name__)

class MemoryEnhancedExecutor(MultiAgentExecutor):
    """Enhanced executor with Supermemory integration"""
    
    def __init__(self):
        super().__init__()
        self.memory_service = get_supermemory_service()
        self.memory_enabled = True
        
    async def enhance_prompt_with_memories(
        self, 
        agent_id: str, 
        original_prompt: str,
        task_id: Optional[str] = None
    ) -> str:
        """Enhance a prompt with relevant memories"""
        if not self.memory_enabled:
            return original_prompt
        
        try:
            # Search for relevant memories
            memories = await self.memory_service.search_memories(
                query=original_prompt,
                agent_id=agent_id,
                limit=5,
                threshold=0.7
            )
            
            if not memories:
                return original_prompt
            
            # Build enhanced prompt with memory context
            enhanced_prompt = "Based on your previous knowledge:\n\n"
            
            for i, memory in enumerate(memories, 1):
                content = memory.get('content', '')
                score = memory.get('score', 0)
                metadata = memory.get('metadata', {})
                
                # Add relevant memory with context
                enhanced_prompt += f"{i}. [Relevance: {score:.2f}] {content[:200]}..."
                
                # Add metadata context if available
                if metadata.get('conversation_id'):
                    enhanced_prompt += f" (from conversation: {metadata['conversation_id'][:8]}...)"
                
                enhanced_prompt += "\n\n"
            
            enhanced_prompt += f"\nCurrent task: {original_prompt}"
            
            # Store that we used memories for this task
            await self.memory_service.add_memory(Memory(
                content=f"Used {len(memories)} memories to enhance task: {original_prompt[:100]}...",
                metadata={
                    "type": "memory_usage",
                    "task_id": task_id,
                    "memory_count": len(memories)
                },
                agent_id=agent_id,
                timestamp=datetime.now().isoformat()
            ))
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Error enhancing prompt with memories: {str(e)}")
            return original_prompt
    
    async def store_agent_response(
        self,
        agent_id: str,
        task_id: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store an agent's response as a memory"""
        try:
            memory = Memory(
                content=f"Task: {prompt}\n\nResponse: {response}",
                metadata={
                    **(metadata or {}),
                    "type": "agent_response",
                    "task_id": task_id,
                    "prompt": prompt[:200],
                    "response_length": len(response)
                },
                agent_id=agent_id,
                conversation_id=task_id,
                timestamp=datetime.now().isoformat(),
                tags=["agent_response", f"task_{task_id}"]
            )
            
            await self.memory_service.add_memory(memory)
            logger.info(f"Stored response memory for agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Error storing agent response: {str(e)}")
    
    async def execute_task_with_memory(
        self,
        agent_id: str,
        task: str,
        model: Optional[str] = None,
        working_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a task with memory enhancement"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Enhance the prompt with memories
            enhanced_task = await self.enhance_prompt_with_memories(
                agent_id=agent_id,
                original_prompt=task,
                task_id=task_id
            )
            
            # Execute the task with the enhanced prompt
            result = await self.execute_single_agent_task(
                agent_id=agent_id,
                task=enhanced_task,
                model=model
            )
            
            # Store the response as a memory
            if result.get('success') and result.get('response'):
                await self.store_agent_response(
                    agent_id=agent_id,
                    task_id=task_id,
                    prompt=task,
                    response=result['response'],
                    metadata={
                        "model": model,
                        "working_directory": working_directory,
                        "enhanced": enhanced_task != task
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing task with memory: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def share_task_knowledge(
        self,
        task_id: str,
        source_agent: str,
        target_agents: List[str],
        knowledge: str
    ):
        """Share knowledge from a task across multiple agents"""
        try:
            await self.memory_service.share_memory_across_agents(
                content=knowledge,
                source_agent=source_agent,
                target_agents=target_agents,
                metadata={
                    "task_id": task_id,
                    "type": "shared_knowledge",
                    "shared_at": datetime.now().isoformat()
                }
            )
            logger.info(f"Shared knowledge from {source_agent} to {target_agents}")
            
        except Exception as e:
            logger.error(f"Error sharing task knowledge: {str(e)}")
    
    async def create_executive_summary_with_memory(
        self,
        task_id: str,
        task_description: str,
        agent_responses: Dict[str, str]
    ) -> str:
        """Create an executive summary and store it in memory"""
        try:
            # Get existing summaries for similar tasks
            similar_summaries = await self.memory_service.search_memories(
                query=task_description,
                agent_id="general_01",
                limit=3,
                threshold=0.8
            )
            
            # Create context from similar summaries
            context = ""
            if similar_summaries:
                context = "Previous similar task summaries:\n"
                for summary in similar_summaries:
                    context += f"- {summary.get('content', '')[:100]}...\n"
                context += "\n"
            
            # Create the summary (using parent class method)
            summary = await self.create_executive_summary(
                task_description=task_description,
                results=agent_responses
            )
            
            # Store the summary in memory
            await self.memory_service.add_memory(Memory(
                content=summary,
                metadata={
                    "type": "executive_summary",
                    "task_id": task_id,
                    "task_description": task_description,
                    "agent_count": len(agent_responses),
                    "similar_tasks_found": len(similar_summaries)
                },
                agent_id="general_01",
                conversation_id=task_id,
                timestamp=datetime.now().isoformat(),
                tags=["executive_summary", f"task_{task_id}"]
            ))
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating summary with memory: {str(e)}")
            return await self.create_executive_summary(task_description, agent_responses)
    
    async def get_agent_expertise(self, agent_id: str) -> Dict[str, Any]:
        """Get an agent's expertise based on their memory history"""
        try:
            # Get agent's recent memories
            memories = await self.memory_service.get_agent_memories(agent_id, limit=50)
            
            if not memories:
                return {
                    "expertise_areas": [],
                    "task_count": 0,
                    "common_topics": []
                }
            
            # Analyze memories for expertise
            topics = {}
            task_count = 0
            
            for memory in memories:
                metadata = memory.get('metadata', {})
                content = memory.get('content', '')
                
                # Count tasks
                if metadata.get('type') == 'agent_response':
                    task_count += 1
                
                # Extract topics (simple keyword extraction)
                words = content.lower().split()
                for word in words:
                    if len(word) > 5:  # Simple filter for meaningful words
                        topics[word] = topics.get(word, 0) + 1
            
            # Get top topics
            top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "expertise_areas": [topic[0] for topic in top_topics[:5]],
                "task_count": task_count,
                "common_topics": top_topics
            }
            
        except Exception as e:
            logger.error(f"Error getting agent expertise: {str(e)}")
            return {
                "expertise_areas": [],
                "task_count": 0,
                "common_topics": []
            }
    
    async def initialize_agent_profiles(self):
        """Initialize memory profiles for all agents"""
        try:
            from config.agents import AGENT_PROFILES
            
            for agent_id, profile in AGENT_PROFILES.items():
                profile_data = {
                    "agent_id": profile.get('agent_id', agent_id),
                    "name": profile.get('name'),
                    "role": profile.get('role'),
                    "capabilities": profile.get('capabilities', []),
                    "specialties": profile.get('specialties', []),
                    "tools": profile.get('tools', []),
                    "preferred_models": profile.get('preferred_models', []),
                    "initialized_at": datetime.now().isoformat()
                }
                
                await self.memory_service.create_agent_profile(
                    agent_id=profile.get('agent_id', agent_id),
                    profile_data=profile_data
                )
                
                logger.info(f"Initialized memory profile for agent: {agent_id}")
            
        except Exception as e:
            logger.error(f"Error initializing agent profiles: {str(e)}")
    
    async def get_collaborative_context(
        self,
        agents: List[str],
        topic: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get relevant memories from multiple agents for collaboration"""
        context = {}
        
        try:
            for agent_id in agents:
                memories = await self.memory_service.search_memories(
                    query=topic,
                    agent_id=agent_id,
                    limit=3
                )
                context[agent_id] = memories
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting collaborative context: {str(e)}")
            return {}


# Create enhanced executor instance
memory_enhanced_executor = None

def get_memory_enhanced_executor() -> MemoryEnhancedExecutor:
    """Get or create the memory-enhanced executor instance"""
    global memory_enhanced_executor
    if memory_enhanced_executor is None:
        memory_enhanced_executor = MemoryEnhancedExecutor()
    return memory_enhanced_executor