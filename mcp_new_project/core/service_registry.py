"""
Service Registration and Configuration
Central place to configure all dependency injection
"""
import logging
from typing import Optional

from core.dependency_injection import ServiceContainer, Scope
from core.interfaces import (
    IEventBus, ICacheService, IMonitoringService,
    INotificationService, IConfigurationService
)
from core.base_implementations import (
    InMemoryEventBus, InMemoryCacheService, InMemoryMonitoringService
)

# Import existing services
from services.mcp_manager import EnhancedMCPManager as MCPManager
from services.multi_agent_service import MultiAgentTaskService
from services.repository_service import RepositoryService
from services.api_client import OpenRouterClient
from services.config_manager import ConfigManager
from services.error_handler import ErrorHandler
from services.workflow_engine import WorkflowTemplateEngine
from services.supermemory_service import SupermemoryService
from services.zen_mcp_service import ZenMCPService
from services.email_service import EmailService
from services.database_task_storage import DatabaseTaskStorage
from services.memory_aware_chat_service import get_memory_aware_chat_service

# Import utilities that act as services
from utils.notification_service import NotificationService
from utils.logging_config import get_logger
from utils.async_database import async_db_manager

# Import plugin system
from core.plugins import PluginLoader, PluginRegistry

# Import auditing system
from services.auditing import AgentAuditor, DatabaseAuditStorage, ExplainabilityEngine

logger = get_logger(__name__)


def configure_core_services(container: ServiceContainer) -> None:
    """Configure core infrastructure services"""
    
    # Event Bus
    container.register_singleton(IEventBus, InMemoryEventBus())
    container.register_singleton('event_bus', InMemoryEventBus())
    
    # Cache Service
    container.register_singleton(ICacheService, InMemoryCacheService())
    container.register_singleton('cache', InMemoryCacheService())
    
    # Monitoring Service
    container.register_singleton(IMonitoringService, InMemoryMonitoringService())
    container.register_singleton('monitoring', InMemoryMonitoringService())
    
    # Notification Service
    container.register_factory(
        INotificationService,
        lambda: NotificationService(),
        scope=Scope.SINGLETON
    )
    container.register_singleton('notification_service', NotificationService())
    
    # Configuration Service
    container.register_singleton(IConfigurationService, ConfigManager())
    container.register_singleton('config_manager', ConfigManager())
    
    # Logging
    container.register_factory('logger', lambda: get_logger(__name__))
    
    # Async Database Manager
    container.register_singleton('async_db_manager', async_db_manager)
    
    # WebSocket Support
    # container.register_factory('socketio', get_socketio)  # Function doesn't exist
    
    # Plugin System
    container.register_singleton('plugin_registry', PluginRegistry())
    container.register_factory(
        'plugin_loader',
        lambda: PluginLoader(),
        scope=Scope.SINGLETON
    )
    
    # Auditing System
    container.register_factory(
        'audit_storage',
        lambda: DatabaseAuditStorage(),
        scope=Scope.SINGLETON
    )
    
    container.register_factory(
        'agent_auditor',
        lambda: AgentAuditor(
            storage_backend=container.get_service('audit_storage')
        ),
        scope=Scope.SINGLETON
    )
    
    container.register_factory(
        'explainability_engine',
        lambda: ExplainabilityEngine(
            audit_storage=container.get_service('audit_storage')
        ),
        scope=Scope.SINGLETON
    )
    
    logger.info("Core services configured")


def configure_application_services(container: ServiceContainer) -> None:
    """Configure application-specific services"""
    
    # MCP Manager
    container.register_singleton('mcp_manager', MCPManager())
    
    # Memory-Aware Chat Service (requires async initialize later)
    container.register_singleton(
        'memory_aware_chat_service',
        lambda: get_memory_aware_chat_service()
    )
    # Mark for async-phase initialization
    if not hasattr(container, "_async_init_services"):
        container._async_init_services = []            # type: ignore[attr-defined]
    container._async_init_services.append('memory_aware_chat_service')  # type: ignore[attr-defined]

    # Multi-Agent Task Service
    container.register_factory(
        'multi_agent_task_service',
        lambda: MultiAgentTaskService(),
        scope=Scope.SINGLETON
    )
    
    # Repository Service
    container.register_factory(
        'repository_service',
        lambda: RepositoryService(),
        scope=Scope.SINGLETON
    )
    
    # API Clients
    container.register_factory(
        'api_client',
        lambda: OpenRouterClient(),
        scope=Scope.SINGLETON
    )
    container.register_factory(
        'openrouter_client',
        lambda: OpenRouterClient(),
        scope=Scope.SINGLETON
    )
    
    # Error Handler
    container.register_singleton('error_handler', ErrorHandler())
    
    # Workflow Engine
    container.register_factory(
        'workflow_engine',
        lambda: WorkflowTemplateEngine(),
        scope=Scope.SINGLETON
    )
    
    # Task Storage
    container.register_factory(
        'task_storage',
        lambda: DatabaseTaskStorage(),
        scope=Scope.SINGLETON
    )
    
    # Task Dispatcher
    # Task Dispatcher - Commented out due to circular import
    # container.register_factory(
    #     'task_dispatcher',
    #     lambda: TaskDispatcher(),
    #     scope=Scope.SINGLETON
    # )
    
    # Email Service
    container.register_factory(
        'email_service',
        lambda: EmailService(),
        scope=Scope.SINGLETON
    )
    
    # Email Agent - No EmailAgent class, using blueprint directly
    # container.register_factory(
    #     'email_agent',
    #     lambda: EmailAgent(),
    #     scope=Scope.SINGLETON
    # )
    
    # External Service Integrations
    container.register_factory(
        'supermemory_service',
        lambda: SupermemoryService(),
        scope=Scope.SINGLETON
    )
    
    container.register_factory(
        'zen_service',
        lambda: ZenMCPService(),
        scope=Scope.SINGLETON
    )
    
    logger.info("Application services configured")


def configure_request_scoped_services(container: ServiceContainer) -> None:
    """Configure services that should be created per request"""
    
    # Add any request-scoped services here
    # Example:
    # container.register('request_context', RequestContext, scope=Scope.SCOPED)
    
    pass


def configure_all_services(container: ServiceContainer) -> None:
    """Configure all services in the application"""
    
    # Configure in order of dependencies
    configure_core_services(container)
    configure_application_services(container)
    configure_request_scoped_services(container)
    
    logger.info("All services configured successfully")


# Auto-wire common dependencies
def configure_auto_wiring(container: ServiceContainer) -> None:
    """Configure automatic dependency injection patterns"""
    
    # Register common interfaces to implementations
    container.register('logger', lambda: get_logger(__name__), scope=Scope.TRANSIENT)
    
    # Register factory patterns for services that need context
    def create_logger_for_class(class_name: str):
        return get_logger(class_name)
    
    container.register('logger_factory', create_logger_for_class)


# Singleton instance management
_initialized = False


def initialize_services() -> ServiceContainer:
    """Initialize and return the configured service container"""
    global _initialized
    
    from core.dependency_injection import get_container
    container = get_container()
    
    if not _initialized:
        configure_all_services(container)
        configure_auto_wiring(container)
        _initialized = True
        logger.info("Service container initialized")
    
    return container


# Convenience function for getting services
def get_service(service_name: str):
    """Get a service from the container"""
    container = initialize_services()
    return container.get_service(service_name)


def get_required_service(service_name: str):
    """Get a required service from the container"""
    container = initialize_services()
    return container.get_required_service(service_name)