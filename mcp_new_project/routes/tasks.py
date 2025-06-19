"""
Task Management Routes
Handles background task creation, monitoring, and control
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any
import logging
from config.celery_config import celery_app
from tasks.agent_tasks import execute_multi_agent_workflow, analyze_conversation, batch_file_processing
from tasks.analysis_tasks import generate_usage_report, analyze_model_performance
from utils.websocket import task_notifier
from utils.session import get_session_id
from utils.error_catalog import ErrorCodes, format_error_response

logger = logging.getLogger(__name__)

tasks_bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')


@tasks_bp.route('/start/multi-agent-workflow', methods=['POST'])
def start_multi_agent_workflow():
    """Start a multi-agent workflow in background"""
    try:
        data = request.get_json()
        if not data:
            response = format_error_response(
                ErrorCodes.INVALID_REQUEST,
                details='No workflow configuration provided'
            )
            return jsonify(response), response['error']['status_code']
        
        # Validate required fields
        if 'steps' not in data:
            response = format_error_response(
                ErrorCodes.MISSING_PARAMETER,
                parameter='steps'
            )
            return jsonify(response), response['error']['status_code']
        
        # Add session context
        workflow_config = {
            **data,
            'session_id': get_session_id(),
            'requested_by': request.remote_addr
        }
        
        # Start background task
        task = execute_multi_agent_workflow.delay(workflow_config)
        
        logger.info(f"Started multi-agent workflow task: {task.id}")
        
        # Send initial notification
        task_notifier.send_progress_update(task.id, {
            'progress': 0,
            'status': 'Task queued',
            'timestamp': None
        })
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'status': 'started',
            'message': 'Multi-agent workflow started in background',
            'websocket_room': f'task_{task.id}'
        })
        
    except Exception as e:
        logger.error(f"Error starting multi-agent workflow: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/start/conversation-analysis', methods=['POST'])
def start_conversation_analysis():
    """Start conversation analysis in background"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No analysis configuration provided'}), 400
        
        conversation_id = data.get('conversation_id')
        analysis_type = data.get('analysis_type', 'full')
        
        if not conversation_id:
            return jsonify({'error': 'Conversation ID is required'}), 400
        
        # Start background task
        task = analyze_conversation.delay(conversation_id, analysis_type)
        
        logger.info(f"Started conversation analysis task: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'status': 'started',
            'message': 'Conversation analysis started in background',
            'websocket_room': f'task_{task.id}'
        })
        
    except Exception as e:
        logger.error(f"Error starting conversation analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/start/batch-processing', methods=['POST'])
def start_batch_processing():
    """Start batch file processing in background"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No processing configuration provided'}), 400
        
        file_paths = data.get('file_paths', [])
        processing_type = data.get('processing_type', 'analyze')
        
        if not file_paths:
            return jsonify({'error': 'File paths are required'}), 400
        
        # Start background task
        task = batch_file_processing.delay(file_paths, processing_type)
        
        logger.info(f"Started batch processing task: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'status': 'started',
            'message': f'Batch processing started for {len(file_paths)} files',
            'websocket_room': f'task_{task.id}'
        })
        
    except Exception as e:
        logger.error(f"Error starting batch processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/start/usage-report', methods=['POST'])
def start_usage_report():
    """Start usage report generation in background"""
    try:
        data = request.get_json() or {}
        
        report_config = {
            'days': data.get('days', 30),
            'session_id': get_session_id(),
            'include_detailed_metrics': data.get('include_detailed_metrics', True),
            'report_format': data.get('report_format', 'json')
        }
        
        # Start background task
        task = generate_usage_report.delay(report_config)
        
        logger.info(f"Started usage report generation task: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'status': 'started',
            'message': f'Usage report generation started for {report_config["days"]} days',
            'websocket_room': f'task_{task.id}'
        })
        
    except Exception as e:
        logger.error(f"Error starting usage report: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/start/model-analysis', methods=['POST'])
def start_model_analysis():
    """Start model performance analysis in background"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No analysis configuration provided'}), 400
        
        models = data.get('models', [])
        timeframe = data.get('timeframe', 7)
        
        if not models:
            return jsonify({'error': 'Models list is required'}), 400
        
        analysis_config = {
            'models': models,
            'timeframe': timeframe,
            'session_id': get_session_id()
        }
        
        # Start background task
        task = analyze_model_performance.delay(analysis_config)
        
        logger.info(f"Started model analysis task: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'status': 'started',
            'message': f'Model analysis started for {len(models)} models',
            'websocket_room': f'task_{task.id}'
        })
        
    except Exception as e:
        logger.error(f"Error starting model analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/status/<task_id>')
def get_task_status(task_id):
    """Get current status of a background task"""
    try:
        result = celery_app.AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'state': result.state,
            'current': result.info.get('progress', 0) if result.info else 0,
            'status': result.info.get('status', 'Unknown') if result.info else 'Unknown',
            'result': None
        }
        
        if result.state == 'PENDING':
            response_data['status'] = 'Task is waiting to be processed'
        elif result.state == 'PROGRESS':
            response_data['current'] = result.info.get('progress', 0)
            response_data['status'] = result.info.get('status', 'In progress')
            response_data['meta'] = result.info
        elif result.state == 'SUCCESS':
            response_data['status'] = 'Task completed successfully'
            response_data['result'] = result.result
            response_data['current'] = 100
        elif result.state == 'FAILURE':
            response_data['status'] = 'Task failed'
            response_data['error'] = str(result.info)
            response_data['current'] = 0
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """Cancel a running background task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        
        # Send cancellation notification
        task_notifier.send_task_error(task_id, {
            'error': 'Task cancelled by user',
            'timestamp': None
        })
        
        logger.info(f"Cancelled task: {task_id}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'status': 'cancelled',
            'message': 'Task cancelled successfully'
        })
        
    except Exception as e:
        logger.error(f"Error cancelling task: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/list')
def list_active_tasks():
    """List all active tasks"""
    try:
        # Get active tasks from Celery
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            return jsonify({'active_tasks': []})
        
        # Format task information
        formatted_tasks = []
        for worker, tasks in active_tasks.items():
            for task in tasks:
                formatted_tasks.append({
                    'task_id': task['id'],
                    'name': task['name'],
                    'worker': worker,
                    'args': task.get('args', []),
                    'kwargs': task.get('kwargs', {}),
                    'time_start': task.get('time_start')
                })
        
        return jsonify({
            'active_tasks': formatted_tasks,
            'total_active': len(formatted_tasks)
        })
        
    except Exception as e:
        logger.error(f"Error listing active tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/queue-info')
def get_queue_info():
    """Get information about task queues"""
    try:
        inspect = celery_app.control.inspect()
        
        # Get queue information
        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}
        
        queue_info = {
            'active_tasks': sum(len(tasks) for tasks in active.values()),
            'scheduled_tasks': sum(len(tasks) for tasks in scheduled.values()),
            'reserved_tasks': sum(len(tasks) for tasks in reserved.values()),
            'workers': list(active.keys()) if active else [],
            'total_workers': len(active.keys()) if active else 0
        }
        
        return jsonify(queue_info)
        
    except Exception as e:
        logger.error(f"Error getting queue info: {str(e)}")
        return jsonify({'error': str(e)}), 500