from flask import Blueprint, jsonify, request, current_app as app
import logging
import os
from werkzeug.utils import secure_filename
from typing import List, Dict, Any
from utils.session import get_session_id
from utils.logging import log_system_event
from utils.file_io import safe_read_json
from utils.error_catalog import ErrorCodes, format_error_response
from utils.auth import require_auth, optional_auth
from utils.rate_limiter import standard_rate_limit, strict_rate_limit
from models.core import db, Conversation, Message
from services.service_container import get_service_container
from services.error_handler import error_handler, ErrorCategory
from config.constants import AgentSpecialty
from services.nlu_service import analyze_task
from services.orchestrator_service import orchestrator

agents_bp = Blueprint('agents', __name__, url_prefix='/api/agents')
logger = logging.getLogger(__name__)

# Load agent profiles from config file
def _load_agent_profiles():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'agents.json')
    config = safe_read_json(config_path, default_value={'AGENT_PROFILES': {}})
    return config.get('AGENT_PROFILES', {})

# Load agent profiles
AGENT_PROFILES = _load_agent_profiles()

def get_agent_for_task(task_description: str) -> List[str]:
    """Simple logic to suggest agents based on task description"""
    task_lower = task_description.lower()
    if "code" in task_lower or "develop" in task_lower or "program" in task_lower or "refactor" in task_lower:
        return ["coder", "product"]
    elif "plan" in task_lower or "design" in task_lower or "roadmap" in task_lower or "story" in task_lower:
        return ["product"]
    elif "bug" in task_lower or "error" in task_lower or "incident" in task_lower or "crash" in task_lower:
        return ["bug"]
    elif "test" in task_lower or "qa" in task_lower:
        return ["tester"]
    return ["product", "coder"]

def get_agents_by_specialty(specialty):
    """Get agents by specialty"""
    return [profile for profile in AGENT_PROFILES.values() if specialty in profile.get("specialties", [])]

@agents_bp.route('/profiles', methods=['GET'])
def get_agent_profiles():
    """Get all available agent profiles"""
    try:
        profiles = []
        for role, profile in AGENT_PROFILES.items():
            profiles.append({
                'role': profile['role'],
                'name': profile['name'],
                'description': profile['description'],
                'capabilities': profile['capabilities'],
                'specialties': profile.get('specialties', []),
                'tools': profile.get('tools', []),
                'interaction_style': profile.get('interaction_style', 'conversational')
            })
        
        return jsonify({
            'success': True,
            'profiles': profiles,
            'total': len(profiles)
        })
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR, 
            {'endpoint': 'get_agent_profiles'}
        )
        response = format_error_response(
            ErrorCodes.INTERNAL_ERROR,
            details={'original_error': str(e)}
        )
        return jsonify(response), response['error']['status_code']

@agents_bp.route('/list', methods=['GET'])
def get_agent_list():
    """Get list of available agents (alias for profiles)"""
    return get_agent_profiles()

@agents_bp.route('/suggest', methods=['POST'])
def suggest_agents():
    """Suggest agents for a given task"""
    try:
        data = request.get_json()
        if not data or 'task' not in data:
            response = format_error_response(
                ErrorCodes.MISSING_PARAMETER,
                parameter='task'
            )
            return jsonify(response), response['error']['status_code']
        
        task_description = data['task']
        include_details = data.get('include_details', False)
        
        # Get suggested agent roles
        suggested_roles = get_agent_for_task(task_description)
        
        response = {
            'suggested_roles': suggested_roles,
            'reasoning': f"Based on your task, I recommend using {len(suggested_roles)} agents"
        }
        
        if include_details:
            # Include full profiles
            response['profiles'] = []
            for role in suggested_roles:
                profile = AGENT_PROFILES.get(role)
                if profile:
                    response['profiles'].append({
                        'role': profile['role'],
                        'name': profile['name'],
                        'description': profile['description'],
                        'capabilities': profile['capabilities'][:3]  # Top 3 capabilities
                    })
        
        return jsonify(response)
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'suggest_agents'}
        )
        return jsonify({'error': error_context.user_message}), 500

@agents_bp.route('/execute', methods=['POST'])
def execute_multi_agent_task():
    """Execute a task using the consolidated multi-agent executor"""
    session_id = get_session_id()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided', 'success': False}), 400
        
        # Extract required fields
        task_description = data.get('task_description', data.get('task', '')).strip()
        agents = data.get('agents', [])
        working_directory = data.get('working_directory', './').strip()
        enable_real_time = data.get('enable_real_time', True)
        
        if not task_description:
            return jsonify({'error': 'Task description is required', 'success': False}), 400
        
        if not agents:
            return jsonify({'error': 'At least one agent is required', 'success': False}), 400
        
        # Log the multi-agent task
        log_system_event('info', 'multi_agent_task',
                         f"Starting multi-agent task with {len(agents)} agents in {working_directory}",
                         session_id)
        
        # Execute the task using service
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-agent task service not available',
                'task_id': None
            }), 503
            
        result = service.execute_repository_task(
            task_description=task_description,
            agent_roles=agents,
            working_directory=working_directory,
            enable_real_time=enable_real_time
        )
        
        # Save conversation history if successful and conversation_id provided
        conversation_id = data.get('conversation_id')
        if result.get('success') and conversation_id:
            _save_agent_conversation(conversation_id, task_description, result, session_id)
        
        return jsonify(result)
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'execute_multi_agent_task', 'task': task_description},
            session_id
        )
        return jsonify({
            'success': False,
            'error': error_context.user_message,
            'suggestions': error_context.recovery_suggestions
        }), 500

@agents_bp.route('/conversation/<task_id>', methods=['GET'])
def get_agent_conversation(task_id: str):
    """Get the conversation history for a multi-agent task"""
    try:
        # Get task status from service
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            return jsonify({
                'success': True,
                'task_id': task_id,
                'status': 'unavailable',
                'progress': 0,
                'current_phase': '',
                'conversations': [],
                'task': {'status': 'service unavailable'}
            })
            
        task_status = service.get_task_status(task_id)
        
        if not task_status:
            return jsonify({
                'error': f'Task {task_id} not found',
                'success': False
            }), 404
        
        # Return conversation in expected format
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': task_status.get('status', 'unknown'),
            'progress': task_status.get('progress', 0),
            'current_phase': task_status.get('current_phase', ''),
            'conversations': task_status.get('conversations', []),
            'task': task_status
        })
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'get_agent_conversation', 'task_id': task_id}
        )
        return jsonify({'error': error_context.user_message}), 500

@agents_bp.route('/status', methods=['GET'])
def get_executor_status():
    try:
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            return jsonify({
                "active_tasks": 0,
                "task_ids": [],
                "status": "service unavailable"
            })
            
        active_tasks = service.executor.list_active_tasks()
        return jsonify({
            "active_tasks": len(active_tasks),
            "task_ids": active_tasks
        })
    except Exception as e:
        logger.error(f"Failed to get executor status: {e}")
        return jsonify({
            "active_tasks": 0,
            "task_ids": [],
            "status": "error",
            "message": "Service unavailable"
        })

@agents_bp.route('/workflows', methods=['GET'])
def get_workflow_templates():
    """Get available workflow templates"""
    try:
        import json
        workflows_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'workflows.json')
        
        if os.path.exists(workflows_path):
            with open(workflows_path, 'r') as f:
                workflows = json.load(f)
                return jsonify(workflows)
        else:
            # Return default templates if file doesn't exist
            return jsonify({
                "templates": [
                    {
                        "id": "code_review",
                        "name": "Code Review Workflow",
                        "description": "Comprehensive code review by multiple agents",
                        "task_description": "Perform a detailed code review of the specified repository.",
                        "tagged_agents": ["product_01", "coding_01", "bug_01"]
                    },
                    {
                        "id": "feature_development",
                        "name": "Feature Development",
                        "description": "Develop a new feature with planning and implementation",
                        "task_description": "Plan and implement a new feature based on requirements.",
                        "tagged_agents": ["product_01", "coding_01"]
                    }
                ]
            })
    except Exception as e:
        # Return default templates instead of error to not break UI
        logger.warning(f"Failed to get workflow templates: {e}")
        return jsonify({
            "templates": [
                {
                    "id": "code_review",
                    "name": "Code Review Workflow",
                    "description": "Comprehensive code review by multiple agents",
                    "task_description": "Perform a detailed code review of the specified repository.",
                    "tagged_agents": ["product_01", "coding_01", "bug_01"]
                },
                {
                    "id": "feature_development",
                    "name": "Feature Development",
                    "description": "Develop a new feature with planning and implementation",
                    "task_description": "Plan and implement a new feature based on requirements.",
                    "tagged_agents": ["product_01", "coding_01"]
                }
            ]
        })

@agents_bp.route('/chat/<agent_id>', methods=['POST'])
def chat_with_agent(agent_id: str):
    """Chat directly with a specific agent."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required', 'success': False}), 400
        
        message = data['message']
        model = data.get('model')  # Optional model override
        enhance_prompt = data.get('enhance_prompt', False)  # Default to True
        
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            return jsonify({
                'success': False,
                'error': 'Chat service not available',
                'response': 'The chat service is currently unavailable. Please try again later.'
            }), 503
            
        result = service.executor.start_agent_chat(agent_id, message, model, enhance_prompt)
        return jsonify(result)
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'chat_with_agent', 'agent_id': agent_id}
        )
        return jsonify({'error': error_context.user_message}), 500

@agents_bp.route('/chat_history/<agent_id>', methods=['GET'])
def get_agent_chat_history(agent_id: str):
    """Get chat history for a specific agent."""
    try:
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            # Return empty history if service not available
            return jsonify({'success': True, 'agent_id': agent_id, 'history': []})
        
        history = service.executor.get_agent_chat_history(agent_id)
        return jsonify({'success': True, 'agent_id': agent_id, 'history': history})
    except Exception as e:
        # Return empty history instead of error to not break UI
        logger.warning(f"Chat history service unavailable for {agent_id}: {e}")
        return jsonify({'success': True, 'agent_id': agent_id, 'history': []})

@agents_bp.route('/chat_history/<agent_id>', methods=['DELETE'])
def clear_agent_chat_history(agent_id: str):
    """Clear chat history for a specific agent."""
    try:
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            return jsonify({'success': True, 'agent_id': agent_id, 'message': 'No history to clear (service unavailable)'})
            
        service.executor.clear_agent_chat_history(agent_id)
        return jsonify({'success': True, 'agent_id': agent_id, 'message': 'Chat history cleared'})
    except Exception as e:
        # Return success instead of error to not break UI
        logger.warning(f"Failed to clear chat history for {agent_id}: {e}")
        return jsonify({'success': True, 'agent_id': agent_id, 'message': 'No history to clear'})

@agents_bp.route('/collaborate', methods=['POST'])
def execute_collaborative_task():
    """Execute a collaborative task with tagged agents."""
    session_id = get_session_id()
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided', 'success': False}), 400
        
        task_description = data.get('task_description', '').strip()
        tagged_agents = data.get('tagged_agents', [])  # List of agent IDs
        working_directory = data.get('working_directory', './').strip()
        sequential = data.get('sequential', False)
        enhance_prompt = data.get('enhance_prompt', False)  # Default to True
        
        if not task_description or not tagged_agents:
            return jsonify({'error': 'Task description and tagged agents are required', 'success': False}), 400
        
        log_system_event('info', 'collaborative_task',
                         f"Starting {'sequential' if sequential else 'parallel'} collaborative task with {len(tagged_agents)} agents in {working_directory}",
                         session_id)
        
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            return jsonify({
                'success': False,
                'error': 'Collaboration service not available',
                'task_id': None
            }), 503
            
        result = service.executor.execute_collaborative_task(task_description, tagged_agents, working_directory, sequential, enhance_prompt)
        return jsonify(result)
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'execute_collaborative_task', 'task': task_description},
            session_id
        )
        return jsonify({'success': False, 'error': error_context.user_message}), 500

@agents_bp.route('/upload/<agent_id>', methods=['POST'])
def upload_file_to_agent(agent_id: str):
    """Handle file uploads for a specific agent."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided', 'success': False}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected', 'success': False}), 400
        
        # Save file to upload folder
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        
        # Use MCP filesystem tool to read the file and provide context to agent
        try:
            from services.mcp_manager import mcp_manager
            from utils.async_wrapper import async_manager
            
            # Read file info using MCP
            file_info = async_manager.run_sync(mcp_manager.call_tool("get_file_info", {
                "path": upload_path
            }))
            
            # If it's a text file, read contents
            file_contents = ""
            if filename.endswith(('.txt', '.csv', '.json', '.py', '.js', '.md', '.yml', '.yaml')):
                try:
                    file_contents = async_manager.run_sync(mcp_manager.call_tool("read_file", {
                        "path": upload_path
                    }))
                    # Limit content length
                    if len(file_contents) > 2000:
                        file_contents = file_contents[:2000] + "... [truncated]"
                except Exception as read_error:
                    file_contents = f"[Could not read file contents: {str(read_error)}]"
            else:
                file_contents = "[Binary file - contents not displayed]"
            
            # Create comprehensive message for agent
            message = f"""File '{filename}' uploaded successfully.

**File Information:**
{file_info}

**File Contents:**
{file_contents}

**File Path:** {upload_path}

Please analyze this file according to your role as {AGENT_PROFILES.get(agent_id, {}).get('name', agent_id)}."""
            
        except Exception as mcp_error:
            logger.error(f"MCP error during upload: {mcp_error}")
            # Fallback message
            message = f"File '{filename}' uploaded to {upload_path}. Note: Filesystem analysis unavailable due to MCP error: {str(mcp_error)}"
        
        # Get the service and notify agent about the uploaded file
        service = get_service_container().get('multi_agent_task_service')
        if not service:
            return jsonify({
                'success': True,
                'filename': filename,
                'path': upload_path,
                'agent_response': 'File received but agent service unavailable. The file has been saved and can be processed later.'
            })
            
        result = service.executor.start_agent_chat(agent_id, message)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': upload_path,
            'agent_response': result.get('response', 'File received and analyzed')
        })
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'error': f"Upload failed: {str(e)}", 'success': False}), 500

def _save_agent_conversation(conversation_id, task_description, result, session_id):
    """Save agent conversation to database"""
    try:
        conversation = Conversation.query.filter_by(id=conversation_id, session_id=session_id).first()
        if not conversation:
            return
        
        # Create a message record for the task initiation
        message = Message(
            conversation_id=conversation.id,
            message_id=f"agent_task_{result.get('task_id', 'unknown')}",
            role="user",
            content=f"Started multi-agent task: {task_description}",
            model_used="multi-agent-executor"
        )
        db.session.add(message)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to save agent conversation: {e}")
        db.session.rollback()


@agents_bp.route('/analyze', methods=['POST'])
def analyze_task_endpoint():
    """Analyze a task using NLU to extract intent and entities"""
    try:
        data = request.get_json()
        if not data or 'task' not in data:
            response = format_error_response(
                ErrorCodes.MISSING_PARAMETER,
                parameter='task'
            )
            return jsonify(response), response['error']['status_code']
        
        task_description = data['task']
        
        # Analyze task with NLU
        analysis = analyze_task(task_description)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'analyze_task'}
        )
        return jsonify({'error': error_context.user_message}), 500


@agents_bp.route('/orchestrate', methods=['POST'])
def orchestrate_task_endpoint():
    """Execute a task using intelligent orchestration"""
    session_id = get_session_id()
    
    try:
        data = request.get_json()
        if not data or 'task' not in data:
            response = format_error_response(
                ErrorCodes.MISSING_PARAMETER,
                parameter='task'
            )
            return jsonify(response), response['error']['status_code']
        
        task_description = data['task']
        working_directory = data.get('working_directory', './')
        priority = data.get('priority')
        emergency = data.get('emergency', False)
        
        # Build context
        context = {
            'working_directory': working_directory,
            'session_id': session_id
        }
        if priority:
            context['priority'] = priority
        if emergency:
            context['emergency'] = emergency
        
        log_system_event('info', 'orchestrated_task',
                         f"Starting orchestrated task execution",
                         session_id)
        
        # Create and execute plan
        plan = orchestrator.analyze_and_route(task_description, context)
        
        # Return plan without execution if dry_run is specified
        if data.get('dry_run', False):
            return jsonify({
                'success': True,
                'plan': {
                    'task_id': plan.task_id,
                    'routing': {
                        'primary_agents': plan.routing_decision.primary_agents,
                        'secondary_agents': plan.routing_decision.secondary_agents,
                        'workflow_type': plan.routing_decision.workflow_type,
                        'reasoning': plan.routing_decision.reasoning,
                        'confidence': plan.routing_decision.confidence
                    },
                    'nlu_analysis': plan.nlu_analysis,
                    'execution_steps': plan.execution_steps,
                    'estimated_duration': plan.estimated_duration,
                    'priority': plan.priority
                }
            })
        
        # Execute the plan
        result = orchestrator.execute_plan(plan, **context)
        
        # Save conversation if successful
        conversation_id = data.get('conversation_id')
        if result.get('success') and conversation_id:
            _save_agent_conversation(conversation_id, task_description, result, session_id)
        
        return jsonify(result)
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'orchestrate_task', 'task': task_description},
            session_id
        )
        return jsonify({
            'success': False,
            'error': error_context.user_message,
            'suggestions': error_context.recovery_suggestions
        }), 500
