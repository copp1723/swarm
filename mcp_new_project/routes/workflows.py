"""
Workflow API routes for chain-of-agents template execution
"""
from flask import Blueprint, jsonify, request
import logging
from typing import Dict, Any
from services.workflow_engine import get_workflow_engine
from services.multi_agent_service import get_multi_agent_service
from utils.session import get_session_id
from utils.logging import log_system_event
from services.error_handler import error_handler, ErrorCategory

workflows_bp = Blueprint('workflows', __name__, url_prefix='/api/workflows')
logger = logging.getLogger(__name__)

@workflows_bp.route('/templates', methods=['GET'])
def get_workflow_templates():
    """Get all available workflow templates"""
    try:
        engine = get_workflow_engine()
        templates = engine.get_available_templates()
        
        return jsonify({
            'success': True,
            'templates': templates,
            'total': len(templates)
        })
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'get_workflow_templates'}
        )
        return jsonify({'error': error_context.user_message}), 500

@workflows_bp.route('/templates/<template_id>', methods=['GET'])
def get_workflow_template_details(template_id: str):
    """Get detailed information about a specific workflow template"""
    try:
        engine = get_workflow_engine()
        template = engine.templates.get(template_id)
        
        if not template:
            return jsonify({'error': f'Template {template_id} not found'}), 404
        
        return jsonify({
            'success': True,
            'template': template
        })
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'get_workflow_template_details', 'template_id': template_id}
        )
        return jsonify({'error': error_context.user_message}), 500

@workflows_bp.route('/execute', methods=['POST'])
def execute_workflow():
    """Execute a workflow template"""
    session_id = get_session_id()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        template_id = data.get('template_id')
        working_directory = data.get('working_directory', './')
        context = data.get('context', {})  # Additional context for the workflow
        execution_mode = data.get('execution_mode', 'staged')  # sequential, parallel, staged
        
        if not template_id:
            return jsonify({'error': 'template_id is required'}), 400
        
        # Create workflow execution
        engine = get_workflow_engine()
        execution = engine.create_execution(template_id)
        
        if not execution:
            return jsonify({'error': f'Failed to create execution for template {template_id}'}), 400
        
        log_system_event('info', 'workflow_execution_started',
                        f"Starting workflow {template_id} execution {execution.execution_id}",
                        session_id)
        
        # Get the multi-agent service
        service = get_multi_agent_service()
        
        # Execute workflow based on mode
        if execution_mode == 'sequential':
            result = _execute_sequential_workflow(execution, service, working_directory, context)
        elif execution_mode == 'parallel':
            result = _execute_parallel_workflow(execution, service, working_directory, context)
        else:  # staged
            result = _execute_staged_workflow(execution, service, working_directory, context)
        
        return jsonify({
            'success': True,
            'execution_id': execution.execution_id,
            'workflow_id': template_id,
            'mode': execution_mode,
            'message': f'Workflow execution started in {execution_mode} mode',
            **result
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'execute_workflow'},
            session_id
        )
        return jsonify({'error': error_context.user_message}), 500

@workflows_bp.route('/executions/<execution_id>', methods=['GET'])
def get_workflow_execution(execution_id: str):
    """Get the status and details of a workflow execution"""
    try:
        engine = get_workflow_engine()
        execution = engine.get_execution(execution_id)
        
        if not execution:
            return jsonify({'error': f'Execution {execution_id} not found'}), 404
        
        # Get visualization data
        visualization = engine.get_execution_visualization(execution_id)
        
        # Get execution report
        report = engine.export_execution_report(execution_id)
        
        return jsonify({
            'success': True,
            'execution': report,
            'visualization': visualization
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'get_workflow_execution', 'execution_id': execution_id}
        )
        return jsonify({'error': error_context.user_message}), 500

@workflows_bp.route('/executions/<execution_id>/reorder', methods=['POST'])
def reorder_workflow_steps(execution_id: str):
    """Reorder steps in a workflow execution (if allowed)"""
    try:
        data = request.get_json()
        if not data or 'new_order' not in data:
            return jsonify({'error': 'new_order array is required'}), 400
        
        new_order = data['new_order']
        
        engine = get_workflow_engine()
        success = engine.reorder_steps(execution_id, new_order)
        
        if not success:
            return jsonify({
                'error': 'Failed to reorder steps. Check dependencies and permissions.'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Steps reordered successfully',
            'execution_id': execution_id
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'reorder_workflow_steps', 'execution_id': execution_id}
        )
        return jsonify({'error': error_context.user_message}), 500

@workflows_bp.route('/executions/<execution_id>/step/<agent_id>', methods=['GET'])
def get_workflow_step_details(execution_id: str, agent_id: str):
    """Get detailed information about a specific step in a workflow execution"""
    try:
        engine = get_workflow_engine()
        execution = engine.get_execution(execution_id)
        
        if not execution:
            return jsonify({'error': f'Execution {execution_id} not found'}), 404
        
        # Find the step
        step = None
        for s in execution.steps:
            if s.agent == agent_id:
                step = s
                break
        
        if not step:
            return jsonify({'error': f'Step for agent {agent_id} not found'}), 404
        
        # Get task details from multi-agent service if step is running/completed
        task_details = None
        if step.status in ['running', 'completed']:
            service = get_multi_agent_service()
            # Try to get conversation history for this agent
            task_details = service.executor.get_agent_chat_history(agent_id)
        
        return jsonify({
            'success': True,
            'step': step.to_dict(),
            'task_details': task_details
        })
        
    except Exception as e:
        error_context = error_handler.handle_error(
            e, ErrorCategory.UNKNOWN_ERROR,
            {'endpoint': 'get_workflow_step_details', 
             'execution_id': execution_id,
             'agent_id': agent_id}
        )
        return jsonify({'error': error_context.user_message}), 500

# Helper functions for different execution modes

def _execute_sequential_workflow(execution, service, working_directory: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute workflow steps sequentially"""
    # Build agent configs from steps
    agent_configs = []
    for step in execution.steps:
        from routes.agents import AGENT_PROFILES
        profile = next((p for p in AGENT_PROFILES.values() if p['agent_id'] == step.agent), None)
        if profile:
            agent_configs.append({
                'agent_id': step.agent,
                'agent_name': profile['name'],
                'model': profile['preferred_models'][0],
                'task': step.task  # Include specific task for this step
            })
    
    # Create a comprehensive task description
    template = service.storage.get_task(execution.workflow_id) if hasattr(service, 'storage') else {}
    task_description = f"Execute workflow: {execution.workflow_id}\n\n"
    for i, step in enumerate(execution.steps):
        task_description += f"{i+1}. {step.agent}: {step.task}\n"
    
    # Add context if provided
    if context:
        task_description += f"\n\nContext: {context}"
    
    # Execute using multi-agent service in sequential mode
    result = service.execute_task(
        task_description=task_description,
        agent_configs=agent_configs,
        working_directory=working_directory,
        sequential=True,
        enable_real_time=True
    )
    
    # Link the task to the workflow execution
    if result.get('success') and result.get('task_id'):
        execution.task_id = result['task_id']
    
    return result

def _execute_parallel_workflow(execution, service, working_directory: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute all workflow steps in parallel"""
    # Similar to sequential but with parallel flag
    agent_configs = []
    for step in execution.steps:
        from routes.agents import AGENT_PROFILES
        profile = next((p for p in AGENT_PROFILES.values() if p['agent_id'] == step.agent), None)
        if profile:
            agent_configs.append({
                'agent_id': step.agent,
                'agent_name': profile['name'],
                'model': profile['preferred_models'][0],
                'task': step.task
            })
    
    task_description = f"Execute workflow (parallel): {execution.workflow_id}\n\n"
    for step in execution.steps:
        task_description += f"- {step.agent}: {step.task}\n"
    
    if context:
        task_description += f"\n\nContext: {context}"
    
    result = service.execute_task(
        task_description=task_description,
        agent_configs=agent_configs,
        working_directory=working_directory,
        sequential=False,
        enable_real_time=True
    )
    
    if result.get('success') and result.get('task_id'):
        execution.task_id = result['task_id']
    
    return result

def _execute_staged_workflow(execution, service, working_directory: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute workflow in dependency-based stages"""
    # Get execution stages
    stages = execution.get_execution_stages()
    
    # For now, execute all agents but mention the staged approach in the task
    all_agents = []
    stage_description = "Execute workflow in stages based on dependencies:\n\n"
    
    for i, stage in enumerate(stages):
        stage_description += f"Stage {i+1}:\n"
        for step in stage:
            from routes.agents import AGENT_PROFILES
            profile = next((p for p in AGENT_PROFILES.values() if p['agent_id'] == step.agent), None)
            if profile:
                all_agents.append({
                    'agent_id': step.agent,
                    'agent_name': profile['name'],
                    'model': profile['preferred_models'][0],
                    'task': step.task,
                    'stage': i + 1
                })
                stage_description += f"  - {step.agent}: {step.task}\n"
        stage_description += "\n"
    
    if context:
        stage_description += f"\nContext: {context}"
    
    # Execute with stage awareness
    result = service.execute_task(
        task_description=stage_description,
        agent_configs=all_agents,
        working_directory=working_directory,
        sequential=True,  # Stages are sequential, but items within can be parallel
        enable_real_time=True
    )
    
    if result.get('success') and result.get('task_id'):
        execution.task_id = result['task_id']
    
    return result