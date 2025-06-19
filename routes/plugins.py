"""
Plugin Management API Routes
"""
from flask import Blueprint, jsonify, request
import os
from typing import Dict, Any

from core.service_registry import get_service
from utils.logging_config import get_logger
from utils.auth import require_auth

logger = get_logger(__name__)

plugins_bp = Blueprint('plugins', __name__, url_prefix='/api/plugins')


@plugins_bp.route('/', methods=['GET'])
@require_auth
def list_plugins():
    """List all loaded plugins"""
    try:
        plugin_loader = get_service('plugin_loader')
        if not plugin_loader:
            return jsonify({"error": "Plugin system not initialized"}), 503
        
        plugins = plugin_loader.get_loaded_plugins()
        
        return jsonify({
            "plugins": plugins,
            "plugin_count": len(plugins),
            "directories": plugin_loader.plugin_directories
        })
        
    except Exception as e:
        logger.error(f"Error listing plugins: {e}")
        return jsonify({"error": str(e)}), 500


@plugins_bp.route('/directory', methods=['POST'])
@require_auth
def add_plugin_directory():
    """Add a new plugin directory to watch"""
    try:
        data = request.get_json()
        directory = data.get('directory')
        
        if not directory:
            return jsonify({"error": "Directory path required"}), 400
        
        plugin_loader = get_service('plugin_loader')
        if not plugin_loader:
            return jsonify({"error": "Plugin system not initialized"}), 503
        
        # Validate directory exists
        if not os.path.exists(directory):
            return jsonify({"error": f"Directory does not exist: {directory}"}), 400
        
        plugin_loader.add_plugin_directory(directory)
        
        return jsonify({
            "message": f"Plugin directory added: {directory}",
            "directories": plugin_loader.plugin_directories
        })
        
    except Exception as e:
        logger.error(f"Error adding plugin directory: {e}")
        return jsonify({"error": str(e)}), 500


@plugins_bp.route('/registry', methods=['GET'])
@require_auth
def get_plugin_registry():
    """Get plugin registry statistics"""
    try:
        plugin_registry = get_service('plugin_registry')
        if not plugin_registry:
            return jsonify({"error": "Plugin registry not initialized"}), 503
        
        stats = plugin_registry.get_plugin_statistics()
        active_plugins = plugin_registry.get_active_plugins()
        
        return jsonify({
            "statistics": stats,
            "active_plugins": active_plugins
        })
        
    except Exception as e:
        logger.error(f"Error getting plugin registry: {e}")
        return jsonify({"error": str(e)}), 500


@plugins_bp.route('/<plugin_id>/reload', methods=['POST'])
@require_auth
def reload_plugin(plugin_id: str):
    """Reload a specific plugin"""
    try:
        plugin_loader = get_service('plugin_loader')
        if not plugin_loader:
            return jsonify({"error": "Plugin system not initialized"}), 503
        
        # Get plugin metadata to find the file
        if plugin_id in plugin_loader.plugin_metadata:
            file_path = plugin_loader.plugin_metadata[plugin_id]['file_path']
            
            # Reload the plugin
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            plugin = loop.run_until_complete(
                plugin_loader.reload_plugin_from_file(file_path)
            )
            
            if plugin:
                return jsonify({
                    "message": f"Plugin {plugin_id} reloaded successfully",
                    "plugin_info": plugin.get_plugin_info()
                })
            else:
                return jsonify({"error": "Failed to reload plugin"}), 500
        else:
            return jsonify({"error": f"Plugin {plugin_id} not found"}), 404
            
    except Exception as e:
        logger.error(f"Error reloading plugin {plugin_id}: {e}")
        return jsonify({"error": str(e)}), 500