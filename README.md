# MCP Multi-Agent Chat System

A powerful multi-agent AI system for collaborative software development, featuring specialized agents for architecture, coding, testing, security, and DevOps, with advanced NLU capabilities and intelligent task orchestration.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![SQLAlchemy](https://img.shields.io/badge/sqlalchemy-2.0+-red.svg)
![Celery](https://img.shields.io/badge/celery-5.3+-green.svg)
![License](https://img.shields.io/badge/license-MIT-purple.svg)

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Python 3.11+
- Redis (optional, for background tasks)
- OpenRouter API key

### Installation

```bash
# 1. Clone and navigate to the project
cd ~/Desktop/swarm/mcp_new_project

# 2. Set up environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python app.py

# 5. Test the API
curl http://localhost:5006/api/agents/list

# 6. Open the UI
# Navigate to http://localhost:5006 in your browser
```

## ✨ Key Features

### Core Capabilities
- **6 Specialized AI Agents** - Each expert in their domain with unique system prompts
- **Multi-Model Support** - OpenAI, Anthropic, Google, DeepSeek models
- **Natural Language Understanding** - Advanced intent recognition and entity extraction
- **Intelligent Task Orchestration** - Automatic routing and multi-agent coordination
- **Plugin System** - Extensible architecture with hot-reload capability
- **Audit & Explainability** - Complete tracking of agent actions and decisions

### Technical Features
- **MCP Integration** - Full filesystem access via Model Context Protocol
- **Async/Sync Bridge** - Standardized async operations with async_manager
- **Real-time Updates** - WebSocket support for live collaboration
- **Background Tasks** - Celery-powered async task processing
- **High Performance** - Optimized core components with connection pooling
- **Production Ready** - Gunicorn + Uvicorn ASGI server configuration

### New Architecture
- **Simplified DI Container** - Streamlined dependency injection
- **Centralized Blueprint Registry** - Clean Flask blueprint management
- **Optimized Service Registry** - Duplicate-free service registration
- **Improved Async Bridge** - Cached thread pool executors

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Redis (for background tasks)
- Git
- Node.js/npm (for MCP servers)

### Installation

```bash
# Clone the repository
cd ~/Desktop
git clone <repository-url>
cd swarm/mcp_new_project

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OpenRouter API key:
# OPENROUTER_API_KEY=your_key_here

# Initialize MCP servers
cd servers/swarm_mcp
npm install
cd ../..

# Start Redis (if using background tasks)
redis-server  # Or: brew services start redis (macOS)

# Start the server
python app.py

# Open in browser
# http://localhost:5006
```

### Production Deployment

```bash
# Using Gunicorn with Uvicorn workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app

# Or use the provided startup script
python run_server.py
```

## 🤖 Available Agents

| Agent | Role | Best For | Unique Capabilities |
|-------|------|----------|---------------------|
| **Architect** | System Design | Planning, architecture, high-level design | Technology stack recommendations, scalability planning |
| **Developer** | Implementation | Coding, debugging, feature development | Multi-language support, code generation |
| **QA Engineer** | Testing | Test planning, bug finding, quality assurance | Test framework expertise, coverage analysis |
| **Security Analyst** | Security | Vulnerability assessment, threat modeling | OWASP knowledge, security best practices |
| **DevOps Engineer** | Infrastructure | Deployment, CI/CD, automation | Container orchestration, cloud platforms |
| **General Assistant** | Versatile | Any task, general help | Broad knowledge, task coordination |

## 🧠 Natural Language Understanding

### Intent Recognition
The system automatically detects user intent from natural language:
- **Code Development** - "Create a REST API endpoint"
- **Bug Fixing** - "Fix the login crash issue"
- **Code Review** - "Review the auth module for security"
- **Testing** - "Write unit tests for payment processing"
- **Documentation** - "Document the API endpoints"
- **Architecture** - "Design a microservices architecture"
- **Security Analysis** - "Check for SQL injection vulnerabilities"
- **Performance** - "Optimize database queries"
- **Refactoring** - "Refactor the user service"
- **Deployment** - "Deploy to production"
- **Debugging** - "Debug the memory leak"
- **General Query** - "How does the system work?"

### Entity Extraction
Automatically extracts:
- File paths and modules
- Function and class names
- Error types and messages
- Technology stack components
- Urgency and priority levels

## 🎯 Intelligent Orchestration

### Automated Task Routing
```python
# Example: Orchestrated task execution
POST /api/agents/orchestrate
{
    "task": "Fix the critical bug in payment processing",
    "priority": "high",
    "dry_run": false
}

# Response includes:
# - Execution plan with step-by-step breakdown
# - Agent assignments based on expertise
# - Estimated duration
# - Real-time progress tracking
```

### Workflow Templates
Pre-built patterns for common scenarios:
- **Bug Fix Workflow** - Reproduce → Analyze → Fix → Test
- **Feature Development** - Design → Implement → Test → Document
- **Security Audit** - Scan → Analyze → Report → Remediate
- **Code Review** - Analyze → Feedback → Refactor → Validate

## 🔌 Plugin System

### Architecture
- Dynamic plugin discovery from `plugins/` directory
- Hot-reload capability with file watching
- Automatic service registration in DI container
- Plugin lifecycle management (load, reload, unload)

### Available Plugins
- **Analytics Plugin** - Tracks system metrics and usage
- **Test Counter Plugin** - Example plugin for testing

### Creating Custom Plugins
```python
# plugins/my_plugin/__init__.py
from core.plugins import Plugin

class MyPlugin(Plugin):
    def __init__(self):
        self.info = {
            "name": "My Plugin",
            "version": "1.0.0",
            "description": "Custom functionality"
        }

    def load(self):
        # Initialize plugin
        pass

    def get_service(self):
        # Return service instance
        return MyService()
```

## 📊 Audit & Explainability

### Agent Auditing
- Complete tracking of all agent actions
- Decision reasoning and confidence scores
- Performance metrics per agent
- Success/failure analysis

### Explainability Features
```python
# Get explanation for a task
GET /api/audit/explain/{task_id}

# Returns:
# - Agent decisions and reasoning
# - Step-by-step execution trace
# - Performance metrics
# - Improvement suggestions
```

### Audit Levels
- **Minimal** - Basic action logging
- **Standard** - Actions + decisions
- **Detailed** - Full context including prompts
- **Debug** - Complete trace for troubleshooting

## 🛠️ API Endpoints

### Core Agent APIs
- `POST /api/agents/chat/{agent_id}` - Chat with specific agent
- `POST /api/agents/suggest` - Get agent recommendations
- `POST /api/agents/collaborate` - Multi-agent collaboration

### NLU & Orchestration APIs
- `POST /api/agents/analyze` - Analyze task with NLU
- `POST /api/agents/orchestrate` - Execute with intelligent routing

### System APIs
- `GET /api/plugins/` - List loaded plugins
- `GET /api/audit/statistics` - Audit system stats
- `POST /api/audit/level` - Set audit detail level
- `GET /api/mcp/servers` - MCP server status

## ⚡ Performance Optimizations

### Async Architecture
- Standardized on `async_manager` for all async/sync operations
- Cached thread pool executors
- Proper event loop detection and handling
- Lazy loading to prevent circular imports

### Core Optimizations
- **Centralized Blueprint Registry** - Single source for all Flask blueprints
- **Consolidated Database Config** - Unified database configuration
- **Streamlined Service Registry** - Validation and duplicate prevention
- **Extracted Agent Models** - Separated concerns for maintainability
- **Simplified DI Container** - Focus on essential functionality

## 📦 Project Structure
```
mcp_new_project/
├── app.py                  # Main application (optimized)
├── core/                   # Core components
│   ├── blueprint_registry.py    # Centralized blueprints
│   ├── database_config.py       # Database configuration
│   ├── service_registry.py      # Service registration
│   ├── simple_di.py            # Simplified DI
│   └── plugins/                # Plugin system
├── services/               # Business logic
│   ├── nlu_service.py          # Natural Language Understanding
│   ├── orchestrator_service.py # Task orchestration
│   ├── multi_agent_executor.py # Agent execution
│   └── auditing/               # Audit system
├── routes/                 # API endpoints
├── models/                 # Database models
├── utils/                  # Utilities
│   └── async_bridge.py         # Improved async/sync bridge
├── plugins/                # Plugin directory
├── static/                 # Frontend files
└── docs/                   # Documentation
```

## ⌨️ Keyboard Shortcuts

- `Ctrl/Cmd + K` - Quick search
- `Ctrl/Cmd + Enter` - Send message
- `Alt + 1-6` - Focus specific agent
- `Alt + C` - Focus collaboration hub
- `Alt + T` - Toggle theme
- `Ctrl + /` - Show all shortcuts

## 📚 Documentation

- **[Complete Documentation](./docs/README.md)** - Full documentation index
- **[Architecture Guide](./docs/architecture.md)** - System design and components
- **[NLU & Orchestration](./docs/nlu-orchestration.md)** - Intelligence layer
- **[Plugin Development](./docs/plugin-development.md)** - Creating custom plugins
- **[API Reference](./docs/api/README.md)** - Complete API documentation
- **[Agent Reference](./docs/agents/README.md)** - Detailed guide to each agent
- **[Troubleshooting](./docs/troubleshooting.md)** - Common issues and solutions

## 🔧 Troubleshooting UI

### Common UI Issues and Solutions

#### WebSocket Connection Problems
```bash
# Check if WebSocket is connecting
# Open browser DevTools → Console and look for:
✅ WebSocket connected successfully
❌ WebSocket connection error: Failed to connect

# Manual reconnection if needed
# In browser console:
window.app.getWebSocketService().reconnect();
```

#### Module Loading Errors
```bash
# Check for ES6 module compatibility issues
# Common errors in DevTools Console:
- "Failed to resolve module specifier"
- "Unexpected token 'export'"
- "Cannot use import statement outside a module"

# Solution: Ensure scripts are loaded with type="module"
# Check network tab for 404 errors on .js files
```

#### Chat Interface Issues
```bash
# If agents don't respond or interface is broken:

1. Check API configuration:
curl http://localhost:5006/api/agents/list

2. Verify provider status:
curl http://localhost:5006/api/providers/status

3. Check browser console for errors:
- "API key required for chat functionality"
- "Authentication failed"
- "Failed to load agents"

4. Clear localStorage and refresh:
localStorage.clear();
location.reload();
```

#### Source Map Debugging
```bash
# Enable source maps for better debugging:
# 1. Open DevTools → Sources tab
# 2. Verify .js.map files are loading
# 3. Set breakpoints in original source code

# Generate source maps if missing:
python scripts/generate_sourcemaps.py
```

#### Performance Issues
```bash
# Monitor WebSocket health:
window.app.getWebSocketService().getConnectionStatus();

# Check API health:
window.app.getWebSocketService().checkApiHealth();

# Clear chat history to reduce memory:
# Use the trash icon in each agent's chat interface
```

#### Interface Switching Issues
```bash
# Switch between Unified and Classic interfaces:
localStorage.setItem('mcp_interface_preference', 'unified');
# or
localStorage.setItem('mcp_interface_preference', 'classic');
location.reload();

# Force unified workspace:
window.location.href = '/?workspace=unified';
```

#### Debugging Guide

1. **Enable Verbose Logging**:
   ```javascript
   // In browser console:
   localStorage.setItem('debug', 'true');
   ```

2. **Check Network Requests**:
   - Open DevTools → Network tab
   - Look for failed requests (red entries)
   - Check API endpoint responses

3. **Browser Compatibility**:
   - Chrome/Edge: Full ES6 module support
   - Firefox: Full support with latest version
   - Safari: Requires recent version for full compatibility

4. **Resource Loading Issues**:
   ```bash
   # Check static file serving:
   curl http://localhost:5006/static/js/app.js
   curl http://localhost:5006/static/css/main.css
   ```

5. **API Key Configuration**:
   - Ensure `.env` file contains `OPENROUTER_API_KEY`
   - Use the API key setup modal in the UI
   - Check provider configuration endpoints

### Advanced Debugging

For detailed UI debugging, see: [`docs/debug/ui-audit.md`](./docs/debug/ui-audit.md)

#### TypeScript Type Checking
Critical UI modules include `@ts-check` for enhanced debugging:
- `static/js/app-unified.js`
- `static/js/components/chat-interface.js`
- `static/js/services/websocket.js`
- `static/js/services/api-client.js`

Use TypeScript-aware IDEs (VS Code, WebStorm) for better error detection.

## 🧪 Testing

```bash
# Test NLU and Orchestration
python test_nlu_orchestrator.py

# Test Plugin and Audit System
python test_plugin_audit_simple.py

# Test MCP Integration
python test_mcp_chat.py

# Run all diagnostic checks
python diagnose.py
```

## 🤝 Contributing

See [Development Guide](./docs/development.md) for contribution guidelines.

## 📄 License

MIT License - see LICENSE file for details.

## 🔗 Links

- [Report Issues](https://github.com/anthropics/claude-code/issues)
- [Documentation](./docs/README.md)
- [API Reference](./docs/api/README.md)