"""
WebSocket Integration for Real-time Updates
Provides real-time task progress and system notifications
"""
import logging
from flask import request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)

# Global SocketIO instance
socketio = None


def init_socketio(app):
    """Initialize SocketIO with Flask app"""
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode='gevent',
        logger=True
    )
    
    # Register event handlers
    register_socket_events()
    
    return socketio


def register_socket_events():
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect(auth):
        """Handle client connection"""
        session_id = request.sid
        logger.info(f"Client connected: {session_id}")
        
        # Send connection confirmation
        emit('connected', {
            'status': 'success',
            'session_id': session_id,
            'message': 'Connected to MCP Executive Interface'
        })
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        session_id = request.sid
        logger.info(f"Client disconnected: {session_id}")
    
    @socketio.on('join_task_room')
    def handle_join_task_room(data):
        """Join a room for task updates"""
        task_id = data.get('task_id')
        if not task_id:
            emit('error', {'message': 'Task ID required'})
            return
        
        room = f"task_{task_id}"
        join_room(room)
        logger.info(f"Client {request.sid} joined room {room}")
        
        emit('joined_room', {
            'room': room,
            'task_id': task_id,
            'message': f'Joined task room for {task_id}'
        })
    
    @socketio.on('leave_task_room')
    def handle_leave_task_room(data):
        """Leave a task room"""
        task_id = data.get('task_id')
        if not task_id:
            emit('error', {'message': 'Task ID required'})
            return
        
        room = f"task_{task_id}"
        leave_room(room)
        logger.info(f"Client {request.sid} left room {room}")
        
        emit('left_room', {
            'room': room,
            'task_id': task_id,
            'message': f'Left task room for {task_id}'
        })
    
    @socketio.on('join_agent_communication_room')
    def handle_join_agent_communication_room(data):
        """Join a room for agent communication updates"""
        task_id = data.get('task_id')
        if not task_id:
            emit('error', {'message': 'Task ID required'})
            return
        
        room = f"agent_comm_{task_id}"
        join_room(room)
        logger.info(f"Client {request.sid} joined agent communication room {room}")
        
        emit('joined_agent_comm_room', {
            'room': room,
            'task_id': task_id,
            'message': f'Joined agent communication room for {task_id}'
        })
    
    @socketio.on('get_agent_communications')
    def handle_get_agent_communications(data):
        """Get agent-to-agent communications for a task"""
        task_id = data.get('task_id')
        if not task_id:
            emit('error', {'message': 'Task ID required'})
            return
        
        try:
            # Get agent communications from the multi-agent executor
            from services.multi_agent_service import MultiAgentTaskService
            service = MultiAgentTaskService()
            
            # Get task conversation which now includes agent communications
            conversation_data = service.get_task_conversation(task_id)
            
            if conversation_data:
                emit('agent_communications', {
                    'task_id': task_id,
                    'communications': conversation_data.get('agent_communications', []),
                    'all_communications': conversation_data.get('all_communications', [])
                })
            else:
                emit('error', {'message': f'Task {task_id} not found'})
                
        except Exception as e:
            logger.error(f"Error getting agent communications: {str(e)}")
            emit('error', {'message': f'Error getting agent communications: {str(e)}'})
    
    @socketio.on('join_task')
    def handle_join_task(data):
        """Join a task room for all updates including agent communications"""
        task_id = data.get('task_id')
        if not task_id:
            emit('error', {'message': 'Task ID required'})
            return
        
        # Join both task room and agent communication room
        task_room = f"task_{task_id}"
        agent_room = f"agent_comm_{task_id}"
        
        join_room(task_room)
        join_room(agent_room)
        
        logger.info(f"Client {request.sid} joined task rooms for {task_id}")
        
        emit('joined_task', {
            'task_id': task_id,
            'message': f'Joined task {task_id} for real-time updates'
        })
    
    @socketio.on('get_task_status')
    def handle_get_task_status(data):
        """Get current status of a task"""
        task_id = data.get('task_id')
        if not task_id:
            emit('error', {'message': 'Task ID required'})
            return
        
        # Get task status from Celery
        from config.celery_config import celery_app
        
        try:
            result = celery_app.AsyncResult(task_id)
            status_data = {
                'task_id': task_id,
                'state': result.state,
                'info': result.info if result.info else {},
                'successful': result.successful(),
                'failed': result.failed()
            }
            
            emit('task_status', status_data)
            
        except Exception as e:
            logger.error(f"Error getting task status: {str(e)}")
            emit('error', {'message': f'Error getting task status: {str(e)}'})


class TaskProgressNotifier:
    """Utility class for sending task progress updates via WebSocket"""
    
    @staticmethod
    def send_agent_communication_update(task_id: str, communication_data: Dict[str, Any]):
        """Send agent-to-agent communication update to task room"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send agent communication update")
            return
        
        # Send to both task room and agent communication room
        task_room = f"task_{task_id}"
        agent_comm_room = f"agent_comm_{task_id}"
        
        try:
            # Prepare the communication event
            comm_event = {
                'task_id': task_id,
                'type': 'agent_communication',
                'communication': communication_data,
                'timestamp': communication_data.get('timestamp')
            }
            
            # Send to task room (for general collaboration monitoring)
            socketio.emit('agent_communication', comm_event, room=task_room)
            
            # Send to dedicated agent communication room
            socketio.emit('agent_communication_detailed', comm_event, room=agent_comm_room)
            
            logger.info(f"Sent agent communication update for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error sending agent communication update: {str(e)}")
    
    @staticmethod
    def send_progress_update(task_id: str, progress_data: Dict[str, Any]):
        """Send progress update to all clients in task room"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send progress update")
            return
        
        room = f"task_{task_id}"
        
        try:
            socketio.emit('task_progress', {
                'task_id': task_id,
                'timestamp': progress_data.get('timestamp'),
                'progress': progress_data.get('progress', 0),
                'status': progress_data.get('status', 'Running'),
                'meta': progress_data.get('meta', {})
            }, room=room)
            
            logger.debug(f"Sent progress update for task {task_id} to room {room}")
            
        except Exception as e:
            logger.error(f"Error sending progress update: {str(e)}")
    
    @staticmethod
    def send_task_complete(task_id: str, result_data: Dict[str, Any]):
        """Send task completion notification"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send completion update")
            return
        
        room = f"task_{task_id}"
        
        try:
            socketio.emit('task_complete', {
                'task_id': task_id,
                'status': 'completed',
                'result': result_data,
                'timestamp': result_data.get('timestamp')
            }, room=room)
            
            logger.info(f"Sent completion notification for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error sending completion notification: {str(e)}")
    
    @staticmethod
    def send_task_error(task_id: str, error_data: Dict[str, Any]):
        """Send task error notification"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send error update")
            return
        
        room = f"task_{task_id}"
        
        try:
            socketio.emit('task_error', {
                'task_id': task_id,
                'status': 'failed',
                'error': error_data,
                'timestamp': error_data.get('timestamp')
            }, room=room)
            
            logger.error(f"Sent error notification for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error sending error notification: {str(e)}")
    
    @staticmethod
    def send_system_notification(notification_type: str, data: Dict[str, Any]):
        """Send system-wide notification"""
        if not socketio:
            logger.warning("SocketIO not initialized, cannot send system notification")
            return
        
        try:
            socketio.emit('system_notification', {
                'type': notification_type,
                'data': data,
                'timestamp': data.get('timestamp')
            }, broadcast=True)
            
            logger.info(f"Sent system notification: {notification_type}")
            
        except Exception as e:
            logger.error(f"Error sending system notification: {str(e)}")


# Export the notifier for easy import
task_notifier = TaskProgressNotifier()

__all__ = ['init_socketio', 'socketio', 'task_notifier', 'TaskProgressNotifier']