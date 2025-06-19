# Plugin Development Guide

## Overview

The MCP Multi-Agent Chat System features a powerful plugin architecture that allows you to extend functionality without modifying core code. Plugins can add new services, modify agent behavior, integrate external systems, and more.

## Plugin Architecture

### Core Components

```
plugins/                      # Plugin directory
├── __init__.py              # Plugin loader initialization
├── analytics_plugin/        # Example: Analytics plugin
│   ├── __init__.py         # Plugin entry point
│   └── analytics.py        # Plugin implementation
└── my_custom_plugin/       # Your plugin
    ├── __init__.py         # Required: Plugin class
    ├── config.json         # Optional: Configuration
    └── requirements.txt    # Optional: Dependencies
```

### Plugin Lifecycle

```
┌──────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
│ Discovery │────▶│   Load   │────▶│Initialize │────▶│  Active  │
└──────────┘     └──────────┘     └───────────┘     └──────────┘
                                                           │
                                                           ▼
┌──────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
│  Removed │◀────│  Unload  │◀────│   Reload  │◀────│  Monitor │
└──────────┘     └──────────┘     └───────────┘     └──────────┘
```

## Creating a Plugin

### Basic Plugin Structure

```python
# plugins/my_plugin/__init__.py
from core.plugins import Plugin
from typing import Dict, Any, Optional

class MyPlugin(Plugin):
    """Example plugin implementation"""
    
    def __init__(self):
        """Initialize plugin metadata"""
        self.info = {
            "name": "My Custom Plugin",
            "version": "1.0.0",
            "description": "Adds custom functionality",
            "author": "Your Name",
            "dependencies": ["requests>=2.28.0"]
        }
        self.service = None
    
    def load(self) -> bool:
        """Load plugin and initialize resources"""
        try:
            # Initialize your plugin components
            from .my_service import MyService
            self.service = MyService()
            
            # Register with dependency injection
            self._register_services()
            
            # Set up any hooks or event listeners
            self._setup_hooks()
            
            print(f"{self.info['name']} loaded successfully")
            return True
        except Exception as e:
            print(f"Failed to load {self.info['name']}: {e}")
            return False
    
    def unload(self) -> bool:
        """Clean up plugin resources"""
        try:
            # Unregister services
            self._unregister_services()
            
            # Clean up resources
            if self.service:
                self.service.cleanup()
            
            print(f"{self.info['name']} unloaded")
            return True
        except Exception as e:
            print(f"Error unloading {self.info['name']}: {e}")
            return False
    
    def reload(self) -> bool:
        """Reload plugin (hot-reload support)"""
        self.unload()
        return self.load()
    
    def get_service(self) -> Optional[Any]:
        """Return the main service instance"""
        return self.service
    
    def get_info(self) -> Dict[str, Any]:
        """Return plugin metadata"""
        return self.info
    
    def _register_services(self):
        """Register services with DI container"""
        from core.dependency_injection import get_container
        container = get_container()
        
        # Register your service
        container.register_singleton(
            f'plugin_{self.__class__.__name__}_service',
            self.service
        )
    
    def _unregister_services(self):
        """Unregister services from DI container"""
        from core.dependency_injection import get_container
        container = get_container()
        
        # Remove your service
        service_name = f'plugin_{self.__class__.__name__}_service'
        if service_name in container._singletons:
            del container._singletons[service_name]
    
    def _setup_hooks(self):
        """Set up event hooks and listeners"""
        # Example: Listen for agent events
        from core.events import event_bus
        
        @event_bus.on('agent.task.completed')
        def on_task_completed(task_id, agent_id, result):
            # Your plugin logic here
            if self.service:
                self.service.track_completion(task_id, agent_id)
```

### Service Implementation

```python
# plugins/my_plugin/my_service.py
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class MyService:
    """Main service implementation for the plugin"""
    
    def __init__(self):
        self.data = {}
        self.initialized = False
        self._initialize()
    
    def _initialize(self):
        """Initialize service resources"""
        # Set up database connections, caches, etc.
        self.initialized = True
        logger.info("MyService initialized")
    
    def track_completion(self, task_id: str, agent_id: str):
        """Example method - track task completions"""
        if not self.initialized:
            return
        
        key = f"{agent_id}:{datetime.now().date()}"
        if key not in self.data:
            self.data[key] = []
        
        self.data[key].append({
            'task_id': task_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            'total_tracked': sum(len(v) for v in self.data.values()),
            'agents_tracked': len(set(k.split(':')[0] for k in self.data.keys())),
            'data': self.data
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.data.clear()
        self.initialized = False
        logger.info("MyService cleaned up")
```

## Plugin Types

### 1. Service Plugin
Adds new services to the system:

```python
class DatabasePlugin(Plugin):
    """Adds advanced database functionality"""
    
    def load(self):
        from .advanced_db import AdvancedDatabaseService
        self.service = AdvancedDatabaseService()
        
        # Make available to agents
        from core.service_registry import get_container
        container = get_container()
        container.register_singleton('advanced_db', self.service)
```

### 2. Agent Enhancement Plugin
Modifies or extends agent behavior:

```python
class AgentEnhancerPlugin(Plugin):
    """Enhances agent capabilities"""
    
    def load(self):
        from services.multi_agent_executor import MultiAgentTaskService
        
        # Monkey-patch or extend agent functionality
        original_execute = MultiAgentTaskService.execute_task
        
        def enhanced_execute(self, *args, **kwargs):
            # Pre-processing
            self._pre_process(*args, **kwargs)
            
            # Call original
            result = original_execute(self, *args, **kwargs)
            
            # Post-processing
            return self._post_process(result)
        
        MultiAgentTaskService.execute_task = enhanced_execute
```

### 3. Integration Plugin
Connects to external services:

```python
class SlackIntegrationPlugin(Plugin):
    """Integrates with Slack for notifications"""
    
    def load(self):
        from .slack_service import SlackService
        self.service = SlackService(
            token=os.getenv('SLACK_BOT_TOKEN'),
            channel=os.getenv('SLACK_CHANNEL')
        )
        
        # Listen for important events
        from core.events import event_bus
        
        @event_bus.on('task.failed')
        def notify_failure(task_id, error):
            self.service.send_alert(
                f"Task {task_id} failed: {error}"
            )
```

### 4. Analytics Plugin
Collects and analyzes system metrics:

```python
class AnalyticsPlugin(Plugin):
    """System analytics and monitoring"""
    
    def load(self):
        from .analytics import AnalyticsService
        self.service = AnalyticsService()
        
        # Track all agent interactions
        self._setup_tracking()
    
    def _setup_tracking(self):
        # Hook into agent chat endpoints
        from flask import g, request
        from app import app
        
        @app.before_request
        def track_request():
            g.request_start = time.time()
        
        @app.after_request
        def track_response(response):
            if hasattr(g, 'request_start'):
                duration = time.time() - g.request_start
                self.service.track_request(
                    endpoint=request.endpoint,
                    duration=duration,
                    status=response.status_code
                )
            return response
```

## Advanced Features

### Configuration Management

```python
# plugins/my_plugin/config.json
{
    "enabled": true,
    "settings": {
        "api_key": "${MY_PLUGIN_API_KEY}",
        "endpoint": "https://api.example.com",
        "timeout": 30,
        "retry_count": 3
    },
    "features": {
        "auto_sync": true,
        "cache_results": true,
        "cache_ttl": 3600
    }
}
```

Loading configuration:

```python
import json
import os
from string import Template

class ConfigurablePlugin(Plugin):
    def load(self):
        # Load and process configuration
        self.config = self._load_config()
        
        # Initialize with config
        from .service import ConfigurableService
        self.service = ConfigurableService(self.config)
    
    def _load_config(self):
        config_path = os.path.join(
            os.path.dirname(__file__),
            'config.json'
        )
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Substitute environment variables
        config_str = json.dumps(config)
        template = Template(config_str)
        config_str = template.substitute(os.environ)
        
        return json.loads(config_str)
```

### Event System Integration

```python
class EventDrivenPlugin(Plugin):
    """Plugin that uses the event system"""
    
    def load(self):
        from core.events import event_bus
        
        # Define event handlers
        self.handlers = {
            'agent.chat.started': self.on_chat_started,
            'agent.chat.completed': self.on_chat_completed,
            'task.created': self.on_task_created,
            'task.updated': self.on_task_updated,
            'system.error': self.on_system_error
        }
        
        # Register all handlers
        for event, handler in self.handlers.items():
            event_bus.on(event, handler)
    
    def on_chat_started(self, agent_id, user_id, message):
        """Handle chat start event"""
        logger.info(f"Chat started: {agent_id} with {user_id}")
    
    def on_task_created(self, task_id, task_data):
        """Handle task creation"""
        # Process new task
        pass
    
    def unload(self):
        # Unregister event handlers
        from core.events import event_bus
        for event, handler in self.handlers.items():
            event_bus.off(event, handler)
```

### API Endpoint Addition

```python
from flask import Blueprint, jsonify, request

class APIPlugin(Plugin):
    """Plugin that adds new API endpoints"""
    
    def load(self):
        # Create blueprint
        self.blueprint = Blueprint(
            'my_plugin_api',
            __name__,
            url_prefix='/api/plugins/my-plugin'
        )
        
        # Define routes
        self._setup_routes()
        
        # Register blueprint
        from app import app
        app.register_blueprint(self.blueprint)
    
    def _setup_routes(self):
        @self.blueprint.route('/status', methods=['GET'])
        def get_status():
            return jsonify({
                'plugin': self.info['name'],
                'version': self.info['version'],
                'status': 'active'
            })
        
        @self.blueprint.route('/action', methods=['POST'])
        def perform_action():
            data = request.json
            result = self.service.process(data)
            return jsonify(result)
    
    def unload(self):
        # Note: Flask doesn't support blueprint unregistration
        # In production, you'd need to restart the app
        pass
```

### Database Integration

```python
from sqlalchemy import Column, String, DateTime, Integer
from models.base import Base

class PluginModel(Base):
    """Database model for plugin data"""
    __tablename__ = 'plugin_my_plugin'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True)
    value = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class DatabasePlugin(Plugin):
    def load(self):
        # Create tables
        from utils.database import engine
        PluginModel.metadata.create_all(bind=engine)
        
        # Initialize service with DB access
        from .db_service import PluginDatabaseService
        self.service = PluginDatabaseService()
```

### Hot Reload Support

```python
class HotReloadablePlugin(Plugin):
    """Plugin with enhanced hot-reload support"""
    
    def __init__(self):
        super().__init__()
        self._original_functions = {}
    
    def load(self):
        # Store original functions before modifying
        self._store_originals()
        
        # Apply modifications
        self._apply_modifications()
        
        return True
    
    def _store_originals(self):
        """Store original functions for clean unload"""
        from services.multi_agent_executor import MultiAgentTaskService
        
        self._original_functions['execute_task'] = (
            MultiAgentTaskService.execute_task
        )
    
    def _apply_modifications(self):
        """Apply plugin modifications"""
        from services.multi_agent_executor import MultiAgentTaskService
        
        # Wrap original function
        original = self._original_functions['execute_task']
        
        def wrapped_execute(self, *args, **kwargs):
            # Plugin logic here
            print("Plugin: Before task execution")
            result = original(self, *args, **kwargs)
            print("Plugin: After task execution")
            return result
        
        MultiAgentTaskService.execute_task = wrapped_execute
    
    def unload(self):
        """Restore original functions"""
        from services.multi_agent_executor import MultiAgentTaskService
        
        if 'execute_task' in self._original_functions:
            MultiAgentTaskService.execute_task = (
                self._original_functions['execute_task']
            )
        
        return True
```

## Testing Plugins

### Unit Testing

```python
# tests/test_my_plugin.py
import unittest
from plugins.my_plugin import MyPlugin

class TestMyPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = MyPlugin()
    
    def test_plugin_info(self):
        info = self.plugin.get_info()
        self.assertEqual(info['name'], 'My Custom Plugin')
        self.assertEqual(info['version'], '1.0.0')
    
    def test_load_unload(self):
        # Test loading
        self.assertTrue(self.plugin.load())
        self.assertIsNotNone(self.plugin.get_service())
        
        # Test unloading
        self.assertTrue(self.plugin.unload())
        self.assertIsNone(self.plugin.get_service())
    
    def test_service_functionality(self):
        self.plugin.load()
        service = self.plugin.get_service()
        
        # Test service methods
        service.track_completion('task123', 'agent456')
        stats = service.get_statistics()
        
        self.assertEqual(stats['total_tracked'], 1)
        self.assertEqual(stats['agents_tracked'], 1)
```

### Integration Testing

```python
# tests/test_plugin_integration.py
import requests
import json

def test_plugin_api():
    """Test plugin API endpoints"""
    base_url = "http://localhost:5006"
    headers = {"X-API-Key": "test-key"}
    
    # Check plugin is loaded
    response = requests.get(
        f"{base_url}/api/plugins/",
        headers=headers
    )
    
    plugins = response.json()['plugins']
    assert 'MyPlugin' in plugins
    
    # Test plugin endpoint
    response = requests.get(
        f"{base_url}/api/plugins/my-plugin/status",
        headers=headers
    )
    
    assert response.status_code == 200
    assert response.json()['status'] == 'active'
```

## Best Practices

### 1. Error Handling
Always implement robust error handling:

```python
def load(self):
    try:
        # Load resources
        self._load_resources()
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error loading plugin: {e}")
        return False
```

### 2. Resource Management
Clean up resources properly:

```python
def unload(self):
    try:
        # Close connections
        if hasattr(self, 'db_connection'):
            self.db_connection.close()
        
        # Cancel timers
        if hasattr(self, 'timer'):
            self.timer.cancel()
        
        # Clear caches
        if hasattr(self, 'cache'):
            self.cache.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return False
```

### 3. Configuration Validation
Validate configuration on load:

```python
def _validate_config(self, config):
    """Validate plugin configuration"""
    required_fields = ['api_key', 'endpoint']
    
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    # Validate types
    if not isinstance(config.get('timeout', 30), int):
        raise ValueError("Timeout must be an integer")
    
    # Validate ranges
    if config.get('retry_count', 3) < 0:
        raise ValueError("Retry count must be non-negative")
```

### 4. Documentation
Document your plugin thoroughly:

```python
class WellDocumentedPlugin(Plugin):
    """
    My Custom Plugin
    
    This plugin provides advanced functionality for X, Y, and Z.
    
    Configuration:
        api_key (str): API key for external service
        endpoint (str): API endpoint URL
        timeout (int): Request timeout in seconds (default: 30)
    
    Events:
        Listens to:
            - agent.task.completed
            - system.error
        
        Emits:
            - plugin.my_plugin.processed
            - plugin.my_plugin.error
    
    API Endpoints:
        GET /api/plugins/my-plugin/status - Get plugin status
        POST /api/plugins/my-plugin/process - Process data
    """
```

### 5. Logging
Use appropriate logging levels:

```python
import logging

logger = logging.getLogger(__name__)

class LoggingPlugin(Plugin):
    def load(self):
        logger.info(f"Loading {self.info['name']} v{self.info['version']}")
        
        try:
            self._initialize()
            logger.debug("Initialization complete")
        except Exception as e:
            logger.error(f"Failed to initialize: {e}", exc_info=True)
            return False
        
        logger.info(f"{self.info['name']} loaded successfully")
        return True
```

## Deployment

### Plugin Distribution

Structure for distribution:
```
my_plugin/
├── __init__.py
├── README.md
├── LICENSE
├── requirements.txt
├── config.json.example
├── src/
│   ├── service.py
│   └── models.py
└── tests/
    ├── __init__.py
    └── test_plugin.py
```

### Installation Instructions

Create a `README.md` for your plugin:

```markdown
# My Custom Plugin

## Installation

1. Copy the plugin directory to `plugins/`
2. Install dependencies: `pip install -r plugins/my_plugin/requirements.txt`
3. Configure: Copy `config.json.example` to `config.json` and edit
4. Restart the application

## Configuration

Set the following environment variables:
- `MY_PLUGIN_API_KEY`: Your API key
- `MY_PLUGIN_ENDPOINT`: API endpoint (optional)

## Usage

The plugin automatically processes all completed tasks...
```

## Troubleshooting

### Common Issues

1. **Plugin not loading**
   - Check logs for import errors
   - Verify all dependencies are installed
   - Ensure `__init__.py` exports the plugin class

2. **Configuration errors**
   - Verify environment variables are set
   - Check config.json syntax
   - Validate required fields

3. **Hot reload not working**
   - Some changes require app restart
   - Check for cached imports
   - Verify file monitoring is enabled

### Debug Mode

Enable debug logging for plugins:

```python
# In your plugin
import logging
logging.getLogger(__name__).setLevel(logging.DEBUG)

# Or globally in .env
PLUGIN_DEBUG=true
```