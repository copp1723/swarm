"""
Optimized Service Registration and Configuration
Reduces duplication and improves maintainability
"""
import logging
from typing import Dict, Type, Callable, Any, List, Optional
from dataclasses import dataclass

from core.dependency_injection import ServiceContainer, Scope
from core.interfaces import (
    IEventBus, ICacheService, IMonitoringService,
    INotificationService, IConfigurationService
)
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceDefinition:
    """Defines a service registration"""
    name: str
    factory: Callable
    scope: Scope = Scope.SINGLETON
    interfaces: List[Type] = None
    depends_on: List[str] = None
    
    def __post_init__(self):
        if self.interfaces is None:
            self.interfaces = []
        if self.depends_on is None:
            self.depends_on = []


class ServiceRegistry:
    """Optimized service registry with automatic dependency validation"""
    
    def __init__(self):
        self._definitions: Dict[str, ServiceDefinition] = {}
        self._initialized = False
    
    def define_core_services(self) -> Dict[str, ServiceDefinition]:
        """Define all core infrastructure services"""
        from core.base_implementations import (
            InMemoryEventBus, InMemoryCacheService, InMemoryMonitoringService
        )
        from utils.notification_service import NotificationService
        from services.config_manager import ConfigManager
        from utils.async_database import async_db_manager
        
        return {
            'event_bus': ServiceDefinition(
                name='event_bus',
                factory=InMemoryEventBus,
                interfaces=[IEventBus]
            ),
            'cache': ServiceDefinition(
                name='cache',
                factory=InMemoryCacheService,
                interfaces=[ICacheService]
            ),
            'monitoring': ServiceDefinition(
                name='monitoring',
                factory=InMemoryMonitoringService,
                interfaces=[IMonitoringService]
            ),
            'notification_service': ServiceDefinition(
                name='notification_service',
                factory=NotificationService,
                interfaces=[INotificationService]
            ),
            'config_manager': ServiceDefinition(
                name='config_manager',
                factory=ConfigManager,
                interfaces=[IConfigurationService]
            ),
            'async_db_manager': ServiceDefinition(
                name='async_db_manager',
                factory=lambda: async_db_manager,
                scope=Scope.SINGLETON
            ),
        }
    
    def define_plugin_services(self) -> Dict[str, ServiceDefinition]:
        """Define plugin system services"""
        from core.plugins import PluginLoader, PluginRegistry
        
        return {
            'plugin_registry': ServiceDefinition(
                name='plugin_registry',
                factory=PluginRegistry
            ),
            'plugin_loader': ServiceDefinition(
                name='plugin_loader',
                factory=PluginLoader
            ),
        }
    
    def define_audit_services(self) -> Dict[str, ServiceDefinition]:
        """Define auditing system services"""
        from services.auditing import AgentAuditor, DatabaseAuditStorage, ExplainabilityEngine
        
        return {
            'audit_storage': ServiceDefinition(
                name='audit_storage',
                factory=DatabaseAuditStorage
            ),
            'agent_auditor': ServiceDefinition(
                name='agent_auditor',
                factory=lambda container: AgentAuditor(
                    storage_backend=container.get_service('audit_storage')
                ),
                depends_on=['audit_storage']
            ),
            'explainability_engine': ServiceDefinition(
                name='explainability_engine',
                factory=lambda container: ExplainabilityEngine(
                    audit_storage=container.get_service('audit_storage')
                ),
                depends_on=['audit_storage']
            ),
        }
    
    def define_application_services(self) -> Dict[str, ServiceDefinition]:
        """Define application-specific services"""
        from services.mcp_manager import EnhancedMCPManager as MCPManager
        from services.multi_agent_service import MultiAgentTaskService
        from services.repository_service import RepositoryService
        from services.api_client import OpenRouterClient
        from services.error_handler import ErrorHandler
        from services.workflow_engine import WorkflowTemplateEngine
        from services.database_task_storage import DatabaseTaskStorage
        from services.email_service import EmailService
        from services.supermemory_service import SupermemoryService
        from services.zen_mcp_service import ZenMCPService
        
        return {
            'mcp_manager': ServiceDefinition(
                name='mcp_manager',
                factory=MCPManager
            ),
            'multi_agent_task_service': ServiceDefinition(
                name='multi_agent_task_service',
                factory=MultiAgentTaskService
            ),
            'repository_service': ServiceDefinition(
                name='repository_service',
                factory=RepositoryService
            ),
            'api_client': ServiceDefinition(
                name='api_client',
                factory=OpenRouterClient
            ),
            'error_handler': ServiceDefinition(
                name='error_handler',
                factory=ErrorHandler
            ),
            'workflow_engine': ServiceDefinition(
                name='workflow_engine',
                factory=WorkflowTemplateEngine
            ),
            'task_storage': ServiceDefinition(
                name='task_storage',
                factory=DatabaseTaskStorage
            ),
            'email_service': ServiceDefinition(
                name='email_service',
                factory=EmailService
            ),
            'supermemory_service': ServiceDefinition(
                name='supermemory_service',
                factory=SupermemoryService
            ),
            'zen_service': ServiceDefinition(
                name='zen_service',
                factory=ZenMCPService
            ),
        }
    
    def register_all_services(self, container: ServiceContainer) -> None:
        """Register all services with dependency validation"""
        # Collect all definitions
        all_definitions = {
            **self.define_core_services(),
            **self.define_plugin_services(),
            **self.define_audit_services(),
            **self.define_application_services(),
        }
        
        # Validate dependencies
        self._validate_dependencies(all_definitions)
        
        # Register in dependency order
        registered = set()
        
        def register_service(name: str, definition: ServiceDefinition):
            if name in registered:
                return
            
            # Register dependencies first
            for dep in definition.depends_on:
                if dep in all_definitions and dep not in registered:
                    register_service(dep, all_definitions[dep])
            
            # Register the service
            if callable(definition.factory) and definition.factory.__name__ == '<lambda>':
                # Lambda factory that needs container
                container.register_factory(
                    name,
                    lambda: definition.factory(container),
                    scope=definition.scope
                )
            else:
                container.register(
                    name,
                    definition.factory,
                    scope=definition.scope
                )
            
            # Register interfaces
            for interface in definition.interfaces:
                container.register(interface, definition.factory, scope=definition.scope)
            
            registered.add(name)
            logger.debug(f"Registered service: {name}")
        
        # Register all services
        for name, definition in all_definitions.items():
            register_service(name, definition)
        
        logger.info(f"Registered {len(registered)} services")
    
    def _validate_dependencies(self, definitions: Dict[str, ServiceDefinition]) -> None:
        """Validate that all dependencies exist"""
        all_names = set(definitions.keys())
        
        for name, definition in definitions.items():
            for dep in definition.depends_on:
                if dep not in all_names:
                    raise ValueError(f"Service '{name}' depends on undefined service '{dep}'")


# Optimized initialization function
_registry = ServiceRegistry()


def initialize_services() -> ServiceContainer:
    """Initialize and return the configured service container"""
    from core.dependency_injection import get_container
    
    container = get_container()
    
    if not _registry._initialized:
        _registry.register_all_services(container)
        _registry._initialized = True
        logger.info("Service container initialized with optimized registry")
    
    return container


def get_service(service_name: str) -> Any:
    """Get a service from the container"""
    container = initialize_services()
    return container.get_service(service_name)


def get_required_service(service_name: str) -> Any:
    """Get a required service from the container"""
    container = initialize_services()
    return container.get_required_service(service_name)