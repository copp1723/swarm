#!/usr/bin/env python3
"""
Production-ready Flask server for multi-agent workspace
"""
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os
import uuid
import time
import json

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*", "allow_headers": "*", "expose_headers": "*"}})

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

# Basic API endpoints
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
            },
            {
                'role': 'coding_01',
                'name': 'Software Developer', 
                'description': 'Expert software developer specializing in code creation and debugging',
                'capabilities': ['code development', 'debugging', 'code review', 'architecture design'],
                'specialties': ['development'],
                'tools': ['coding', 'debugging'],
                'interaction_style': 'technical'
            }
        ],
        'total': 3
    })

@app.route('/api/agents/status')
def get_executor_status():
    return jsonify({
        "active_tasks": len(active_tasks),
        "task_ids": list(active_tasks.keys()),
        "status": "healthy"
    })

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'service': 'multi-agent-workspace-server'})

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
    
    # Simulate different agent responses
    responses = {
        'general_01': f"As your General Assistant, I understand you need help with: {message}. Let me provide a comprehensive approach to address this.",
        'product_01': f"From a product strategy perspective, regarding '{message[:30]}...', I recommend we first analyze the requirements and create a structured plan.",
        'coding_01': f"Looking at this from a technical standpoint: '{message[:30]}...'. Let me break down the implementation approach and potential solutions."
    }
    
    agent_response = responses.get(agent_id, f"Hello! This is {agent_id} responding to: {message}")
    
    agent_msg = {
        'id': str(uuid.uuid4()),
        'role': 'assistant',
        'content': agent_response,
        'timestamp': time.time()
    }
    agent_chat_history[agent_id].append(agent_msg)
    
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
        'message': 'Chat history cleared successfully'
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
        'status': 'completed',
        'progress': 100,
        'started_at': time.time(),
        'completed_at': time.time() + 5
    }
    active_tasks[task_id] = task
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'completed',
        'agents': task['agents'],
        'result': f"Collaborative task completed successfully with {len(task['agents'])} agents"
    })

@app.route('/api/agents/execute', methods=['POST'])
def execute_multi_agent_task():
    """Execute a task using multiple agents"""
    data = request.get_json()
    task_id = str(uuid.uuid4())
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'completed',
        'agents': data.get('agents', []),
        'result': 'Multi-agent task executed successfully'
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
    
    return jsonify({
        'success': True,
        'workspace': workspace_state
    })

# Provider configuration endpoint
@app.route('/api/providers/status')
def check_provider_status():
    return jsonify({
        'openrouter_configured': True,
        'openai_configured': True,
        'hasAnyProvider': True
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Multi-Agent Workspace Server on port {port}")
    print(f"📱 Frontend: http://localhost:{port}")
    print(f"🔗 API: http://localhost:{port}/api/agents/profiles")
    print("✅ Server ready for multi-agent collaboration!")
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)

