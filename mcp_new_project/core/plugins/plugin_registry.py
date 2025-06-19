"""
Plugin Registry for Managing Dynamic Services
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from pathlib import Path

from utils.logging_config import get_logger

logger = get_logger(__name__)


class PluginRegistry:
    """Central registry for all dynamically loaded plugins"""
    
    def __init__(self, registry_file: Optional[str] = None):
        self.registry_file = registry_file
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger(__name__)
        
        if self.registry_file and Path(self.registry_file).exists():
            self.load_registry()
    
    def register_plugin(self, plugin_id: str, metadata: Dict[str, Any]) -> None:
        """Register a plugin in the registry"""
        self.plugins[plugin_id] = {
            'id': plugin_id,
            'metadata': metadata,
            'registered_at': datetime.now().isoformat(),
            'status': 'active'
        }
        self.save_registry()
        self.logger.info(f"Registered plugin: {plugin_id}")
    
    def unregister_plugin(self, plugin_id: str) -> None:
        """Remove a plugin from the registry"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id]['status'] = 'inactive'
            self.plugins[plugin_id]['unregistered_at'] = datetime.now().isoformat()
            self.save_registry()
            self.logger.info(f"Unregistered plugin: {plugin_id}")
    
    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin information"""
        return self.plugins.get(plugin_id)
    
    def get_active_plugins(self) -> List[Dict[str, Any]]:
        """Get all active plugins"""
        return [
            plugin for plugin in self.plugins.values()
            if plugin.get('status') == 'active'
        ]
    
    def get_plugins_by_type(self, plugin_type: str) -> List[Dict[str, Any]]:
        """Get plugins by their type"""
        return [
            plugin for plugin in self.plugins.values()
            if plugin.get('metadata', {}).get('type') == plugin_type
        ]
    
    def save_registry(self) -> None:
        """Save registry to file"""
        if self.registry_file:
            try:
                with open(self.registry_file, 'w') as f:
                    json.dump(self.plugins, f, indent=2)
                self.logger.debug(f"Saved plugin registry to {self.registry_file}")
            except Exception as e:
                self.logger.error(f"Failed to save plugin registry: {e}")
    
    def load_registry(self) -> None:
        """Load registry from file"""
        if self.registry_file and Path(self.registry_file).exists():
            try:
                with open(self.registry_file, 'r') as f:
                    self.plugins = json.load(f)
                self.logger.info(f"Loaded {len(self.plugins)} plugins from registry")
            except Exception as e:
                self.logger.error(f"Failed to load plugin registry: {e}")
                self.plugins = {}
    
    def get_plugin_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded plugins"""
        active_count = len(self.get_active_plugins())
        plugin_types = {}
        
        for plugin in self.plugins.values():
            plugin_type = plugin.get('metadata', {}).get('type', 'unknown')
            plugin_types[plugin_type] = plugin_types.get(plugin_type, 0) + 1
        
        return {
            'total_plugins': len(self.plugins),
            'active_plugins': active_count,
            'inactive_plugins': len(self.plugins) - active_count,
            'plugins_by_type': plugin_types,
            'last_update': datetime.now().isoformat()
        }