"""
Centralized Blueprint Registration
Consolidates all blueprint imports and registration
"""
from flask import Flask
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BlueprintRegistry:
    """Manages blueprint registration in a centralized way"""
    
    @staticmethod
    def get_all_blueprints() -> List[Tuple[str, str]]:
        """
        Returns list of (module_path, blueprint_name) tuples
        Lazy imports to avoid circular dependencies
        """
        return [
            # Core routes
            ('routes.chat', 'chat_bp'),
            ('routes.mcp', 'mcp_bp'),
            ('routes.files', 'files_bp'),
            ('routes.agents', 'agents_bp'),
            
            # Feature routes
            ('routes.async_demo', 'async_demo_bp'),
            ('routes.tasks', 'tasks_bp'),
            ('routes.memory', 'memory_bp'),
            ('routes.memory_api', 'memory_api_bp'),
            ('routes.workflows', 'workflows_bp'),
            
            # Utility routes
            ('routes.zen', 'zen_bp'),
            ('routes.templates', 'templates_bp'),
            ('routes.monitoring', 'monitoring_bp'),
            
            # Extension routes
            ('routes.email', 'email_api_bp'),
            ('routes.plugins', 'plugins_bp'),
            ('routes.audit', 'audit_bp'),
        ]
    
    @staticmethod
    def register_all_blueprints(app: Flask) -> None:
        """Register all blueprints with the Flask app"""
        blueprints = BlueprintRegistry.get_all_blueprints()
        
        for module_path, blueprint_name in blueprints:
            try:
                # Dynamic import
                module = __import__(module_path, fromlist=[blueprint_name])
                blueprint = getattr(module, blueprint_name)
                app.register_blueprint(blueprint)
                logger.debug(f"Registered blueprint: {blueprint_name} from {module_path}")
            except Exception as e:
                logger.error(f"Failed to register blueprint {blueprint_name}: {e}")
                # Continue with other blueprints
    
    @staticmethod
    def register_extensions(app: Flask) -> None:
        """Register Flask extensions that require special handling"""
        # Email agent registration
        try:
            from services.email_agent import register_email_agent
            register_email_agent(app)
            logger.info("Email agent registered")
        except Exception as e:
            logger.error(f"Failed to register email agent: {e}")