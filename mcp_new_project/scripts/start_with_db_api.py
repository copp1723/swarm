#!/usr/bin/env python3
"""
Complete server with API routes and database persistence
Replaces in-memory TASKS with persistent database storage
"""
import os
import sys
import json
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
import requests
import time
import uuid
import threading
from threading import Lock

# Set up paths
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))
os.chdir(project_dir)

# Load environment
env_file = project_dir / 'config' / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Create Flask app with absolute path to static folder
static_folder = project_dir / 'static'
app = Flask(__name__, static_folder=str(static_folder), static_url_path='/static')
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize database
from config.database import init_database, create_all_tables
from models.core import db
init_database(app)

# Initialize Socket.IO if available
try:
    from utils.websocket import init_socketio, task_notifier
    socketio = init_socketio(app)
except ImportError:
    socketio = None
    print("Warning: Socket.IO not available, real-time updates disabled")

# Import database task storage
from services.db_task_storage import get_task_storage, log_action

# Load agents configuration
agents_file = project_dir / 'config' / 'agents.json'
try:
    with open(agents_file) as f:
        agents_config = json.load(f)
        # Handle both old and new formats
        if 'AGENT_PROFILES' in agents_config:
            AGENTS = agents_config['AGENT_PROFILES']
        elif 'agents' in agents_config and isinstance(agents_config['agents'], dict):
            AGENTS = agents_config['agents']
        else:
            # Try to build from array
            AGENTS = {}
            agent_list = agents_config.get('agents', [])
            profiles = agents_config.get('AGENT_PROFILES', {})
            for agent_id in agent_list:
                if agent_id in profiles:
                    AGENTS[agent_id] = profiles[agent_id]
except Exception as e:
    print(f"Warning: Could not load agents.json: {e}")
    AGENTS = {}

# --------------------------------------------------------------------------- #
# Database initialization
# --------------------------------------------------------------------------- #
with app.app_context():
    create_all_tables(db)
    print("Database tables created successfully")

# Get task storage instance
task_storage = get_task_storage()

# --------------------------------------------------------------------------- #
# Helper: OpenRouter API call
# --------------------------------------------------------------------------- #

def call_openrouter_api(
    message: str,
    agent_context: str = "",
    model: str = "openai/gpt-4",
    temperature: float = 0.7,
) -> str:
    """
    Send a single-turn chat completion request.
    
    Priority:
    1. Use OpenRouter if `OPENROUTER_API_KEY` is configured.
    2. Fallback to direct OpenAI call if `OPENAI_API_KEY` is configured.
    3. Return a clear error message if no keys are available or the request fails.
    """

    system_prompt = agent_context or "You are a helpful AI assistant."

    # 1) ----------  OpenRouter  ----------
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {or_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            # Fall through to OpenAI fallback if possible
            fallback_reason = f"OpenRouter error: {exc}"
    else:
        fallback_reason = "OPENROUTER_API_KEY not set"

    # 2) ----------  OpenAI Fallback  ----------
    oa_key = os.environ.get("OPENAI_API_KEY")
    if oa_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {oa_key}",
                "Content-Type": "application/json",
            }
            # Map model name if caller still passes "openai/gpt-4"
            oa_model = model.split("/")[-1] if "/" in model else model
            payload = {
                "model": oa_model,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message},
                ],
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            return f"API Error (OpenRouter fallback: {fallback_reason}) -> OpenAI error: {exc}"

    # 3) ----------  No Keys Available  ----------
    return (
        "API Error: No valid API key found. "
        "Set OPENROUTER_API_KEY or OPENAI_API_KEY in your environment."
    )

# --------------------------------------------------------------------------- #
# Background task runner with database persistence
# --------------------------------------------------------------------------- #

# Helper thread target – orchestrates agent calls sequentially
def _run_collaboration(task_id: str):
    task = task_storage.get_task(task_id)
    if not task:
        print(f"Task {task_id} not found in database")
        return
        
    agents = task.get("agents", [])
    total_steps = len(agents) + 1  # +1 for executive summary

    for idx, agent_id in enumerate(agents, start=1):
        agent = AGENTS.get(agent_id)
        if not agent:
            task_storage.update_task(
                task_id, 
                status="error",
                error_message=f"Agent {agent_id} not found"
            )
            return

        system_prompt = agent.get(
            "system_prompt",
            f"You are {agent.get('name','an AI assistant')} specialised in {agent.get('role','tasks')}."
        )
        model_pref = agent.get("model") or agent.get(
            "preferred_models", ["openai/gpt-4"]
        )[0]

        user_msg = task["description"]
        
        # Log API call
        log_action(
            action_type='api_call',
            action_description=f'Calling {model_pref} for agent {agent_id}',
            agent_id=agent_id,
            task_id=task_id,
            metadata={'model': model_pref}
        )
        
        assistant_reply = call_openrouter_api(
            user_msg, agent_context=system_prompt, model=model_pref
        )

        # Store conversation in database
        task_storage.add_message(
            task_id=task_id,
            agent_id=agent_id,
            content=assistant_reply,
            role='assistant',
            model_used=model_pref
        )
        
        # Update progress
        progress = int(idx / total_steps * 100)
        task_storage.update_task(
            task_id,
            progress=progress,
            current_phase=f"Agent {agent_id} processing"
        )
        
        # Notify via websocket if available
        if socketio:
            from utils.websocket import task_notifier
            task_notifier.notify_task_update(task_id, {
                'progress': progress,
                'phase': f"Agent {agent_id} completed"
            })

    # Final executive summary from General Assistant (if present)
    summary_prompt = (
        "Provide an executive summary of the previous agent responses "
        "in no more than 200 words."
    )
    
    log_action(
        action_type='summary_generation',
        action_description='Generating executive summary',
        agent_id='executive_summary',
        task_id=task_id
    )
    
    summary = call_openrouter_api(
        summary_prompt,
        agent_context="You are a helpful executive summary assistant.",
        model="openai/gpt-4",
    )

    # Store summary
    task_storage.add_message(
        task_id=task_id,
        agent_id='executive_summary',
        content=summary,
        role='assistant'
    )
    
    # Mark task as completed
    task_storage.update_task(
        task_id,
        status='completed',
        progress=100,
        current_phase='Summary complete',
        summary=summary
    )
    
    # Final notification
    if socketio:
        task_notifier.notify_task_complete(task_id, summary)

# Basic routes
@app.route('/')
def index():
    index_path = static_folder / 'index.html'
    if index_path.exists():
        return send_file(str(index_path))
    else:
        return f"index.html not found at {index_path}", 404

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(str(static_folder), filename)

@app.route('/health')
def health():
    # Test database connection
    db_status = 'connected'
    try:
        db.session.execute('SELECT 1')
        task_count = task_storage.get_all_tasks()
        db_status = f'connected ({len(task_count)} tasks)'
    except Exception as e:
        db_status = f'error: {str(e)}'
        
    return jsonify({
        'status': 'ok',
        'message': 'Server is running with database persistence',
        'version': 'v2.1.0',
        'agents_loaded': len(AGENTS),
        'database': db_status,
        'features': {
            'persistence': True,
            'audit_trail': True,
            'conversation_history': True,
            'websockets': socketio is not None
        }
    })

# Agent API routes
@app.route('/api/agents/list', methods=['GET'])
def list_agents():
    """List all available agent profiles"""
    profiles = []
    for agent_id, agent_data in AGENTS.items():
        profile = {
            'agent_id': agent_id,
            'name': agent_data.get('name', agent_id),
            'role': agent_data.get('role', 'specialist'),
            'description': agent_data.get('description', ''),
            'capabilities': agent_data.get('capabilities', []),
            'model_preferences': agent_data.get('model_preferences', []),
            'status': 'online'
        }
        profiles.append(profile)
    
    return jsonify({
        'success': True,
        'profiles': profiles,
        'total': len(profiles)
    })

@app.route('/api/agents/chat/<agent_id>', methods=['POST'])
def chat_with_agent(agent_id):
    """Chat with a specific agent (real OpenRouter call)"""
    data = request.get_json()
    message = data.get('message', '')
    session_id = data.get('session_id', f"session_{int(time.time())}")
    
    if agent_id not in AGENTS:
        return jsonify({
            'success': False,
            'error': f'Agent {agent_id} not found'
        }), 404
    
    agent = AGENTS[agent_id]
    # Build context & model
    system_prompt = agent.get("system_prompt", f"You are {agent.get('name','an AI assistant')}, expert {agent.get('role','agent')}.")
    model_pref = agent.get("model") or agent.get("preferred_models", ["openai/gpt-4"])[0]

    # Log chat request
    log_action(
        action_type='agent_chat',
        action_description=f'Chat with agent {agent_id}',
        agent_id=agent_id,
        session_id=session_id,
        metadata={'message_preview': message[:100]}
    )

    start_ts = time.time()
    assistant_reply = call_openrouter_api(message, agent_context=system_prompt, model=model_pref)
    elapsed = round(time.time() - start_ts, 2)

    return jsonify({
        "success": True,
        "agent_id": agent_id,
        "response": assistant_reply,
        "model_used": model_pref,
        "elapsed_sec": elapsed
    })

@app.route('/api/agents/collaborate', methods=['POST'])
def collaborate():
    """Start a real multi-agent collaboration task with database persistence"""
    data = request.get_json()
    task_description = data.get("task_description", "").strip()
    agents = data.get("tagged_agents", [])
    session_id = data.get("session_id", f"session_{int(time.time())}")
    
    if not task_description or not agents:
        return jsonify(
            {"success": False, "error": "task_description and tagged_agents required"}
        ), 400

    task_id = f"task-{uuid.uuid4().hex[:8]}"
    
    # Create task in database
    task = task_storage.create_task(
        task_id=task_id,
        description=task_description,
        agents=agents,
        session_id=session_id,
        status='running',
        task_description=task_description  # Legacy field
    )

    # Start background thread
    threading.Thread(target=_run_collaboration, args=(task_id,), daemon=True).start()

    return jsonify({
        "success": True,
        "task_id": task_id,
        "status": "running",
        "progress": 0,
        "persistent": True
    })

# Polling endpoint used by UI to fetch progress & messages
@app.route("/api/agents/conversation/<task_id>", methods=["GET"])
def conversation_status(task_id):
    task = task_storage.get_task(task_id)
    if not task:
        return jsonify({"success": False, "error": "task not found"}), 404
    
    # Get full conversation history from database
    conversations = task_storage.get_task_conversations(task_id)
    
    # Format for legacy UI compatibility
    messages = []
    for conv in conversations:
        messages.append({
            'agent_id': conv['agent_id'],
            'content': conv['content'],
            'timestamp': conv.get('created_at', time.time())
        })
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "progress": task.get("progress", 0),
        "conversations": messages,
        "summary": task.get("summary"),
        "persistent": True
    })

@app.route('/api/agents/workflows', methods=['GET'])
def get_workflows():
    """Get available workflows"""
    # Return default workflows if config not available
    return jsonify({
        'success': True,
        'workflows': [
            {
                'id': 'code_review',
                'name': 'Code Review',
                'description': 'Multi-agent code review process',
                'agents': ['coding_01', 'bug_01']
            },
            {
                'id': 'feature_planning',
                'name': 'Feature Planning',
                'description': 'Plan and design new features',
                'agents': ['product_01', 'coding_01']
            }
        ]
    })

@app.route('/api/agents/chat_history/<agent_id>', methods=['GET'])
def get_chat_history(agent_id):
    """Get chat history for an agent from database"""
    limit = request.args.get('limit', 50, type=int)
    history = task_storage.get_agent_history(agent_id, limit)
    
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        'conversations': history,
        'total': len(history)
    })

# Task management routes
@app.route('/api/tasks', methods=['GET'])
def list_tasks():
    """List all tasks from database"""
    session_id = request.args.get('session_id')
    status = request.args.get('status')
    
    tasks = task_storage.get_all_tasks(session_id=session_id, status=status)
    
    return jsonify({
        'success': True,
        'tasks': tasks,
        'total': len(tasks)
    })

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task_details(task_id):
    """Get detailed task information"""
    task = task_storage.get_task(task_id)
    if not task:
        return jsonify({'success': False, 'error': 'Task not found'}), 404
    
    # Get full conversation history
    conversations = task_storage.get_task_conversations(task_id)
    task['conversation_history'] = conversations
    
    return jsonify({
        'success': True,
        'task': task
    })

# Audit routes
@app.route('/api/audit/task/<task_id>', methods=['GET'])
def get_audit_task(task_id):
    """Get audit information for a task from database"""
    from models.task_storage import AuditLog
    
    # Get audit logs for this task
    logs = AuditLog.query.filter_by(task_id=task_id).order_by(AuditLog.created_at).all()
    
    timeline = []
    for log in logs:
        timeline.append({
            'timestamp': log.created_at.isoformat(),
            'agent': log.agent_id,
            'action': log.action_type,
            'status': 'success' if log.success else 'error',
            'message': log.action_description,
            'error': log.error_message
        })
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'timeline': timeline,
        'total_actions': len(timeline)
    })

@app.route('/api/audit/task/<task_id>/export', methods=['GET'])
def export_audit(task_id):
    """Export audit data from database"""
    from models.task_storage import AuditLog
    format_type = request.args.get('format', 'csv')
    
    # Get audit logs
    logs = AuditLog.query.filter_by(task_id=task_id).order_by(AuditLog.created_at).all()
    
    if format_type == 'csv':
        csv_data = "timestamp,agent,action,status,message,error\n"
        for log in logs:
            status = 'success' if log.success else 'error'
            csv_data += f"{log.created_at.isoformat()},{log.agent_id},{log.action_type},{status},{log.action_description},{log.error_message or ''}\n"
        
        from flask import Response
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=audit_task_{task_id}.csv'
            }
        )
    else:
        return jsonify({'error': 'Format not supported'}), 501

# Database maintenance route
@app.route('/api/admin/cleanup', methods=['POST'])
def cleanup_old_tasks():
    """Clean up old tasks from database"""
    data = request.get_json()
    days = data.get('days', 30)
    
    # Only allow with admin key
    admin_key = request.headers.get('X-Admin-Key')
    if admin_key != os.environ.get('ADMIN_KEY', 'default-admin-key'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    deleted = task_storage.cleanup_old_tasks(days)
    
    return jsonify({
        'success': True,
        'deleted_tasks': deleted,
        'message': f'Deleted {deleted} tasks older than {days} days'
    })

if __name__ == '__main__':
    print("Starting SWARM v2.1.0 Server (Database Persistence Mode)")
    print("-" * 50)
    print(f"Loaded {len(AGENTS)} agents from configuration")
    print("\nServer URLs:")
    print("  Main UI: http://localhost:5006/")
    print("  API Endpoints:")
    print("    - GET  /api/agents/list")
    print("    - POST /api/agents/chat/<agent_id>")
    print("    - POST /api/agents/collaborate")
    print("    - GET  /api/tasks")
    print("    - GET  /api/audit/task/<task_id>")
    print("    - GET  /api/audit/task/<task_id>/export?format=csv")
    print("\nDatabase Features:")
    print("  ✅ Tasks persist across restarts")
    print("  ✅ Full conversation history")
    print("  ✅ Comprehensive audit trail")
    print("  ✅ Agent memory across sessions")
    print("\nPress Ctrl+C to stop")
    print("-" * 50)
    
    if socketio:
        socketio.run(app, host='0.0.0.0', port=5006, debug=False)
    else:
        app.run(host='0.0.0.0', port=5006, debug=False)