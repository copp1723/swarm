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
from services.mcp_manager import MCPManager
from services.multi_agent_service import MultiAgentTaskService
from services.repository_service import RepositoryService
from services.api_client import OpenRouterClient
from services.config_manager import ConfigManager
from services.error_handler import ErrorHandler
from services.workflow_engine import WorkflowTemplateEngine
from services.supermemory_service import SupermemoryService
from services.zen_mcp_service import ZenMCPService
from services.email_agent import EmailAgent
from services.task_dispatcher import TaskDispatcher
from services.database_task_storage import DatabaseTaskStorage

# Import utilities that act as services
from utils.notification_service import NotificationService
from utils.logging_config import get_logger
from utils.async_database import async_db_manager
from utils.websocket import get_socketio

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
    container.register_factory('socketio', get_socketio)
    
    logger.info("Core services configured")


def configure_application_services(container: ServiceContainer) -> None:
    """Configure application-specific services"""
    
    # MCP Manager
    container.register_singleton('mcp_manager', MCPManager())
    
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
    container.register_factory(
        'task_dispatcher',
        lambda: TaskDispatcher(),
        scope=Scope.SINGLETON
    )
    
    # Email Agent
    container.register_factory(
        'email_agent',
        lambda: EmailAgent(),
        scope=Scope.SINGLETON
    )
    
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
    """Configure automatic dependency resolution"""
    
    # Register common interfaces to their implementations
    container.register('IEventBus', lambda: container.get_service('event_bus'))
    container.register('ICacheService', lambda: container.get_service('cache'))
    container.register('IMonitoringService', lambda: container.get_service('monitoring'))
    container.register('INotificationService', lambda: container.get_service('notification_service'))
    container.register('IConfigurationService', lambda: container.get_service('config_manager'))


# Convenience function to get fully configured container
def get_configured_container() -> ServiceContainer:
    """Get a fully configured service container"""
    from core.dependency_injection import get_container
    
    container = get_container()
    configure_all_services(container)
    configure_auto_wiring(container)
    
    return container


# Initialize services on module import
def initialize_services():
    """Initialize all services"""
    container = get_configured_container()
    
    # Initialize core services that need startup
    event_bus = container.get_service('event_bus')
    cache = container.get_service('cache')
    monitoring = container.get_service('monitoring')
    
    # Start async initialization if needed
    import asyncio
    
    async def init_async_services():
        if hasattr(event_bus, 'initialize'):
            await event_bus.initialize()
        if hasattr(cache, 'initialize'):
            await cache.initialize()
        if hasattr(monitoring, 'initialize'):
            await monitoring.initialize()
    
    # Run initialization if we're in an async context
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(init_async_services())
    except RuntimeError:
        # No event loop running, skip async initialization
        pass