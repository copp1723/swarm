"""
Supermemory Service Integration
Provides persistent memory capabilities for all agents in the MCP Multi-Agent Chat System
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from services.resilient_http_client import SupermemoryClient
from utils.tenacity_retry import retry_memory_operation
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)

@dataclass
class Memory:
    """Represents a memory item"""
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

class SupermemoryService:
    """Service for managing agent memories using Supermemory API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('SUPERMEMORY_API_KEY')
        if not self.api_key:
            raise ValueError("Supermemory API key not provided")
        
        self.base_url = "https://api.supermemory.ai/v3"
        self.client = SupermemoryClient(api_key=self.api_key, base_url=self.base_url)
        
        # Container tags for organizing memories
        self.container_tags = {
            "system": "mcp_agent_system",
            "shared": "shared_knowledge",
            "conversations": "agent_conversations"
        }
    
    @retry_memory_operation(max_attempts=3)
    async def add_memory(self, memory: Memory) -> Dict[str, Any]:
        """Add a memory to Supermemory"""
        try:
            # Prepare the memory document - using memories endpoint
            document = {
                "content": memory.content,
                "type": "text",  # Can be "text", "url", or "file"
                "metadata": {
                    **memory.metadata,
                    "agent_id": memory.agent_id,
                    "conversation_id": memory.conversation_id or "default",
                    "timestamp": memory.timestamp,
                    "source": "mcp_agent_system"
                }
            }
            
            # Add conversation ID as a parameter if available
            if memory.conversation_id:
                document["conversationId"] = memory.conversation_id
            
            # Use resilient client method
            result = await self.client.add_memory(document)
            
            logger.info(f"Memory added successfully: {result.get('id', 'Unknown')}")
            return result
                
        except Exception as e:
            logger.error(f"Error adding memory: {str(e)}")
            raise  # Let retry decorator handle it
    
    @retry_memory_operation(max_attempts=3)
    async def search_memories(
        self, 
        query: str, 
        agent_id: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for relevant memories"""
        try:
            # Supermemory expects 'q' parameter for query
            search_params = {
                "q": query,  # Changed from "query" to "q"
                "limit": limit
            }
            
            results = await self.client.search_memories(query, limit=limit)
            logger.info(f"Found {len(results)} memories for query: {query}")
            return results
                
        except Exception as e:
            logger.error(f"Error searching memories: {str(e)}")
            raise  # Let retry decorator handle it
    
    async def get_agent_memories(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all memories for a specific agent"""
        try:
            response = await self.client.post(
                f"{self.base_url}/documents/list",
                json={
                    "containerTags": [
                        self.container_tags["system"],
                        f"agent_{agent_id}"
                    ],
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get agent memories: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting agent memories: {str(e)}")
            return []
    
    async def share_memory_across_agents(
        self, 
        content: str, 
        source_agent: str,
        target_agents: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Share a memory from one agent to multiple agents"""
        try:
            # Convert target_agents list to string for metadata
            shared_memory = Memory(
                content=content,
                metadata={
                    **(metadata or {}),
                    "source_agent": source_agent,
                    "shared_with": ", ".join(target_agents),  # Convert list to string
                    "shared_at": datetime.now().isoformat()
                },
                agent_id=source_agent,  # Add agent_id
                conversation_id="shared_knowledge",  # Add conversation_id
                timestamp=datetime.now().isoformat(),
                tags=[self.container_tags["shared"]] + [f"agent_{agent}" for agent in target_agents]
            )
            
            return await self.add_memory(shared_memory)
            
        except Exception as e:
            logger.error(f"Error sharing memory: {str(e)}")
            return {"error": str(e)}
    
    async def get_conversation_context(
        self, 
        conversation_id: str, 
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all memories related to a specific conversation"""
        try:
            search_params = {
                "query": f"conversation_id:{conversation_id}",
                "containerTags": [self.container_tags["conversations"]]
            }
            
            if agent_id:
                search_params["containerTags"].append(f"agent_{agent_id}")
            
            response = await self.client.post(
                f"{self.base_url}/search",
                json=search_params
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get conversation context: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return []
    
    async def consolidate_memories(self, agent_id: str, topic: str) -> Dict[str, Any]:
        """Consolidate multiple memories into a summary"""
        try:
            # Search for related memories
            memories = await self.search_memories(topic, agent_id, limit=20)
            
            if not memories:
                return {"message": "No memories found to consolidate"}
            
            # Create a consolidated summary
            summary_content = f"Consolidated knowledge about '{topic}':\n\n"
            for i, memory in enumerate(memories, 1):
                summary_content += f"{i}. {memory.get('content', '')}\n"
            
            # Add the consolidated memory
            consolidated = Memory(
                content=summary_content,
                metadata={
                    "type": "consolidated_summary",
                    "topic": topic,
                    "source_count": len(memories),
                    "consolidation_date": datetime.now().isoformat()
                },
                agent_id=agent_id,
                timestamp=datetime.now().isoformat(),
                tags=["consolidated", f"topic_{topic.replace(' ', '_')}"]
            )
            
            return await self.add_memory(consolidated)
            
        except Exception as e:
            logger.error(f"Error consolidating memories: {str(e)}")
            return {"error": str(e)}
    
    async def create_agent_profile(self, agent_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update an agent's memory profile"""
        try:
            profile_memory = Memory(
                content=json.dumps(profile_data, indent=2),
                metadata={
                    "type": "agent_profile",
                    "agent_id": agent_id,
                    "created_at": datetime.now().isoformat()
                },
                agent_id=agent_id,
                timestamp=datetime.now().isoformat(),
                tags=["agent_profile"]
            )
            
            return await self.add_memory(profile_memory)
            
        except Exception as e:
            logger.error(f"Error creating agent profile: {str(e)}")
            return {"error": str(e)}
    
    async def get_shared_knowledge(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all shared knowledge accessible to all agents"""
        try:
            response = await self.client.post(
                f"{self.base_url}/documents/list",
                json={
                    "containerTags": [
                        self.container_tags["system"],
                        self.container_tags["shared"]
                    ],
                    "limit": limit
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get shared knowledge: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting shared knowledge: {str(e)}")
            return []
    
    async def cleanup_old_memories(self, days_old: int = 30) -> Dict[str, Any]:
        """Clean up old memories (to be implemented based on Supermemory API capabilities)"""
        # Note: This would require a delete endpoint from Supermemory API
        # For now, we'll mark old memories with a cleanup tag
        try:
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            
            # This is a placeholder - actual implementation depends on API capabilities
            return {
                "message": f"Cleanup scheduled for memories older than {days_old} days",
                "status": "pending_api_support"
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up memories: {str(e)}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.close()
    
    # Synchronous wrapper methods for Celery tasks
    def add_memory_sync(self, memory: Memory) -> Dict[str, Any]:
        """Synchronous wrapper for add_memory - used by Celery tasks"""
        return async_manager.run_sync(self.add_memory(memory))
    
    def search_memories_sync(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for search_memories - used by Celery tasks"""
        # Extract agent_id from filters if provided
        agent_id = filters.get('agent_id') if filters else None
        
        return async_manager.run_sync(
            self.search_memories(query, agent_id=agent_id, limit=limit)
        )
    
    def get_agent_memories_sync(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_agent_memories - used by Celery tasks"""
        return async_manager.run_sync(self.get_agent_memories(agent_id, limit))


# Singleton instance
supermemory_service = None

def get_supermemory_service() -> SupermemoryService:
    """Get or create the Supermemory service instance"""
    global supermemory_service
    if supermemory_service is None:
        supermemory_service = SupermemoryService()
    return supermemory_service