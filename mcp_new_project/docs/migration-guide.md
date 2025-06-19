# Migration Guide - Recent Architecture Updates

## Overview

This guide covers the recent architectural improvements and changes to the MCP Multi-Agent Chat System. If you have existing code or integrations, follow this guide to update your implementation.

## Major Changes

### 1. Async/Sync Architecture Standardization

**Before:**
```python
# Old approach - inconsistent async handling
import asyncio

# In various files
result = asyncio.run(some_async_function())
```

**After:**
```python
# New approach - standardized through async_manager
from utils.async_wrapper import async_manager

# Consistent across all files
result = async_manager.run_sync(some_async_function())
```

**Migration Steps:**
1. Search for all `asyncio.run()` calls in your code
2. Replace with `async_manager.run_sync()`
3. Import `async_manager` from `utils.async_wrapper`

### 2. Service Registry Optimization

**Before:**
```python
# Old service registry with duplicates
from core.service_registry import get_service

# Might have duplicate registrations
service = get_service('some_service')
```

**After:**
```python
# Optimized registry with validation
from core.service_registry import get_service, get_required_service

# Guaranteed single instance
service = get_required_service('some_service')  # Throws if not found
```

**Migration Steps:**
1. Review service registrations for duplicates
2. Use `get_required_service()` for critical services
3. Remove any manual duplicate checking

### 3. New NLU and Orchestration System

**Before:**
```python
# Manual agent selection
response = requests.post('/api/agents/suggest', json={
    'task': 'Fix the bug in login'
})
agents = response.json()['suggested_roles']

# Then manually execute with each agent
```

**After:**
```python
# Automatic orchestration with NLU
response = requests.post('/api/agents/orchestrate', json={
    'task': 'Fix the bug in login',
    'dry_run': False
})
# Automatically analyzes, routes, and executes
```

**New Endpoints:**
- `POST /api/agents/analyze` - NLU analysis only
- `POST /api/agents/orchestrate` - Full orchestration

### 4. Simplified Dependency Injection

**Before:**
```python
# Complex DI with auto-wiring
from core.dependency_injection import Container, AutoWire

@AutoWire
class MyService:
    def __init__(self, logger, config, db):
        # Complex auto-wiring magic
```

**After:**
```python
# Simple, explicit DI
from core.simple_di import get_container

container = get_container()
container.register_singleton('my_service', MyService())
```

**Migration Steps:**
1. Remove `@AutoWire` decorators
2. Explicitly register services
3. Use factory functions for complex initialization

### 5. Blueprint Registry Centralization

**Before (in app.py):**
```python
# Scattered blueprint imports and registration
from routes.agents import agents_bp
from routes.tasks import tasks_bp
# ... many more imports

app.register_blueprint(agents_bp)
app.register_blueprint(tasks_bp)
# ... many more registrations
```

**After:**
```python
# Single centralized registration
from core.blueprint_registry import BlueprintRegistry

BlueprintRegistry.register_all_blueprints(app)
```

**Migration Steps:**
1. Move blueprint registrations to `core/blueprint_registry.py`
2. Update `app.py` to use centralized registration
3. Add new blueprints to the registry

### 6. Improved Async Bridge

**Before:**
```python
# Old async wrapper
from utils.async_wrapper import AsyncManager

async_manager = AsyncManager()
result = async_manager.run_sync(coro)
```

**After:**
```python
# New async bridge with better performance
from utils.async_bridge import async_bridge

# Direct usage
result = async_bridge.run_sync(coro)

# Flask route decorator
@app.route('/endpoint')
@async_bridge.async_route
async def my_async_route():
    await some_async_operation()
    return jsonify(result)
```

**Features Added:**
- Cached thread pool executor
- Better event loop detection
- Route decorators for Flask
- Resource cleanup

## Breaking Changes

### 1. Circular Import Fix in MultiAgentExecutor

**Impact:** If you import `MultiAgentTaskService` directly

**Before:**
```python
from services.multi_agent_executor import MultiAgentTaskService
# Might cause circular import with service_registry
```

**After:**
```python
# Still works, but auditor is now lazy-loaded
from services.multi_agent_executor import MultiAgentTaskService
# No more circular import issues
```

### 2. Database Configuration Changes

**Impact:** Custom database configurations

**Before:**
```python
# In app.py
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# ... more config
```

**After:**
```python
# Centralized in core/database_config.py
from core.database_config import DatabaseConfig
DatabaseConfig.configure(app)
```

### 3. Model Extraction from MultiAgentExecutor

**Impact:** If you import models from multi_agent_executor

**Before:**
```python
from services.multi_agent_executor import ChatMessage, AgentTask
```

**After:**
```python
from core.agent_models import ChatMessage, AgentTask
```

## New Features to Adopt

### 1. NLU-Powered Task Analysis

```python
# Analyze any task description
response = requests.post('/api/agents/analyze', 
    headers={'X-API-Key': 'your-key'},
    json={'task': 'Create a secure login system with 2FA'}
)

analysis = response.json()['analysis']
print(f"Intent: {analysis['intent']['primary']}")
print(f"Entities: {analysis['entities']}")
print(f"Recommended agents: {analysis['structured_task']['recommended_agents']}")
```

### 2. Intelligent Orchestration

```python
# Let the system handle everything
response = requests.post('/api/agents/orchestrate',
    headers={'X-API-Key': 'your-key'},
    json={
        'task': 'Build and test a REST API for user management',
        'priority': 'high',
        'dry_run': True  # Test the plan first
    }
)

plan = response.json()['plan']
print(f"Workflow: {plan['routing']['workflow_type']}")
print(f"Steps: {len(plan['execution_steps'])}")
print(f"Estimated duration: {plan['estimated_duration']}s")
```

### 3. Plugin System

```python
# Create a custom plugin
# plugins/my_plugin/__init__.py
from core.plugins import Plugin

class MyPlugin(Plugin):
    def __init__(self):
        self.info = {
            "name": "My Plugin",
            "version": "1.0.0"
        }
    
    def load(self):
        # Your plugin logic
        return True
```

### 4. Audit System Integration

```python
# Get audit statistics
response = requests.get('/api/audit/statistics',
    headers={'X-API-Key': 'your-key'}
)

stats = response.json()['statistics']
print(f"Total audited actions: {stats['total_records']}")
print(f"Success rate: {stats['success_rate']}%")
```

## Performance Improvements

### 1. Async Database Operations
- All database operations now use async/await
- Connection pooling enabled by default
- Significant performance improvement for concurrent requests

### 2. Cached Thread Pool Executors
- Thread pools are now cached and reused
- Reduces overhead for async/sync conversions
- Better resource utilization

### 3. Lazy Loading
- Services are loaded only when needed
- Prevents circular imports
- Faster startup time

## Configuration Updates

### Environment Variables

New environment variables:
```bash
# Enable hot reload for plugins
ENABLE_HOT_RELOAD=true

# Audit system configuration
AUDIT_LEVEL=detailed  # minimal, standard, detailed, debug

# NLU confidence threshold
NLU_CONFIDENCE_THRESHOLD=0.7
```

### Feature Flags

```python
# In config.py
FEATURES = {
    'nlu_enabled': True,          # Enable NLU analysis
    'orchestration_enabled': True, # Enable orchestration
    'audit_system': True,         # Enable auditing
    'plugin_system': True,        # Enable plugins
    'hot_reload': True           # Enable plugin hot reload
}
```

## Testing Your Migration

### 1. Run Diagnostic Tests

```bash
# Check system health
python diagnose.py

# Test NLU and orchestration
python test_nlu_orchestrator.py

# Test plugin system
python test_plugin_audit_simple.py
```

### 2. Verify API Compatibility

```python
# Test script to verify your integration
import requests

base_url = 'http://localhost:5006'
api_key = 'your-api-key'

# Test traditional chat (should still work)
response = requests.post(
    f'{base_url}/api/agents/chat/developer_01',
    headers={'X-API-Key': api_key},
    json={'message': 'Hello'}
)
assert response.status_code == 200

# Test new orchestration
response = requests.post(
    f'{base_url}/api/agents/orchestrate',
    headers={'X-API-Key': api_key},
    json={'task': 'Test task', 'dry_run': True}
)
assert response.status_code == 200
```

## Rollback Plan

If you encounter issues:

1. **Code Rollback:**
   ```bash
   git checkout <previous-commit>
   pip install -r requirements.txt
   ```

2. **Database Rollback:**
   - No schema changes in this update
   - Audit tables are additive only

3. **Configuration Rollback:**
   - Restore previous `.env` file
   - Remove new feature flags

## Getting Help

If you encounter issues during migration:

1. Check the [Troubleshooting Guide](./troubleshooting.md)
2. Review the [Architecture Guide](./architecture.md)
3. Report issues at [GitHub Issues](https://github.com/anthropics/claude-code/issues)

## Timeline

### Phase 1 (Immediate)
- Update async/sync calls
- Fix any circular imports
- Test basic functionality

### Phase 2 (1 week)
- Adopt NLU analysis
- Test orchestration
- Update API integrations

### Phase 3 (2 weeks)
- Develop custom plugins
- Integrate audit system
- Optimize based on metrics

## Summary

The recent updates bring:
- **Better Performance** - Async operations, caching, optimization
- **Smarter Routing** - NLU-based task analysis and orchestration
- **Extensibility** - Plugin system with hot reload
- **Observability** - Comprehensive audit and explainability
- **Cleaner Architecture** - Simplified DI, centralized configuration

While there are some breaking changes, the migration path is straightforward and the benefits significant. The system is now more maintainable, performant, and intelligent.