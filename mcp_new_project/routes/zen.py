"""
Zen MCP API Routes
Handles Zen multi-model orchestration and development tools
"""

from flask import Blueprint, jsonify, request
import logging
from typing import Dict, Any
from services.zen_mcp_service import get_zen_service
from services.zen_memory_executor import get_zen_memory_executor
from services.error_handler import error_handler, ErrorCategory

zen_bp = Blueprint('zen', __name__, url_prefix='/api/zen')
logger = logging.getLogger(__name__)

@zen_bp.route('/status', methods=['GET'])
async def zen_status():
    """Check Zen MCP service status"""
    try:
        zen_service = get_zen_service()
        is_available = await zen_service.is_available()
        
        return jsonify({
            'success': True,
            'enabled': zen_service.enabled,
            'available': is_available,
            'url': zen_service.base_url,
            'tools': [
                'chat', 'thinkdeep', 'planner', 'consensus',
                'codereview', 'debug', 'analyze', 'refactor', 'tracer'
            ] if is_available else []
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'enabled': False,
            'available': False
        }), 500

@zen_bp.route('/chat', methods=['POST'])
async def zen_chat():
    """Use Zen's collaborative thinking"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message']
        context = data.get('context')
        
        zen_service = get_zen_service()
        result = await zen_service.chat(message, context)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'response': result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'zen_chat'}
        )
        return jsonify({'error': error_context.user_message}), 500

@zen_bp.route('/think-deep', methods=['POST'])
async def zen_think_deep():
    """Use Zen's extended reasoning"""
    try:
        data = request.get_json()
        if not data or 'problem' not in data:
            return jsonify({'error': 'Problem description is required'}), 400
        
        problem = data['problem']
        constraints = data.get('constraints', [])
        
        zen_service = get_zen_service()
        result = await zen_service.think_deep(problem, constraints)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'analysis': result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'zen_think_deep'}
        )
        return jsonify({'error': error_context.user_message}), 500

@zen_bp.route('/code-review', methods=['POST'])
async def zen_code_review():
    """Perform code review with Zen"""
    try:
        data = request.get_json()
        if not data or 'code_path' not in data:
            return jsonify({'error': 'Code path is required'}), 400
        
        code_path = data['code_path']
        focus_areas = data.get('focus_areas', [])
        agent_id = data.get('agent_id', 'coder_01')
        
        executor = get_zen_memory_executor()
        result = await executor.code_review_with_memory(
            agent_id=agent_id,
            code_path=code_path,
            focus_areas=focus_areas
        )
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'review': result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'zen_code_review'}
        )
        return jsonify({'error': error_context.user_message}), 500

@zen_bp.route('/debug', methods=['POST'])
async def zen_debug():
    """Debug with Zen root cause analysis"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Debug data is required'}), 400
        
        error_message = data.get('error_message', '')
        code_context = data.get('code_context', '')
        stack_trace = data.get('stack_trace')
        agent_id = data.get('agent_id', 'bug_01')
        
        if not error_message:
            return jsonify({'error': 'Error message is required'}), 400
        
        executor = get_zen_memory_executor()
        result = await executor.debug_with_context(
            agent_id=agent_id,
            error_message=error_message,
            code_context=code_context,
            stack_trace=stack_trace
        )
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'debug_analysis': result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'zen_debug'}
        )
        return jsonify({'error': error_context.user_message}), 500

@zen_bp.route('/plan', methods=['POST'])
async def zen_plan():
    """Create project plan with Zen"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Planning data is required'}), 400
        
        project = data.get('project_description', '')
        requirements = data.get('requirements', [])
        constraints = data.get('constraints', [])
        agent_ids = data.get('agent_ids', ['product_01', 'coder_01'])
        
        if not project or not requirements:
            return jsonify({
                'error': 'Project description and requirements are required'
            }), 400
        
        executor = get_zen_memory_executor()
        result = await executor.collaborative_planning(
            task_description=project,
            agent_ids=agent_ids,
            requirements=requirements,
            constraints=constraints
        )
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'plan': result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'zen_plan'}
        )
        return jsonify({'error': error_context.user_message}), 500

@zen_bp.route('/consensus', methods=['POST'])
async def zen_consensus():
    """Build consensus across multiple perspectives"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Consensus data is required'}), 400
        
        question = data.get('question', '')
        perspectives = data.get('perspectives', [])
        
        if not question or not perspectives:
            return jsonify({
                'error': 'Question and perspectives are required'
            }), 400
        
        zen_service = get_zen_service()
        result = await zen_service.consensus(question, perspectives)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'consensus': result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'zen_consensus'}
        )
        return jsonify({'error': error_context.user_message}), 500

@zen_bp.route('/multi-model', methods=['POST'])
async def zen_multi_model():
    """Query multiple models through Zen"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        models = data.get('models')
        
        zen_service = get_zen_service()
        result = await zen_service.multi_model_query(query, models)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify({
            'success': True,
            'multi_model_response': result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'zen_multi_model'}
        )
        return jsonify({'error': error_context.user_message}), 500

@zen_bp.route('/agent/profile/<agent_id>', methods=['GET'])
async def get_zen_agent_profile(agent_id: str):
    """Get enhanced agent profile with Zen capabilities"""
    try:
        executor = get_zen_memory_executor()
        profile = await executor.get_enhanced_agent_profile(agent_id)
        
        return jsonify({
            'success': True,
            'profile': profile
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'get_zen_agent_profile', 'agent_id': agent_id}
        )
        return jsonify({'error': error_context.user_message}), 500