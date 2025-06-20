#!/usr/bin/env python3
"""
Enhanced Flask server with complete API and WebSocket support for multi-agent workspace
"""
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os
import uuid
import time
import json
from threading import Timer

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})

# Initialize SocketIO for real-time communication
socketio = SocketIO(app, cors_allowed_origins="*")

# In-memory storage for demo
active_tasks = {}
agent_chat_history = {}
workspace_state = {
    'active_agents': [],
    'current_task': None,
    'messages': []
}

# Serve static files from the project root
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        # Serve index.html for all other routes (SPA routing)
        return send_from_directory(app.static_folder, 'index.html')

# Basic API endpoints for testing
@app.route('/api/agents/profiles')
def get_agent_profiles():
    return jsonify({
        'success': True,
        'profiles': [
            {
                'role': 'general_01',
                'name': 'General Assistant',
                'description': 'A helpful general-purpose assistant',
                'capabilities': ['general assistance', 'task planning', 'problem solving'],
                'specialties': ['general'],
                'tools': [],
                'interaction_style': 'conversational'
            },
            {
                'role': 'product_01',
                'name': 'Product Manager',
                'description': 'Product strategy and planning expert',
                'capabilities': ['product planning', 'requirements analysis', 'roadmap creation'],
                'specialties': ['product'],
                'tools': [],
                'interaction_style': 'structured'
            }
        ],
        'total': 2
    })

@app.route('/api/agents/status')
def get_executor_status():
    return jsonify({
        "active_tasks": 0,
        "task_ids": [],
        "status": "healthy"
    })

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'enhanced-multi-agent-server'})

# Multi-agent chat endpoints
@app.route('/api/agents/chat/<agent_id>', methods=['POST'])
def chat_with_agent(agent_id):
    data = request.get_json()
    message = data.get('message', '')
    
    # Initialize chat history if needed
    if agent_id not in agent_chat_history:
        agent_chat_history[agent_id] = []
    
    # Add user message
    user_msg = {
        'id': str(uuid.uuid4()),
        'role': 'user',
        'content': message,
        'timestamp': time.time()
    }
    agent_chat_history[agent_id].append(user_msg)
    
    # Simulate agent response
    agent_response = f"Hello! This is {agent_id} responding to: {message[:50]}..."
    
    agent_msg = {
        'id': str(uuid.uuid4()),
        'role': 'assistant',
        'content': agent_response,
        'timestamp': time.time()
    }
    agent_chat_history[agent_id].append(agent_msg)
    
    # Emit WebSocket event
    socketio.emit('agent_response', {
        'agent_id': agent_id,
        'message': agent_msg,
        'conversation_id': f'chat_{agent_id}'
    })
    
    return jsonify({
        'success': True,
        'response': agent_response,
        'message_id': agent_msg['id']
    })

@app.route('/api/agents/chat_history/<agent_id>')
def get_agent_chat_history(agent_id):
    history = agent_chat_history.get(agent_id, [])
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        'history': history
    })

@app.route('/api/agents/chat_history/<agent_id>', methods=['DELETE'])
def clear_agent_chat_history(agent_id):
    agent_chat_history[agent_id] = []
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        'message': 'Chat history cleared'
    })

# Multi-agent collaboration endpoints
@app.route('/api/agents/collaborate', methods=['POST'])
def execute_collaborative_task():
    data = request.get_json()
    task_id = str(uuid.uuid4())
    
    task = {
        'task_id': task_id,
        'description': data.get('task_description', ''),
        'agents': data.get('tagged_agents', []),
        'status': 'running',
        'progress': 0,
        'started_at': time.time()
    }
    active_tasks[task_id] = task
    
    # Simulate task progress
    def simulate_progress():
        for i in range(1, 6):
            Timer(i * 2.0, lambda p=i*20: update_task_progress(task_id, p)).start()
    
    simulate_progress()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'started',
        'agents': task['agents']
    })

def update_task_progress(task_id, progress):
    if task_id in active_tasks:
        active_tasks[task_id]['progress'] = progress
        socketio.emit('task_progress', {
            'task_id': task_id,
            'progress': progress,
            'status': 'completed' if progress >= 100 else 'running'
        })

# Workspace state management
@app.route('/api/workspace/state')
def get_workspace_state():
    return jsonify({
        'success': True,
        'workspace': workspace_state
    })

@app.route('/api/workspace/state', methods=['POST'])
def update_workspace_state():
    data = request.get_json()
    workspace_state.update(data)
    
    # Broadcast workspace update
    socketio.emit('workspace_updated', workspace_state)
    
    return jsonify({
        'success': True,
        'workspace': workspace_state
    })

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'status': 'connected', 'workspace': workspace_state})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('join_workspace')
def handle_join_workspace(data):
    workspace_id = data.get('workspace_id', 'default')
    print(f'Client joined workspace: {workspace_id}')
    emit('workspace_joined', {'workspace_id': workspace_id})

@socketio.on('agent_message')
def handle_agent_message(data):
    agent_id = data.get('agent_id')
    message = data.get('message')
    
    # Broadcast to all clients
    emit('agent_communication', {
        'from_agent': agent_id,
        'message': message,
        'timestamp': time.time()
    }, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting enhanced multi-agent server on port {port}")
    print("Frontend available at: http://localhost:5000")
    print("WebSocket support enabled for real-time communication")
    socketio.run(app, debug=True, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

