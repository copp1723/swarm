"""
Memory API Routes
REST endpoints for Supermemory integration with agent-specific contexts
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

from utils.logging_config import get_logger
from utils.auth import require_auth
from utils.rate_limiter import rate_limit
from utils.async_wrapper import async_manager
from services.supermemory_service import SupermemoryService, Memory
from core.service_registry import get_service

logger = get_logger(__name__)

memory_api_bp = Blueprint('memory_api', __name__, url_prefix='/api/memory')


@memory_api_bp.route('/add', methods=['POST'])
@require_auth
@rate_limit(requests_per_minute=30)
@async_manager.async_route
async def add_memory():
    """
    Add a memory to Supermemory with agent context.
    
    Request body:
    {
        "content": "Memory content",
        "agent_id": "DEVELOPER",
        "conversation_id": "conv_123",
        "metadata": {
            "category": "code_review",
            "importance": "high"
        },
        "tags": ["python", "optimization"]
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('content'):
            return jsonify({'error': 'Content is required'}), 400
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Create memory object
        memory = Memory(
            content=data['content'],
            agent_id=data.get('agent_id'),
            conversation_id=data.get('conversation_id'),
            metadata=data.get('metadata', {}),
            tags=data.get('tags', []),
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Add memory
        result = await supermemory.add_memory(memory)
        
        return jsonify({
            'success': True,
            'memory_id': result.get('id'),
            'timestamp': memory.timestamp
        }), 201
        
    except Exception as e:
        logger.error(f"Error adding memory: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/search', methods=['GET', 'POST'])
@require_auth
@rate_limit(requests_per_minute=50)
@async_manager.async_route
async def search_memories():
    """
    Search memories with optional agent context.
    
    Query parameters or JSON body:
    - query: Search query
    - agent_id: Filter by agent
    - limit: Max results (default 10)
    - threshold: Relevance threshold (0-1)
    """
    try:
        # Support both GET and POST
        if request.method == 'GET':
            query = request.args.get('query', '')
            agent_id = request.args.get('agent_id')
            limit = int(request.args.get('limit', 10))
            threshold = float(request.args.get('threshold', 0.7))
        else:
            data = request.get_json()
            query = data.get('query', '')
            agent_id = data.get('agent_id')
            limit = data.get('limit', 10)
            threshold = data.get('threshold', 0.7)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Search memories
        results = await supermemory.search_memories(
            query=query,
            agent_id=agent_id,
            limit=limit,
            threshold=threshold
        )
        
        return jsonify({
            'query': query,
            'agent_id': agent_id,
            'count': len(results),
            'memories': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/agent/<agent_id>', methods=['GET'])
@require_auth
@rate_limit(requests_per_minute=30)
@async_manager.async_route
async def get_agent_memories(agent_id: str):
    """
    Get all memories for a specific agent.
    
    Query parameters:
    - limit: Max results (default 50)
    """
    try:
        limit = int(request.args.get('limit', 50))
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Get agent memories
        memories = await supermemory.get_agent_memories(agent_id, limit=limit)
        
        return jsonify({
            'agent_id': agent_id,
            'count': len(memories),
            'memories': memories
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting agent memories: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/share', methods=['POST'])
@require_auth
@rate_limit(requests_per_minute=20)
@async_manager.async_route
async def share_memory():
    """
    Share a memory across multiple agents.
    
    Request body:
    {
        "content": "Shared knowledge",
        "source_agent": "DEVELOPER",
        "target_agents": ["PRODUCT", "BUG"],
        "metadata": {
            "importance": "high",
            "category": "best_practice"
        }
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['content', 'source_agent', 'target_agents']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return jsonify({'error': f'Missing required fields: {missing}'}), 400
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Share memory
        result = await supermemory.share_memory_across_agents(
            content=data['content'],
            source_agent=data['source_agent'],
            target_agents=data['target_agents'],
            metadata=data.get('metadata', {})
        )
        
        return jsonify({
            'success': True,
            'shared_with': data['target_agents'],
            'result': result
        }), 201
        
    except Exception as e:
        logger.error(f"Error sharing memory: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/conversation/<conversation_id>', methods=['GET'])
@require_auth
@rate_limit(requests_per_minute=30)
@async_manager.async_route
async def get_conversation_context(conversation_id: str):
    """
    Get all memories for a specific conversation.
    
    Query parameters:
    - agent_id: Filter by agent (optional)
    """
    try:
        agent_id = request.args.get('agent_id')
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Get conversation context
        memories = await supermemory.get_conversation_context(
            conversation_id=conversation_id,
            agent_id=agent_id
        )
        
        return jsonify({
            'conversation_id': conversation_id,
            'agent_id': agent_id,
            'count': len(memories),
            'memories': memories
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/consolidate', methods=['POST'])
@require_auth
@rate_limit(requests_per_minute=10)
@async_manager.async_route
async def consolidate_memories():
    """
    Consolidate memories on a topic into a summary.
    
    Request body:
    {
        "agent_id": "DEVELOPER",
        "topic": "Python optimization techniques"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('agent_id') or not data.get('topic'):
            return jsonify({'error': 'agent_id and topic are required'}), 400
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Consolidate memories
        result = await supermemory.consolidate_memories(
            agent_id=data['agent_id'],
            topic=data['topic']
        )
        
        return jsonify({
            'success': True,
            'agent_id': data['agent_id'],
            'topic': data['topic'],
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error consolidating memories: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/agent/<agent_id>/profile', methods=['GET', 'POST'])
@require_auth
@rate_limit(requests_per_minute=20)
@async_manager.async_route
async def agent_profile(agent_id: str):
    """
    Get or update an agent's memory profile.
    
    GET: Retrieve profile
    POST: Create/update profile with body:
    {
        "capabilities": ["code_review", "optimization"],
        "preferences": {
            "language": "python",
            "style": "pep8"
        },
        "knowledge_areas": ["web_development", "data_science"]
    }
    """
    try:
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        if request.method == 'POST':
            # Create/update profile
            profile_data = request.get_json()
            
            result = await supermemory.create_agent_profile(
                agent_id=agent_id,
                profile_data=profile_data
            )
            
            return jsonify({
                'success': True,
                'agent_id': agent_id,
                'profile': profile_data,
                'result': result
            }), 201
        
        else:  # GET
            # Search for agent profile
            memories = await supermemory.search_memories(
                query=f"agent_profile {agent_id}",
                agent_id=agent_id,
                limit=1
            )
            
            if memories:
                # Parse the profile from memory content
                try:
                    profile = json.loads(memories[0].get('content', '{}'))
                except:
                    profile = {}
            else:
                profile = None
            
            return jsonify({
                'agent_id': agent_id,
                'profile': profile,
                'found': profile is not None
            }), 200
            
    except Exception as e:
        logger.error(f"Error with agent profile: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/shared', methods=['GET'])
@require_auth
@rate_limit(requests_per_minute=30)
@async_manager.async_route
async def get_shared_knowledge():
    """
    Get all shared knowledge accessible to all agents.
    
    Query parameters:
    - limit: Max results (default 20)
    """
    try:
        limit = int(request.args.get('limit', 20))
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Get shared knowledge
        memories = await supermemory.get_shared_knowledge(limit=limit)
        
        return jsonify({
            'count': len(memories),
            'memories': memories
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting shared knowledge: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/cleanup', methods=['POST'])
@require_auth
@rate_limit(requests_per_minute=5)
@async_manager.async_route
async def cleanup_memories():
    """
    Clean up old memories.
    
    Request body:
    {
        "days_old": 30
    }
    """
    try:
        data = request.get_json()
        days_old = data.get('days_old', 30)
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Cleanup old memories
        result = await supermemory.cleanup_old_memories(days_old=days_old)
        
        return jsonify({
            'success': True,
            'days_old': days_old,
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up memories: {e}")
        return jsonify({'error': str(e)}), 500


@memory_api_bp.route('/stats', methods=['GET'])
@require_auth
@async_manager.async_route
async def memory_stats():
    """
    Get memory usage statistics.
    
    Query parameters:
    - agent_id: Get stats for specific agent (optional)
    """
    try:
        agent_id = request.args.get('agent_id')
        
        # Get Supermemory service
        supermemory = get_service('supermemory_service')
        if not supermemory:
            return jsonify({'error': 'Supermemory service not available'}), 503
        
        # Gather statistics
        stats = {
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'supermemory'
        }
        
        if agent_id:
            # Get agent-specific stats
            memories = await supermemory.get_agent_memories(agent_id, limit=1000)
            stats['agent_id'] = agent_id
            stats['total_memories'] = len(memories)
            
            # Categorize by metadata type
            categories = {}
            for memory in memories:
                metadata = memory.get('metadata', {})
                mem_type = metadata.get('type', 'general')
                categories[mem_type] = categories.get(mem_type, 0) + 1
            
            stats['categories'] = categories
        else:
            # Get general stats
            shared = await supermemory.get_shared_knowledge(limit=1000)
            stats['shared_knowledge_count'] = len(shared)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        return jsonify({'error': str(e)}), 500