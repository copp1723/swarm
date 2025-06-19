"""
Dynamic Plugin Loader for Service Registration
"""
import os
import importlib
import importlib.util
import logging
from typing import Dict, List, Optional, Type, Any, Callable
from abc import ABC, abstractmethod
from pathlib import Path
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime

from core.dependency_injection import get_container, Scope
from core.interfaces import IService
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ServicePlugin(ABC):
    """Base class for all service plugins"""
    
    @abstractmethod
    def get_plugin_info(self) -> Dict[str, str]:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    def register_services(self, container) -> None:
        """Register services with the DI container"""
        pass
    
    def unregister_services(self, container) -> None:
        """Optional: Clean up services when plugin is unloaded"""
        pass
    
    @property
    def plugin_id(self) -> str:
        """Unique identifier for this plugin"""
        return f"{self.__class__.__module__}.{self.__class__.__name__}"


class PluginFileHandler(FileSystemEventHandler):
    """Watches for changes in plugin directories"""
    
    def __init__(self, plugin_loader: 'PluginLoader'):
        self.plugin_loader = plugin_loader
        self.logger = get_logger(__name__)
    
    def on_created(self, event):
        if event.src_path.endswith('.py') and not event.is_directory:
            self.logger.info(f"New plugin file detected: {event.src_path}")
            asyncio.create_task(self.plugin_loader.load_plugin_from_file(event.src_path))
    
    def on_modified(self, event):
        if event.src_path.endswith('.py') and not event.is_directory:
            self.logger.info(f"Plugin file modified: {event.src_path}")
            asyncio.create_task(self.plugin_loader.reload_plugin_from_file(event.src_path))
    
    def on_deleted(self, event):
        if event.src_path.endswith('.py') and not event.is_directory:
            self.logger.info(f"Plugin file deleted: {event.src_path}")
            asyncio.create_task(self.plugin_loader.unload_plugin_from_file(event.src_path))


class PluginLoader:
    """Dynamic plugin loader with hot-reload support"""
    
    def __init__(self, plugin_directories: List[str] = None):
        self.plugin_directories = plugin_directories or []
        self.loaded_plugins: Dict[str, ServicePlugin] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
        self.observer = Observer()
        self.container = get_container()
        self.logger = get_logger(__name__)
        self._initialization_callbacks: List[Callable] = []
    
    def add_plugin_directory(self, directory: str) -> None:
        """Add a directory to scan for plugins"""
        path = Path(directory)
        if path.exists() and path.is_dir():
            if directory not in self.plugin_directories:
                self.plugin_directories.append(directory)
                self.logger.info(f"Added plugin directory: {directory}")
        else:
            self.logger.warning(f"Plugin directory does not exist: {directory}")
    
    async def start_watching(self) -> None:
        """Start watching plugin directories for changes"""
        handler = PluginFileHandler(self)
        
        for directory in self.plugin_directories:
            if os.path.exists(directory):
                self.observer.schedule(handler, directory, recursive=True)
                self.logger.info(f"Watching plugin directory: {directory}")
        
        self.observer.start()
        self.logger.info("Plugin file watcher started")
    
    def stop_watching(self) -> None:
        """Stop watching for file changes"""
        self.observer.stop()
        self.observer.join()
        self.logger.info("Plugin file watcher stopped")
    
    async def discover_and_load_plugins(self) -> Dict[str, ServicePlugin]:
        """Discover and load all plugins from configured directories"""
        discovered_plugins = {}
        
        for directory in self.plugin_directories:
            if not os.path.exists(directory):
                self.logger.warning(f"Plugin directory not found: {directory}")
                continue
            
            # Look for Python files that might contain plugins
            for file_path in Path(directory).rglob("*.py"):
                if file_path.name.startswith('_'):
                    continue
                
                try:
                    plugin = await self.load_plugin_from_file(str(file_path))
                    if plugin:
                        discovered_plugins[plugin.plugin_id] = plugin
                except Exception as e:
                    self.logger.error(f"Failed to load plugin from {file_path}: {e}")
        
        return discovered_plugins
    
    async def load_plugin_from_file(self, file_path: str) -> Optional[ServicePlugin]:
        """Load a plugin from a specific file"""
        try:
            # Create module name from file path
            module_name = Path(file_path).stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for ServicePlugin subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, ServicePlugin) and 
                    attr is not ServicePlugin):
                    
                    # Instantiate the plugin
                    plugin_instance = attr()
                    plugin_id = plugin_instance.plugin_id
                    
                    # Store metadata
                    self.plugin_metadata[plugin_id] = {
                        'file_path': file_path,
                        'loaded_at': datetime.now(),
                        'info': plugin_instance.get_plugin_info()
                    }
                    
                    # Register services
                    plugin_instance.register_services(self.container)
                    self.loaded_plugins[plugin_id] = plugin_instance
                    
                    self.logger.info(f"Loaded plugin: {plugin_id} from {file_path}")
                    
                    # Call initialization callbacks
                    for callback in self._initialization_callbacks:
                        try:
                            await callback(plugin_instance)
                        except Exception as e:
                            self.logger.error(f"Plugin initialization callback failed: {e}")
                    
                    return plugin_instance
            
        except Exception as e:
            self.logger.error(f"Error loading plugin from {file_path}: {e}")
        
        return None
    
    async def reload_plugin_from_file(self, file_path: str) -> Optional[ServicePlugin]:
        """Reload a plugin when its file is modified"""
        # Find and unload existing plugin from this file
        plugin_to_unload = None
        for plugin_id, metadata in self.plugin_metadata.items():
            if metadata['file_path'] == file_path:
                plugin_to_unload = plugin_id
                break
        
        if plugin_to_unload:
            await self.unload_plugin(plugin_to_unload)
        
        # Load the new version
        return await self.load_plugin_from_file(file_path)
    
    async def unload_plugin_from_file(self, file_path: str) -> None:
        """Unload plugins when their file is deleted"""
        plugins_to_unload = []
        for plugin_id, metadata in self.plugin_metadata.items():
            if metadata['file_path'] == file_path:
                plugins_to_unload.append(plugin_id)
        
        for plugin_id in plugins_to_unload:
            await self.unload_plugin(plugin_id)
    
    async def unload_plugin(self, plugin_id: str) -> None:
        """Unload a specific plugin"""
        if plugin_id in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_id]
            
            try:
                # Let plugin clean up
                plugin.unregister_services(self.container)
            except Exception as e:
                self.logger.error(f"Error during plugin cleanup: {e}")
            
            # Remove from tracking
            del self.loaded_plugins[plugin_id]
            del self.plugin_metadata[plugin_id]
            
            self.logger.info(f"Unloaded plugin: {plugin_id}")
    
    def get_loaded_plugins(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all loaded plugins"""
        result = {}
        for plugin_id, plugin in self.loaded_plugins.items():
            result[plugin_id] = {
                'info': plugin.get_plugin_info(),
                'metadata': self.plugin_metadata.get(plugin_id, {})
            }
        return result
    
    def add_initialization_callback(self, callback: Callable) -> None:
        """Add a callback to be called when new plugins are loaded"""
        self._initialization_callbacks.append(callback)
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.discover_and_load_plugins()
        await self.start_watching()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.stop_watching()
        # Unload all plugins
        for plugin_id in list(self.loaded_plugins.keys()):
            await self.unload_plugin(plugin_id)