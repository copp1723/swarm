#!/usr/bin/env python3
"""
Complete server with API routes but without problematic async components
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

# --------------------------------------------------------------------------- #
# Optional WebSocket / Socket.IO support
# --------------------------------------------------------------------------- #
# We attempt to load the real-time utilities.  If they are not available
# (e.g. missing dependency or still under development) we fall back to no-ops
# so the server can run without crashing.

try:
    from utils.websocket import init_socketio, task_notifier  # type: ignore
    WEBSOCKET_AVAILABLE = True
    print("WebSocket real-time updates: ENABLED")
except Exception as e:  # ImportError or any other startup failure
    print(f"⚠️  WebSocket module not available ({e}); running without real-time updates")
    WEBSOCKET_AVAILABLE = False

    # Stub notifier with no-op methods so the rest of the code remains unchanged
    class _StubTaskNotifier:
        def send_progress_update(self, *args, **kwargs): ...
        def send_agent_communication_update(self, *args, **kwargs): ...
        def send_task_complete(self, *args, **kwargs): ...
        def send_task_error(self, *args, **kwargs): ...

    task_notifier = _StubTaskNotifier()  # type: ignore

    # Stub init_socketio to keep Flask app initialisation simple
    def init_socketio(app):  # type: ignore
        return None

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

# Initialize Socket.IO
socketio = init_socketio(app)

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
# In-memory task store for simple multi-agent collaboration
# --------------------------------------------------------------------------- #
TASKS = {}
TASK_LOCK = Lock()

# Helper to safely update task dict
def _update_task(task_id: str, **kwargs):
    with TASK_LOCK:
        TASKS[task_id].update(kwargs)

# Helper thread target – orchestrates agent calls sequentially
def _run_collaboration(task_id: str):
    try:
        task = TASKS[task_id]
        agents = task["agents"]
        total_steps = len(agents) + 1  # +1 for executive summary

        for idx, agent_id in enumerate(agents, start=1):
            agent = AGENTS.get(agent_id)
            if not agent:
                _update_task(task_id, status="error",
                             error=f"Agent {agent_id} not found")
                # Send error notification
                task_notifier.send_task_error(task_id, {
                    "error": f"Agent {agent_id} not found",
                    "timestamp": time.time()
                })
                return

            system_prompt = agent.get(
                "system_prompt",
                f"You are {agent.get('name','an AI assistant')} specialised in {agent.get('role','tasks')}.")
            model_pref = agent.get("model") or agent.get(
                "preferred_models", ["openai/gpt-4"]
            )[0]

            user_msg = task["task_description"]
            assistant_reply = call_openrouter_api(
                user_msg, agent_context=system_prompt, model=model_pref
            )

            with TASK_LOCK:
                task["messages"].append(
                    {
                        "agent_id": agent_id,
                        "content": assistant_reply,
                        "timestamp": time.time(),
                    }
                )
                task["progress"] = int(idx / total_steps * 100)

            # After updating task progress, notify WebSocket clients
            task_notifier.send_progress_update(task_id, {
                "progress": task["progress"],
                "status": "running",
                "timestamp": time.time()
            })

            # Send agent communication update when agent reply is appended
            task_notifier.send_agent_communication_update(task_id, {
                "from_agent": agent_id,
                "to_agent": "user",
                "message": assistant_reply,
                "timestamp": time.time(),
                "message_id": uuid.uuid4().hex
            })

        # Final executive summary from General Assistant (if present)
        summary_prompt = (
            "Provide an executive summary of the previous agent responses "
            "in no more than 200 words."
        )
        summary = call_openrouter_api(
            summary_prompt,
            agent_context="You are a helpful executive summary assistant.",
            model="openai/gpt-4",
        )

        with TASK_LOCK:
            task["messages"].append(
                {
                    "agent_id": "executive_summary",
                    "content": summary,
                    "timestamp": time.time(),
                }
            )
            task["progress"] = 100
            task["status"] = "completed"

        # After final summary, send final progress update
        task_notifier.send_progress_update(task_id, {
            "progress": 100,
            "status": "running", 
            "timestamp": time.time()
        })

        # Send agent communication for executive summary
        task_notifier.send_agent_communication_update(task_id, {
            "from_agent": "executive_summary",
            "to_agent": "user",
            "message": summary,
            "timestamp": time.time(),
            "message_id": uuid.uuid4().hex
        })

        # Send task completion notification
        task_notifier.send_task_complete(task_id, {
            "timestamp": time.time()
        })
        
    except Exception as e:
        # Handle any errors in the collaboration process
        _update_task(task_id, status="error", error=str(e))
        task_notifier.send_task_error(task_id, {
            "error": str(e),
            "timestamp": time.time()
        })

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

@app.route('/favicon.ico')
def favicon():
    """Serve favicon from static folder"""
    return send_from_directory(str(static_folder), 'favicon.ico')

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'message': 'Server is running',
        'version': 'v2.0.0',
        'agents_loaded': len(AGENTS)
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
    
    if agent_id not in AGENTS:
        return jsonify({
            'success': False,
            'error': f'Agent {agent_id} not found'
        }), 404
    
    agent = AGENTS[agent_id]
    # Build context & model
    system_prompt = agent.get("system_prompt", f"You are {agent.get('name','an AI assistant')}, expert {agent.get('role','agent')}.")
    model_pref = agent.get("model") or agent.get("preferred_models", ["openai/gpt-4"])[0]

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
    """Start a real multi-agent collaboration task"""
    data = request.get_json()
    task_description = data.get("task_description", "").strip()
    agents = data.get("tagged_agents", [])
    if not task_description or not agents:
        return jsonify(
            {"success": False, "error": "task_description and tagged_agents required"}
        ), 400

    task_id = f"task-{uuid.uuid4().hex[:8]}"
    TASKS[task_id] = {
        "task_id": task_id,
        "task_description": task_description,
        "agents": agents,
        "status": "running",
        "progress": 0,
        "messages": [],
        "created_at": time.time(),
    }

    # Start background thread
    threading.Thread(target=_run_collaboration, args=(task_id,), daemon=True).start()

    return jsonify(
        {
            "success": True,
            "task_id": task_id,
            "status": "running",
            "progress": 0,
        }
    )

# Polling endpoint used by UI to fetch progress & messages
@app.route("/api/agents/conversation/<task_id>", methods=["GET"])
def conversation_status(task_id):
    task = TASKS.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "task not found"}), 404
    return jsonify(
        {
            "success": True,
            "task_id": task_id,
            "status": task["status"],
            "progress": task["progress"],
            "conversations": task["messages"],
        }
    )

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
    """Get chat history for an agent"""
    # Return empty history in minimal mode
    return jsonify({
        'success': True,
        'agent_id': agent_id,
        'conversations': [],
        'total': 0
    })

# Audit routes
@app.route('/api/audit/task/<task_id>', methods=['GET'])
def get_audit_task(task_id):
    """Get audit information for a task (stub)"""
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status': 'completed',
        'timeline': [
            {
                'timestamp': '2025-06-19T13:00:00Z',
                'agent': 'architect',
                'action': 'analyze_request',
                'status': 'success',
                'message': 'Analyzed user request'
            }
        ]
    })

@app.route('/api/audit/task/<task_id>/export', methods=['GET'])
def export_audit(task_id):
    """Export audit data (stub)"""
    format_type = request.args.get('format', 'csv')
    if format_type == 'csv':
        csv_data = "timestamp,agent,action,status,message\n"
        csv_data += "2025-06-19T13:00:00Z,architect,analyze_request,success,Analyzed user request\n"
        
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

if __name__ == '__main__':
    print("Starting SWARM v2.0.0 Server (API Mode)")
    print("-" * 50)
    print(f"Loaded {len(AGENTS)} agents from configuration")
    print("\nServer URLs:")
    print("  Main UI: http://localhost:5006/")
    print("  Audit Dashboard: http://localhost:5006/static/audit-dashboard.html")
    print("  API Endpoints:")
    print("    - GET  /api/agents/list")
    print("    - POST /api/agents/chat/<agent_id>")
    print("    - POST /api/agents/collaborate")
    print("    - GET  /api/audit/task/<task_id>")
    print("    - GET  /api/audit/task/<task_id>/export?format=csv")
    print("\nPress Ctrl+C to stop")
    print("-" * 50)
    
    if WEBSOCKET_AVAILABLE and socketio is not None:  # type: ignore
        socketio.run(app, host='0.0.0.0', port=5006, debug=False)  # type: ignore
    else:
        app.run(host='0.0.0.0', port=5006, debug=False)
