#!/usr/bin/env python3
"""
Ultra-simple demo server for multi-agent workspace
"""
from flask import Flask, send_from_directory, jsonify, request
import os
import uuid
import time

app = Flask(__name__, static_folder='static')

# In-memory storage
agent_history = {}

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Serve static files
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/agents/profiles')
def profiles():
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
                'capabilities': ['product planning', 'requirements analysis'],
                'specialties': ['product'],
                'tools': [],
                'interaction_style': 'structured'
            },
            {
                'role': 'coding_01',
                'name': 'Software Developer', 
                'description': 'Expert software developer',
                'capabilities': ['code development', 'debugging'],
                'specialties': ['development'],
                'tools': ['coding', 'debugging'],
                'interaction_style': 'technical'
            }
        ],
        'total': 3
    })

@app.route('/api/agents/chat/<agent_id>', methods=['POST'])
def chat(agent_id):
    data = request.get_json()
    message = data.get('message', '')
    
    if agent_id not in agent_history:
        agent_history[agent_id] = []
    
    response_text = f"Hi! I'm {agent_id} and I received: {message}"
    
    return jsonify({
        'success': True,
        'response': response_text,
        'message_id': str(uuid.uuid4())
    })

@app.route('/api/agents/chat_history/<agent_id>')
def get_history(agent_id):
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        'history': agent_history.get(agent_id, [])
    })

if __name__ == '__main__':
    port = 8000
    print(f"🚀 Demo server starting on port {port}")
    print(f"📱 Open: http://localhost:{port}")
    app.run(host='127.0.0.1', port=port, debug=False)

