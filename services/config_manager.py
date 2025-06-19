import os
import platform
import logging
from typing import Dict, Any
from utils.file_io import safe_read_json, safe_write_json

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages loading, validation, and platform-specific configuration for MCP servers."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), '..', 'config', 'mcp_config.json')
        self.config = {}
        self.prefs_path = os.path.join(os.path.dirname(self.config_path), 'mcp_preferences.json')
        
    def load_config(self) -> bool:
        """Load MCP configuration with environment variable substitution."""
        try:
            if os.path.exists(self.config_path):
                raw_config = safe_read_json(self.config_path, default_value={})
                if not raw_config:
                    logger.warning("Empty or invalid config file, using defaults")
                    raw_config = self._create_default_config()
                
                # Substitute environment variables
                self.config = self._substitute_env_vars(raw_config)
                self._apply_platform_fixes()
                self._load_user_preferences()
                return True
            else:
                self.config = self._create_default_config()
                if safe_write_json(self.config_path, self.config):
                    logger.info(f"Created default MCP config at {self.config_path}")
                else:
                    logger.error(f"Failed to write default config to {self.config_path}")
                return True
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return False
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in configuration values."""
        def replace_env(value):
            if isinstance(value, str):
                for key, val in os.environ.items():
                    placeholder = f"${key}"
                    if placeholder in value:
                        value = value.replace(placeholder, val)
                return value
            elif isinstance(value, dict):
                return {k: replace_env(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [replace_env(item) for item in value]
            return value
        
        return replace_env(config)
    
    def _apply_platform_fixes(self):
        """Apply platform-specific fixes to configuration."""
        system = platform.system().lower()
        if "mcpServers" not in self.config:
            return
            
        for server_name, server_config in self.config["mcpServers"].items():
            if server_name == "docker":
                if system == "windows" and server_config.get("env", {}).get("DOCKER_HOST", "").startswith("unix://"):
                    server_config["env"]["DOCKER_HOST"] = "npipe:////./pipe/docker_engine"
                    logger.info("Updated Docker configuration for Windows")
                elif system != "windows" and server_config.get("env", {}).get("DOCKER_HOST", "").startswith("npipe://"):
                    server_config["env"]["DOCKER_HOST"] = "unix:///var/run/docker.sock"
                    logger.info("Updated Docker configuration for Unix-like system")
    
    def _load_user_preferences(self):
        """Load and apply user preferences to configuration."""
        try:
            if os.path.exists(self.prefs_path):
                preferences = safe_read_json(self.prefs_path, default_value={})
                if preferences and 'userPreferences' in preferences and preferences['userPreferences'].get('autoConfirm', False):
                    for server_name in self.config.get('mcpServers', {}):
                        if 'env' not in self.config['mcpServers'][server_name]:
                            self.config['mcpServers'][server_name]['env'] = {}
                        self.config['mcpServers'][server_name]['env']['MCP_AUTO_CONFIRM'] = 'true'
                        self.config['mcpServers'][server_name]['env']['MCP_SKIP_CONFIRMATION'] = 'true'
                    logger.info("Loaded user preferences for MCP")
        except Exception as e:
            logger.warning(f"Failed to load user preferences: {e}")
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create a default configuration based on platform."""
        system = platform.system().lower()
        config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp" if system != "windows" else os.environ.get("TEMP", "C:\\temp")],
                    "env": {},
                    "description": "File system operations",
                    "enabled": True
                }
            }
        }
        return config
    
    def get_server_config(self, server_name: str) -> Dict[str, Any]:
        """Get configuration for a specific server."""
        return self.config.get("mcpServers", {}).get(server_name, {})