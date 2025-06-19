"""
Memory Synchronization Tasks
Handles agent memory operations and synchronization
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
from celery import current_task
from config.celery_config import celery_app
from services.supermemory_service import get_supermemory_service, Memory
from utils.retry_config import retry_on_failure

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name='tasks.memory_tasks.sync_agent_memories')
def sync_agent_memories() -> Dict[str, Any]:
    """Synchronous wrapper for async sync_agent_memories."""
    return run_async(_sync_agent_memories_async())


async def _sync_agent_memories_async() -> Dict[str, Any]:
    """
    Periodic task to sync agent memories with Supermemory.
    Runs every 5 minutes via Celery Beat.
    
    Returns:
        Sync statistics
    """
    try:
        logger.info("Starting agent memory synchronization")
        
        memory_service = get_supermemory_service()
        
        # Get list of active agents
        from config.agents import AGENT_PROFILES
        agent_ids = list(AGENT_PROFILES.keys())
        
        sync_results = {}
        total_memories_synced = 0
        
        for agent_id in agent_ids:
            try:
                # Get recent memories for the agent
                memories = await memory_service.get_agent_memories(agent_id, limit=10)
                
                # Sync logic: Check for gaps and ensure consistency
                sync_operations = {
                    'new_memories': 0,
                    'updated_memories': 0,
                    'deleted_memories': 0
                }
                
                # 1. Check for memories that need to be updated
                for memory in memories:
                    memory_id = memory.get('id')
                    memory_timestamp = memory.get('timestamp')
                    
                    # Check if memory needs updating based on timestamp
                    if memory_timestamp:
                        # If memory is older than 24 hours, mark for refresh
                        memory_age = (datetime.utcnow() - datetime.fromisoformat(memory_timestamp.replace('Z', '+00:00'))).total_seconds()
                        if memory_age > 86400:  # 24 hours
                            # Refresh memory content
                            await memory_service.refresh_memory(agent_id, memory_id)
                            sync_operations['updated_memories'] += 1
                
                # 2. Check for orphaned memories (memories without associated tasks)
                orphaned_memories = await memory_service.find_orphaned_memories(agent_id)
                if orphaned_memories:
                    for orphaned in orphaned_memories:
                        await memory_service.delete_memory(agent_id, orphaned['id'])
                        sync_operations['deleted_memories'] += 1
                
                # 3. Ensure agent has recent context memories
                recent_tasks = await _get_recent_agent_tasks(agent_id, limit=5)
                for task in recent_tasks:
                    # Check if task has associated memory
                    task_memory = await memory_service.find_memory_by_task(agent_id, task['id'])
                    if not task_memory:
                        # Create memory for task
                        await memory_service.create_memory(
                            agent_id=agent_id,
                            content=f"Task: {task['title']}\nDescription: {task['description']}\nStatus: {task['status']}",
                            metadata={
                                'task_id': task['id'],
                                'task_type': task.get('type', 'general'),
                                'created_from': 'sync_operation'
                            }
                        )
                        sync_operations['new_memories'] += 1
                
                # 4. Deduplicate similar memories
                duplicates = await memory_service.find_duplicate_memories(agent_id)
                for dup_group in duplicates:
                    # Keep the most recent, delete others
                    sorted_dups = sorted(dup_group, key=lambda x: x.get('timestamp', ''), reverse=True)
                    for dup in sorted_dups[1:]:  # Skip the first (most recent)
                        await memory_service.delete_memory(agent_id, dup['id'])
                        sync_operations['deleted_memories'] += 1
                
                sync_results[agent_id] = {
                    'status': 'success',
                    'memories_found': len(memories),
                    'sync_operations': sync_operations
                }
                total_memories_synced += len(memories)
                
            except Exception as e:
                logger.error(f"Error syncing memories for agent {agent_id}: {e}")
                sync_results[agent_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'agents_synced': len(agent_ids),
            'total_memories': total_memories_synced,
            'agent_results': sync_results
        }
        
    except Exception as e:
        logger.error(f"Error in memory sync task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, name='tasks.memory_tasks.consolidate_agent_memories')
@retry_on_failure(max_retries=3)
def consolidate_agent_memories(
    self,
    agent_id: str,
    topic: str,
    time_range_days: int = 7
) -> Dict[str, Any]:
    """Synchronous wrapper for async consolidate_agent_memories."""
    return run_async(_consolidate_agent_memories_async(self, agent_id, topic, time_range_days))


async def _consolidate_agent_memories_async(
    self,
    agent_id: str,
    topic: str,
    time_range_days: int = 7
) -> Dict[str, Any]:
    """
    Consolidate memories for a specific agent and topic.
    
    Args:
        agent_id: ID of the agent
        topic: Topic to consolidate memories about
        time_range_days: Number of days to look back
        
    Returns:
        Consolidation results
    """
    try:
        memory_service = get_supermemory_service()
        
        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'current': 'Consolidating memories', 'total': 100}
        )
        
        # Perform consolidation
        result = await memory_service.consolidate_memories(agent_id, topic)
        
        if 'error' in result:
            raise Exception(result['error'])
        
        return {
            'success': True,
            'agent_id': agent_id,
            'topic': topic,
            'consolidation_result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error consolidating memories: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        return {
            'success': False,
            'error': str(e),
            'agent_id': agent_id,
            'topic': topic
        }


@celery_app.task(name='tasks.memory_tasks.share_memory_batch')
def share_memory_batch(
    memories: List[Dict[str, Any]],
    source_agent: str,
    target_agents: List[str]
) -> Dict[str, Any]:
    """Synchronous wrapper for async share_memory_batch."""
    return run_async(_share_memory_batch_async(memories, source_agent, target_agents))


async def _share_memory_batch_async(
    memories: List[Dict[str, Any]],
    source_agent: str,
    target_agents: List[str]
) -> Dict[str, Any]:
    """
    Share a batch of memories from one agent to others.
    
    Args:
        memories: List of memory dictionaries to share
        source_agent: Source agent ID
        target_agents: List of target agent IDs
        
    Returns:
        Sharing results
    """
    try:
        memory_service = get_supermemory_service()
        
        results = []
        successful = 0
        
        for memory_data in memories:
            try:
                result = await memory_service.share_memory_across_agents(
                    content=memory_data.get('content', ''),
                    source_agent=source_agent,
                    target_agents=target_agents,
                    metadata=memory_data.get('metadata', {})
                )
                
                if 'error' not in result:
                    successful += 1
                    results.append({'status': 'success', 'memory_id': result.get('id')})
                else:
                    results.append({'status': 'error', 'error': result['error']})
                    
            except Exception as e:
                logger.error(f"Error sharing memory: {e}")
                results.append({'status': 'error', 'error': str(e)})
        
        return {
            'success': True,
            'total': len(memories),
            'successful': successful,
            'failed': len(memories) - successful,
            'source_agent': source_agent,
            'target_agents': target_agents,
            'results': results,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in batch memory sharing: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(name='tasks.memory_tasks.export_agent_memories')
def export_agent_memories(
    agent_id: str,
    format: str = 'json',
    include_metadata: bool = True
) -> Dict[str, Any]:
    """Synchronous wrapper for async export_agent_memories."""
    return run_async(_export_agent_memories_async(agent_id, format, include_metadata))


async def _export_agent_memories_async(
    agent_id: str,
    format: str = 'json',
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Export all memories for an agent.
    
    Args:
        agent_id: Agent ID to export memories for
        format: Export format (json, csv, markdown)
        include_metadata: Whether to include metadata
        
    Returns:
        Export results with file location
    """
    try:
        memory_service = get_supermemory_service()
        
        # Get all memories for the agent
        memories = await memory_service.get_agent_memories(agent_id, limit=1000)
        
        if not memories:
            return {
                'success': True,
                'message': 'No memories to export',
                'agent_id': agent_id
            }
        
        # Prepare export data
        export_data = []
        for memory in memories:
            item = {
                'content': memory.get('content', ''),
                'timestamp': memory.get('timestamp', '')
            }
            
            if include_metadata:
                item['metadata'] = memory.get('metadata', {})
            
            export_data.append(item)
        
        # Export based on format
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"agent_{agent_id}_memories_{timestamp}.{format}"
        filepath = f"exports/{filename}"
        
        # Create exports directory if needed
        import os
        os.makedirs('exports', exist_ok=True)
        
        if format == 'json':
            import json
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        elif format == 'csv':
            import csv
            with open(filepath, 'w', newline='') as f:
                if export_data:
                    writer = csv.DictWriter(f, fieldnames=export_data[0].keys())
                    writer.writeheader()
                    writer.writerows(export_data)
        
        elif format == 'markdown':
            with open(filepath, 'w') as f:
                f.write(f"# Agent {agent_id} Memories\n\n")
                f.write(f"Exported on: {datetime.utcnow().isoformat()}\n\n")
                
                for i, item in enumerate(export_data, 1):
                    f.write(f"## Memory {i}\n\n")
                    f.write(f"**Content:** {item['content']}\n\n")
                    f.write(f"**Timestamp:** {item['timestamp']}\n\n")
                    if include_metadata and item.get('metadata'):
                        f.write("**Metadata:**\n")
                        for key, value in item['metadata'].items():
                            f.write(f"- {key}: {value}\n")
                        f.write("\n")
                    f.write("---\n\n")
        
        return {
            'success': True,
            'agent_id': agent_id,
            'memories_exported': len(export_data),
            'format': format,
            'filepath': filepath,
            'filesize': os.path.getsize(filepath),
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error exporting memories: {e}")
        return {
            'success': False,
            'error': str(e),
            'agent_id': agent_id
        }


@celery_app.task(name='tasks.memory_tasks.analyze_agent_expertise')
def analyze_agent_expertise(agent_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for async analyze_agent_expertise."""
    return run_async(_analyze_agent_expertise_async(agent_id))


async def _analyze_agent_expertise_async(agent_id: str) -> Dict[str, Any]:
    """
    Analyze an agent's expertise based on memory history.
    
    Args:
        agent_id: Agent ID to analyze
        
    Returns:
        Expertise analysis results
    """
    try:
        from services.memory_enhanced_executor import get_memory_enhanced_executor
        
        executor = get_memory_enhanced_executor()
        expertise = await executor.get_agent_expertise(agent_id)
        
        # Additional analysis
        memory_service = get_supermemory_service()
        recent_memories = await memory_service.get_agent_memories(agent_id, limit=50)
        
        # Analyze memory patterns
        memory_types = {}
        topics_frequency = {}
        
        for memory in recent_memories:
            metadata = memory.get('metadata', {})
            
            # Count memory types
            mem_type = metadata.get('type', 'unknown')
            memory_types[mem_type] = memory_types.get(mem_type, 0) + 1
            
            # Extract topics from content
            content = memory.get('content', '').lower()
            # Simple keyword extraction (could be enhanced with NLP)
            for word in content.split():
                if len(word) > 5 and word.isalnum():
                    topics_frequency[word] = topics_frequency.get(word, 0) + 1
        
        # Get top topics
        top_topics = sorted(
            topics_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]
        
        return {
            'success': True,
            'agent_id': agent_id,
            'expertise': expertise,
            'memory_analysis': {
                'total_memories': len(recent_memories),
                'memory_types': memory_types,
                'top_topics': dict(top_topics)
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing agent expertise: {e}")
        return {
            'success': False,
            'error': str(e),
            'agent_id': agent_id
        }


async def _get_recent_agent_tasks(agent_id: str, limit: int = 5) -> list:
    """Helper method to get recent tasks for an agent"""
    try:
        # Import task service or database models
        from services.service_container import get_service_container
        container = get_service_container()
        
        # Try to get multi-agent service
        try:
            multi_agent_service = container.get("multi_agent_task_service")
            # Get recent tasks assigned to this agent
            tasks = await multi_agent_service.get_agent_tasks(agent_id, limit=limit)
            return tasks
        except:
            # Fallback to empty list if service not available
            logger.warning(f"Could not retrieve tasks for agent {agent_id}")
            return []
    except Exception as e:
        logger.error(f"Error getting recent tasks: {e}")
        return []
