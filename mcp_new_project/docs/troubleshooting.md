# Troubleshooting Guide

This guide covers common issues and their solutions when using the MCP Multi-Agent System.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Server Startup Problems](#server-startup-problems)
3. [API and Connection Errors](#api-and-connection-errors)
4. [Agent Response Issues](#agent-response-issues)
5. [File System Access Problems](#filesystem-problems)
6. [Performance Issues](#performance-issues)
7. [UI/Interface Problems](#ui-problems)
8. [Database Issues](#database-issues)

## Installation Issues

### Python Version Mismatch

**Problem**: `ModuleNotFoundError` or syntax errors during installation

**Solution**:
```bash
# Check Python version
python --version

# If < 3.11, upgrade Python
# macOS: brew install python@3.11
# Windows: Download from python.org
# Linux: sudo apt update && sudo apt install python3.11
```

### Missing Dependencies

**Problem**: `pip install` fails with compilation errors

**Solution**:
```bash
# Update pip first
python -m pip install --upgrade pip

# Install system dependencies (Linux/Ubuntu)
sudo apt-get install python3-dev build-essential

# Install system dependencies (macOS)
brew install postgresql  # for psycopg2

# Install with verbose output
pip install -r requirements.txt -v

# If specific package fails, install individually
pip install flask==3.0.0
pip install sqlalchemy==2.0.23
pip install aiosqlite==0.19.0
pip install greenlet==3.0.1
```

### Redis Not Available

**Problem**: `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379`

**Solution**:
```bash
# Install Redis
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt-get install redis-server && sudo systemctl start redis
# Windows: Use WSL2 or download from GitHub

# Test Redis connection
redis-cli ping  # Should return PONG

# Run without Redis (limited functionality)
# Set in .env: CELERY_BROKER_URL=memory://
```

### Node.js Not Found

**Problem**: MCP features not working, "command not found: npx"

**Solution**:
```bash
# Install Node.js
# macOS: brew install node
# Windows: Download from nodejs.org
# Linux: curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
#         sudo apt-get install -y nodejs

# Verify installation
node --version
npm --version
```

## Server Startup Problems

### Port Already in Use

**Problem**: `OSError: [Errno 48] Address already in use`

**Solution**:
```bash
# Find process using port 5006
lsof -i :5006  # macOS/Linux
netstat -ano | findstr :5006  # Windows

# Kill the process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use a different port
PORT=5007 python app.py
```

### Import Errors

**Problem**: `ImportError: cannot import name 'X' from 'Y'`

**Solution**:
```bash
# Ensure you're in the correct directory
cd /Users/copp1723/Desktop/swarm/mcp_new_project

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Database Connection Failed

**Problem**: `sqlalchemy.exc.OperationalError: unable to open database file`

**Solution**:
```bash
# Create instance directory
mkdir -p instance

# Set correct permissions
chmod 755 instance

# Remove corrupted database
rm instance/mcp_executive.db

# Let it recreate on startup
python app.py
```

## API and Connection Errors

### OpenRouter API Key Invalid

**Problem**: `401 Unauthorized` or `Invalid API Key`

**Solution**:
1. Verify API key at https://openrouter.ai/keys
2. Check `.env` file format:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
   ```
3. No quotes around the key
4. Restart server after changes

### Rate Limiting

**Problem**: `429 Too Many Requests`

**Solution**:
```python
# Add to .env
RATE_LIMIT_DELAY=2  # Seconds between requests

# Or implement exponential backoff
# See services/api_client.py for retry logic
```

### Timeout Errors

**Problem**: Agents take too long to respond

**Solution**:
```python
# Increase timeout in services/api_client.py
response = requests.post(
    url,
    timeout=120  # Increase from default 30
)
```

## Agent Response Issues

### Generic or Unhelpful Responses

**Problem**: Agents give vague answers without file references

**Solution**:
1. Ensure working directory is correct
2. Check filesystem access:
   ```bash
   ls -la /Users/copp1723/Desktop
   ```
3. Use specific task descriptions
4. Enable structured prompts in agent config

### Agent Not Responding

**Problem**: No response after sending message

**Checklist**:
1. Check browser console for errors (F12)
2. Verify server is running
3. Check `logs/mcp_server.log`
4. Test with simple message: "Hello"

### Wrong Agent Responding

**Problem**: Agent gives response outside their expertise

**Solution**:
- Verify agent selection in UI
- Check `routes/agents.py` for correct agent mapping
- Clear browser cache

## File System Access Problems {#filesystem-problems}

### Permission Denied

**Problem**: `PermissionError: [Errno 13] Permission denied`

**Solution**:
```bash
# Check directory permissions
ls -la /Users/copp1723/Desktop

# Fix permissions
chmod -R 755 /Users/copp1723/Desktop/your_project

# Run server with correct user
sudo -u your_username python app.py
```

### MCP Server Not Starting

**Problem**: Filesystem tools not available to agents

**Solution**:
1. Check MCP config:
   ```json
   // config/mcp_config.json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/copp1723/Desktop"]
       }
     }
   }
   ```

2. Test MCP manually:
   ```bash
   npx @modelcontextprotocol/server-filesystem /Users/copp1723/Desktop
   ```

3. Check PATH includes npm:
   ```bash
   echo $PATH
   # Should include /usr/local/bin or similar
   ```

### Files Not Found

**Problem**: Agents can't see files that exist

**Solution**:
- Use absolute paths
- Check for symbolic links
- Verify no .gitignore blocking access
- Ensure files aren't in hidden directories

## Performance Issues

### Slow Response Times

**Problem**: Agents take 30+ seconds to respond

**Optimizations**:
1. Use faster models (Claude Sonnet vs Opus)
2. Reduce max tokens in requests
3. Enable response streaming
4. Check network latency to API

### High Memory Usage

**Problem**: Server consuming excessive RAM

**Solution**:
```python
# Limit concurrent tasks in services/multi_agent_executor.py
MAX_CONCURRENT_TASKS = 5

# Clear old conversations periodically
def cleanup_old_chats():
    # Implement cleanup logic
```

### Browser Freezing

**Problem**: UI becomes unresponsive

**Solution**:
- Limit chat history display (last 50 messages)
- Use pagination for long conversations
- Disable animations on older devices
- Clear browser cache

## UI/Interface Problems {#ui-problems}

### Styling Not Loading

**Problem**: Page looks broken, no styles

**Solution**:
1. Check Tailwind CDN is accessible
2. Verify `ux-improvements.css` exists
3. Clear browser cache (Ctrl+Shift+R)
4. Check console for 404 errors

### Dark Mode Not Working

**Problem**: Theme toggle doesn't change appearance

**Solution**:
```javascript
// Check localStorage
console.log(localStorage.getItem('theme'));

// Reset theme
localStorage.removeItem('theme');
location.reload();
```

### Keyboard Shortcuts Not Working

**Problem**: Shortcuts don't trigger actions

**Solution**:
- Ensure `ux-enhancements.js` is loaded
- Check for conflicts with browser shortcuts
- Verify focus is on the page (click anywhere)
- Try different browser

## Database Issues

### Async Database Connection Failed

**Problem**: `error: 'async_generator' object does not support the asynchronous context manager protocol`

**Solution**:
```bash
# Check SQLAlchemy version
pip show sqlalchemy  # Should be 2.0+

# Reinstall async dependencies
pip install --upgrade "sqlalchemy[asyncio]"
pip install --upgrade aiosqlite asyncpg
```

### Database Tables Not Created

**Problem**: `sqlite3.OperationalError: no such table`

**Solution**:
```bash
# Initialize databases manually
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# For async database
python -c "
import asyncio
from utils.db_init import init_async_db
asyncio.run(init_async_db())
"
```

### Connection Pool Exhausted

**Problem**: `TimeoutError: QueuePool limit exceeded`

**Solution**:
```bash
# Increase pool size in .env
ASYNC_DB_POOL_SIZE=20
ASYNC_DB_MAX_OVERFLOW=40

# Or in code
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,
    'max_overflow': 40,
    'pool_pre_ping': True
}
```

## WebSocket Issues

### WebSocket Connection Failed

**Problem**: `WebSocket connection to 'ws://localhost:5006/socket.io/' failed`

**Solution**:
```bash
# Check if eventlet is installed
pip install eventlet==0.33.3

# Verify Flask-SocketIO version
pip show flask-socketio  # Should be 5.3.6+

# Check CORS settings in app.py
CORS(app, resources={r"/*": {"origins": "*"}})
```

### Real-time Updates Not Working

**Problem**: Collaboration progress not updating

**Solution**:
1. Check browser console for WebSocket errors
2. Verify Redis is running (if using)
3. Check eventlet compatibility:
   ```python
   # In app.py, ensure eventlet is imported first
   import eventlet
   eventlet.monkey_patch()
   ```

## Performance Issues

### Slow Async Operations

**Problem**: Async endpoints slower than expected

**Solution**:
```bash
# Use production server
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app

# Enable connection pooling
# In .env:
ASYNC_DB_POOL_SIZE=10
ASYNC_DB_MAX_OVERFLOW=20

# Use PostgreSQL instead of SQLite for production
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### High Memory Usage

**Problem**: Server consuming too much memory

**Solution**:
```bash
# Limit worker memory
gunicorn --max-requests 1000 --max-requests-jitter 50 app:app

# Monitor with
pip install memory_profiler
python -m memory_profiler app.py
```

### Corrupted Database

**Problem**: `DatabaseError: database disk image is malformed`

**Solution**:
```bash
# Backup existing data
cp instance/mcp_executive.db instance/mcp_executive.db.backup

# Remove corrupted database
rm instance/mcp_executive.db

# Recreate
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Migration Errors

**Problem**: Schema changes cause errors

**Solution**:
```bash
# Use Alembic for migrations
pip install alembic
alembic init alembic
alembic revision --autogenerate -m "Update schema"
alembic upgrade head
```

## Diagnostic Commands

### Health Check Script

Create `diagnose.py`:

```python
#!/usr/bin/env python3
import os
import sys
import subprocess

def check_python():
    print(f"Python: {sys.version}")
    return sys.version_info >= (3, 11)

def check_node():
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        print(f"Node.js: {result.stdout.strip()}")
        return True
    except:
        print("Node.js: Not found")
        return False

def check_env():
    api_key = os.getenv('OPENROUTER_API_KEY')
    print(f"API Key: {'Set' if api_key else 'Not set'}")
    return bool(api_key)

def check_imports():
    try:
        import flask
        import sqlalchemy
        import requests
        print("Required packages: Installed")
        return True
    except ImportError as e:
        print(f"Missing package: {e}")
        return False

if __name__ == "__main__":
    checks = [
        ("Python version", check_python),
        ("Node.js", check_node),
        ("Environment", check_env),
        ("Dependencies", check_imports)
    ]
    
    failed = []
    for name, check in checks:
        if not check():
            failed.append(name)
    
    if failed:
        print(f"\n❌ Failed checks: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\n✅ All checks passed!")
```

Run with: `python diagnose.py`

## Getting Further Help

If these solutions don't resolve your issue:

1. **Check Logs**:
   - `logs/mcp_server.log` - Server errors
   - Browser console - Frontend errors
   - `backend/server.log` - Detailed traces

2. **Enable Debug Mode**:
   ```bash
   FLASK_DEBUG=1 python app.py
   ```

3. **Report Issues**:
   - Include error messages
   - Steps to reproduce
   - System information (OS, Python version)
   - Relevant log excerpts

4. **Community Support**:
   - GitHub Issues
   - Discord/Slack channels
   - Stack Overflow with tag `mcp-multi-agent`