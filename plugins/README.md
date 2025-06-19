# Plugin Directory

This directory contains dynamically loadable service plugins. Drop your plugin files here and they will be automatically loaded and registered with the DI container.

## Creating a Plugin

Create a Python file that extends `ServicePlugin`:

```python
from core.plugins import ServicePlugin
from core.dependency_injection import Scope

class MyCustomPlugin(ServicePlugin):
    def get_plugin_info(self):
        return {
            'name': 'My Custom Service',
            'version': '1.0.0',
            'description': 'A custom service plugin',
            'type': 'service'
        }
    
    def register_services(self, container):
        # Register your services here
        container.register_factory(
            'my_custom_service',
            lambda: MyCustomService(),
            scope=Scope.SINGLETON
        )
```

Plugins are automatically detected and loaded when:
- The application starts
- A new plugin file is added to this directory
- An existing plugin file is modified

Plugins are automatically unloaded when their files are deleted.