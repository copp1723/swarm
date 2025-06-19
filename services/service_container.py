"""
Service Container - Fixed implementation that properly handles service registration
"""
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

# Service storage
_services: Dict[str, Any] = {}
_initialized = False


def _lazy_initialize():
    """Initialize services on first use"""
    global _initialized
    if _initialized:
        return
        
    logger.info("Lazy initializing core services...")
    
    try:
        # Import and register core services
        from services.error_handler import error_handler
        _services['error_handler'] = error_handler
        
        # MCP Manager
        from services.mcp_manager import mcp_manager
        _services['mcp_manager'] = mcp_manager
        
        # Repository Service
        from services.repository_service import RepositoryService
        _services['repository_service'] = RepositoryService()
        
        # Workflow Engine
        from services.workflow_engine import WorkflowTemplateEngine
        _services['workflow_engine'] = WorkflowTemplateEngine()
        
        _initialized = True
        logger.info(f"Initialized {len(_services)} core services")
        
    except Exception as e:
        logger.error(f"Failed to initialize core services: {e}", exc_info=True)


class ServiceContainer:
    """Service container with lazy initialization"""
    
    def get(self, service_name: str) -> Optional[Any]:
        """Get a service, creating it if necessary"""
        # Ensure core services are initialized
        _lazy_initialize()
        
        # Check if already registered
        if service_name in _services:
            return _services[service_name]
            
        # Special handling for multi_agent_task_service
        if service_name == 'multi_agent_task_service':
            try:
                logger.info("Creating multi_agent_task_service on demand...")
                from services.multi_agent_service import MultiAgentTaskService
                service = MultiAgentTaskService()
                _services[service_name] = service
                logger.info("Successfully created multi_agent_task_service")
                return service
            except Exception as e:
                logger.error(f"Failed to create multi_agent_task_service: {e}", exc_info=True)
                return None
                
        logger.warning(f"Service '{service_name}' not found")
        return None
    
    def register(self, name: str, implementation: Any, **kwargs):
        """Register a service"""
        _services[name] = implementation
        logger.debug(f"Registered service: {name}")
        
    def get_service(self, name: str) -> Optional[Any]:
        """Alias for get() for compatibility"""
        return self.get(name)
        
    def get_required_service(self, name: str) -> Any:
        """Get a required service, raise if not found"""
        service = self.get(name)
        if service is None:
            raise RuntimeError(f"Required service '{name}' not found")
        return service


# Global instance
_container = ServiceContainer()


def get_service_container():
    """Get the global service container"""
    return _container


def get_service(service_name: str) -> Optional[Any]:
    """Get a service from the global container"""
    return _container.get(service_name)


def get_required_service(service_name: str) -> Any:
    """Get a required service from the global container"""
    return _container.get_required_service(service_name)


def register_services():
    """Register all services - for backward compatibility"""
    _lazy_initialize()


# Initialize services (backward compatibility with imports that expect them)
def initialize_services():
    """Initialize services - for imports from core modules"""
    from core.dependency_injection import get_container
    container = get_container()
    
    # Return the DI container for core modules
    return container