"""
Simplified Dependency Injection Container
Focuses on core functionality with better performance
"""
from typing import Dict, Any, Optional, Callable, Type, Union
from enum import Enum
import threading
import logging

logger = logging.getLogger(__name__)


class Scope(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"


class SimpleDI:
    """
    Simplified dependency injection container
    - Focuses on singleton and transient scopes (covers 99% of use cases)
    - Removes complex auto-wiring
    - Better error messages
    - Thread-safe singleton management
    """
    
    def __init__(self):
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._scopes: Dict[str, Scope] = {}
        self._lock = threading.RLock()
    
    def register(
        self,
        service_id: str,
        factory: Union[Callable, Any],
        scope: Scope = Scope.TRANSIENT
    ) -> 'SimpleDI':
        """
        Register a service
        
        Args:
            service_id: Service identifier
            factory: Factory function or instance
            scope: Service lifetime scope
        """
        with self._lock:
            if callable(factory):
                self._factories[service_id] = factory
            else:
                # It's already an instance, store as singleton
                self._singletons[service_id] = factory
                scope = Scope.SINGLETON
            
            self._scopes[service_id] = scope
            logger.debug(f"Registered {service_id} as {scope.value}")
        
        return self
    
    def register_singleton(self, service_id: str, factory: Union[Callable, Any]) -> 'SimpleDI':
        """Register a singleton service"""
        return self.register(service_id, factory, Scope.SINGLETON)
    
    def register_factory(self, service_id: str, factory: Callable) -> 'SimpleDI':
        """Register a transient factory"""
        return self.register(service_id, factory, Scope.TRANSIENT)
    
    def get(self, service_id: str) -> Optional[Any]:
        """Get a service instance"""
        with self._lock:
            # Check if it's already a singleton
            if service_id in self._singletons:
                return self._singletons[service_id]
            
            # Check if we have a factory
            factory = self._factories.get(service_id)
            if not factory:
                return None
            
            # Create instance
            try:
                instance = factory()
                
                # Store if singleton
                if self._scopes.get(service_id) == Scope.SINGLETON:
                    self._singletons[service_id] = instance
                
                return instance
                
            except Exception as e:
                logger.error(f"Failed to create {service_id}: {e}")
                raise
    
    def get_required(self, service_id: str) -> Any:
        """Get a required service (raises if not found)"""
        service = self.get(service_id)
        if service is None:
            raise ValueError(f"Required service '{service_id}' not registered")
        return service
    
    def has(self, service_id: str) -> bool:
        """Check if a service is registered"""
        return service_id in self._factories or service_id in self._singletons
    
    def clear(self):
        """Clear all registrations"""
        with self._lock:
            self._factories.clear()
            self._singletons.clear()
            self._scopes.clear()


# Global container instance
_container = SimpleDI()


def get_container() -> SimpleDI:
    """Get the global container"""
    return _container


def register(service_id: str, factory: Union[Callable, Any], scope: Scope = Scope.TRANSIENT):
    """Register a service in the global container"""
    _container.register(service_id, factory, scope)


def register_singleton(service_id: str, factory: Union[Callable, Any]):
    """Register a singleton in the global container"""
    _container.register_singleton(service_id, factory)


def get_service(service_id: str) -> Optional[Any]:
    """Get a service from the global container"""
    return _container.get(service_id)


def get_required_service(service_id: str) -> Any:
    """Get a required service from the global container"""
    return _container.get_required(service_id)