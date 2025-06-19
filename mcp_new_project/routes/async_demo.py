"""
Async Demo Routes - Demonstrates async database usage
Shows performance benefits of async operations
"""
from flask import Blueprint, jsonify
import asyncio
import time
from repositories.async_repositories import (
    AsyncConversationRepository,
    AsyncMessageRepository,
    AsyncModelUsageRepository
)
from utils.session import get_session_id
from utils.async_wrapper import async_manager
from utils.async_error_handler import handle_async_route_errors
from services.error_handler import ErrorCategory

async_demo_bp = Blueprint('async_demo', __name__, url_prefix='/api/async-demo')


@async_demo_bp.route('/performance-test')
@async_manager.async_route
@handle_async_route_errors(ErrorCategory.API_ERROR)
async def performance_test():
    """
    Demonstrates performance difference between sync and async operations
    """
    session_id = get_session_id()
    
    # Time async operations
    start_time = time.time()
    
    # Perform multiple async operations concurrently
    results = await asyncio.gather(
        AsyncConversationRepository.get_active_conversations(limit=10),
        AsyncModelUsageRepository.get_usage_stats(session_id=session_id, days=7),
        AsyncMessageRepository.count_by_conversation(1),
        return_exceptions=True
    )
    
    async_time = time.time() - start_time
    
    # Parse results
    conversations = results[0] if not isinstance(results[0], Exception) else []
    usage_stats = results[1] if not isinstance(results[1], Exception) else []
    message_count = results[2] if not isinstance(results[2], Exception) else 0
    
    return jsonify({
        'performance': {
            'async_time_ms': round(async_time * 1000, 2),
            'operations_performed': 3,
            'operations_per_second': round(3 / async_time, 2)
        },
        'data': {
            'active_conversations': len(conversations),
            'usage_stats': usage_stats,
            'sample_message_count': message_count
        }
    })


@async_demo_bp.route('/create-conversation', methods=['POST'])
@async_manager.async_route
async def create_conversation_async():
    """
    Create a new conversation using async repository
    """
    from flask import request
    data = request.get_json() or {}
    
    session_id = get_session_id()
    model_id = data.get('model_id', 'openai/gpt-4')
    title = data.get('title', 'Async Conversation Demo')
    
    try:
        # Create conversation asynchronously
        conversation = await AsyncConversationRepository.create(
            session_id=session_id,
            model_id=model_id,
            title=title
        )
        
        # Track model usage asynchronously
        await AsyncModelUsageRepository.track_usage(
            model_id=model_id,
            session_id=session_id
        )
        
        return jsonify({
            'success': True,
            'conversation': conversation.to_dict(),
            'message': 'Conversation created using async database'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@async_demo_bp.route('/bulk-operations')
@async_manager.async_route
async def bulk_operations_demo():
    """
    Demonstrates bulk async operations for performance testing
    """
    start_time = time.time()
    session_id = get_session_id()
    
    # Simulate bulk read operations
    tasks = []
    for i in range(5):
        tasks.append(AsyncConversationRepository.get_active_conversations(limit=5))
    
    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Count successful operations
    successful = sum(1 for r in results if not isinstance(r, Exception))
    
    elapsed_time = time.time() - start_time
    
    return jsonify({
        'performance': {
            'total_operations': len(tasks),
            'successful_operations': successful,
            'total_time_ms': round(elapsed_time * 1000, 2),
            'avg_time_per_operation_ms': round((elapsed_time * 1000) / len(tasks), 2),
            'operations_per_second': round(len(tasks) / elapsed_time, 2)
        },
        'message': 'Bulk operations completed using async database'
    })