"""
Service Container Utility - Wrapper for backward compatibility
"""

# Re-export from the main service container for backward compatibility
from services.service_container import (
    get_service_container,
    get_service,
    get_required_service,
    register_services,
    ServiceContainer
)

__all__ = [
    'get_service_container',
    'get_service', 
    'get_required_service',
    'register_services',
    'ServiceContainer'
]