"""
Enhanced Dependency Injection Container with Support for Factories, Singletons, and Scopes
"""
from typing import Dict, Any, Optional, Callable, Type, Union, Tuple, List
from functools import wraps
import inspect
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Scope(Enum):
    """Service lifetime scopes"""
    SINGLETON = "singleton"  # One instance for the entire application
    TRANSIENT = "transient"  # New instance every time
    SCOPED = "scoped"       # One instance per request/scope
    THREAD = "thread"       # One instance per thread


@dataclass
class ServiceDescriptor:
    """Describes a registered service"""
    service_type: Type
    implementation: Optional[Union[Type, Callable, Any]] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    scope: Scope = Scope.TRANSIENT
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class IServiceProvider(ABC):
    """Interface for service providers"""
    
    @abstractmethod
    def get_service(self, service_type: Union[str, Type]) -> Optional[Any]:
        """Get a service instance"""
        pass
    
    @abstractmethod
    def get_required_service(self, service_type: Union[str, Type]) -> Any:
        """Get a service instance, raise if not found"""
        pass


class ServiceContainer(IServiceProvider):
    """
    Advanced dependency injection container with support for:
    - Multiple scopes (singleton, transient, scoped, thread-local)
    - Factory functions
    - Auto-wiring dependencies
    - Service lifetime management
    - Circular dependency detection
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}
        self._singletons: Dict[str, Any] = {}
        self._thread_locals = threading.local()
        self._scoped_instances: Dict[str, Dict[str, Any]] = {}
        self._current_scope_id: Optional[str] = None
        self._resolution_stack: List[str] = []
        self._lock = threading.RLock()
        
    def register(
        self,
        service_type: Union[str, Type],
        implementation: Optional[Union[Type, Callable, Any]] = None,
        factory: Optional[Callable] = None,
        scope: Union[Scope, str] = Scope.TRANSIENT,
        singleton: bool = False,  # Backward compatibility
        dependencies: Optional[List[str]] = None
    ) -> 'ServiceContainer':
        """
        Register a service with the container.
        
        Args:
            service_type: Service identifier (string or type)
            implementation: Service implementation (class, instance, or None if using factory)
            factory: Factory function to create instances
            scope: Service lifetime scope
            singleton: Legacy parameter for backward compatibility
            dependencies: Explicit dependencies (auto-detected if not provided)
            
        Returns:
            Self for chaining
        """
        # Handle legacy singleton parameter
        if singleton:
            scope = Scope.SINGLETON
            
        # Convert string scope to enum
        if isinstance(scope, str):
            scope = Scope(scope)
            
        # Get service key
        service_key = self._get_service_key(service_type)
        
        # Create descriptor
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation,
            factory=factory,
            scope=scope,
            dependencies=dependencies or []
        )
        
        # If it's already an instance and marked as singleton, store it
        if implementation and not inspect.isclass(implementation) and not callable(implementation):
            if scope == Scope.SINGLETON:
                descriptor.instance = implementation
                self._singletons[service_key] = implementation
        
        # Auto-detect dependencies if not provided
        if not dependencies and (implementation or factory):
            target = factory or implementation
            if callable(target) and not isinstance(target, type):
                # It's a function/factory
                descriptor.dependencies = self._extract_dependencies(target)
            elif inspect.isclass(target):
                # It's a class, check __init__
                descriptor.dependencies = self._extract_dependencies(target.__init__)
        
        # Register the service
        with self._lock:
            self._services[service_key] = descriptor
            logger.debug(f"Registered service: {service_key} with scope: {scope.value}")
            
        return self
    
    def register_factory(
        self,
        service_type: Union[str, Type],
        factory: Callable,
        scope: Union[Scope, str] = Scope.TRANSIENT
    ) -> 'ServiceContainer':
        """Register a factory function for creating service instances"""
        return self.register(service_type, factory=factory, scope=scope)
    
    def register_singleton(
        self,
        service_type: Union[str, Type],
        implementation: Union[Type, Any]
    ) -> 'ServiceContainer':
        """Register a singleton service"""
        return self.register(service_type, implementation, scope=Scope.SINGLETON)
    
    def get_service(self, service_type: Union[str, Type]) -> Optional[Any]:
        """Get a service instance, returns None if not found"""
        try:
            return self._resolve_service(service_type)
        except Exception as e:
            logger.warning(f"Failed to resolve service {service_type}: {e}")
            return None
    
    def get_required_service(self, service_type: Union[str, Type]) -> Any:
        """Get a service instance, raises exception if not found"""
        service = self._resolve_service(service_type)
        if service is None:
            raise ValueError(f"Required service '{service_type}' not found")
        return service
    
    def get_services(self, service_type: Union[str, Type]) -> List[Any]:
        """Get all services of a given type"""
        # This could be extended to support multiple registrations
        service = self.get_service(service_type)
        return [service] if service else []
    
    @contextmanager
    def create_scope(self, scope_id: Optional[str] = None):
        """Create a new service scope"""
        import uuid
        
        if scope_id is None:
            scope_id = str(uuid.uuid4())
            
        previous_scope = self._current_scope_id
        self._current_scope_id = scope_id
        self._scoped_instances[scope_id] = {}
        
        try:
            yield self
        finally:
            # Clean up scoped instances
            if scope_id in self._scoped_instances:
                del self._scoped_instances[scope_id]
            self._current_scope_id = previous_scope
    
    def _resolve_service(self, service_type: Union[str, Type]) -> Optional[Any]:
        """Resolve a service with dependency injection"""
        service_key = self._get_service_key(service_type)
        
        # Check for circular dependencies
        if service_key in self._resolution_stack:
            raise RuntimeError(f"Circular dependency detected: {' -> '.join(self._resolution_stack)} -> {service_key}")
        
        # Get service descriptor
        descriptor = self._services.get(service_key)
        if not descriptor:
            return None
        
        # Add to resolution stack
        self._resolution_stack.append(service_key)
        
        try:
            # Check scope and return existing instance if applicable
            instance = self._get_existing_instance(service_key, descriptor)
            if instance is not None:
                return instance
            
            # Create new instance
            instance = self._create_instance(descriptor)
            
            # Store instance based on scope
            self._store_instance(service_key, descriptor, instance)
            
            return instance
            
        finally:
            # Remove from resolution stack
            self._resolution_stack.pop()
    
    def _get_existing_instance(self, service_key: str, descriptor: ServiceDescriptor) -> Optional[Any]:
        """Get existing instance based on scope"""
        if descriptor.scope == Scope.SINGLETON:
            return self._singletons.get(service_key)
            
        elif descriptor.scope == Scope.SCOPED and self._current_scope_id:
            scoped_instances = self._scoped_instances.get(self._current_scope_id, {})
            return scoped_instances.get(service_key)
            
        elif descriptor.scope == Scope.THREAD:
            if not hasattr(self._thread_locals, 'instances'):
                self._thread_locals.instances = {}
            return self._thread_locals.instances.get(service_key)
            
        return None
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new instance of a service"""
        # If we have a pre-created instance, return it
        if descriptor.instance is not None:
            return descriptor.instance
            
        # Resolve dependencies
        dependencies = {}
        for dep in descriptor.dependencies:
            dep_instance = self._resolve_service(dep)
            if dep_instance is None:
                raise ValueError(f"Unable to resolve dependency '{dep}'")
            dependencies[dep] = dep_instance
        
        # Create instance using factory or constructor
        if descriptor.factory:
            # Use factory function
            return self._invoke_with_dependencies(descriptor.factory, dependencies)
            
        elif descriptor.implementation:
            if inspect.isclass(descriptor.implementation):
                # Instantiate class
                return self._invoke_with_dependencies(descriptor.implementation, dependencies)
            else:
                # Return the implementation directly (it's already an instance)
                return descriptor.implementation
                
        else:
            raise ValueError(f"No implementation or factory provided for service")
    
    def _store_instance(self, service_key: str, descriptor: ServiceDescriptor, instance: Any):
        """Store instance based on scope"""
        if descriptor.scope == Scope.SINGLETON:
            with self._lock:
                self._singletons[service_key] = instance
                
        elif descriptor.scope == Scope.SCOPED and self._current_scope_id:
            self._scoped_instances[self._current_scope_id][service_key] = instance
            
        elif descriptor.scope == Scope.THREAD:
            if not hasattr(self._thread_locals, 'instances'):
                self._thread_locals.instances = {}
            self._thread_locals.instances[service_key] = instance
    
    def _invoke_with_dependencies(self, target: Callable, dependencies: Dict[str, Any]) -> Any:
        """Invoke a callable with resolved dependencies"""
        sig = inspect.signature(target)
        kwargs = {}
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Try to get dependency by parameter name
            if param_name in dependencies:
                kwargs[param_name] = dependencies[param_name]
            # Try to get by type annotation
            elif param.annotation != inspect.Parameter.empty:
                service_key = self._get_service_key(param.annotation)
                if service_key in self._services:
                    kwargs[param_name] = self._resolve_service(service_key)
                    
        return target(**kwargs)
    
    def _extract_dependencies(self, target: Callable) -> List[str]:
        """Extract dependencies from a callable's signature"""
        if not callable(target):
            return []
            
        sig = inspect.signature(target)
        dependencies = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
                
            # Use type annotation if available
            if param.annotation != inspect.Parameter.empty:
                dep_key = self._get_service_key(param.annotation)
                dependencies.append(dep_key)
            # Otherwise use parameter name
            else:
                dependencies.append(param_name)
                
        return dependencies
    
    def _get_service_key(self, service_type: Union[str, Type]) -> str:
        """Get normalized service key"""
        if isinstance(service_type, str):
            return service_type
        elif inspect.isclass(service_type):
            return f"{service_type.__module__}.{service_type.__name__}"
        else:
            return str(service_type)
    
    def clear(self):
        """Clear all registrations and instances"""
        with self._lock:
            self._services.clear()
            self._singletons.clear()
            self._scoped_instances.clear()
            if hasattr(self._thread_locals, 'instances'):
                self._thread_locals.instances.clear()


# Global container instance
_container = ServiceContainer()


def get_container() -> ServiceContainer:
    """Get the global service container"""
    return _container


def configure_services(configuration_func: Callable[[ServiceContainer], None]):
    """Configure services using a configuration function"""
    configuration_func(_container)


# Decorator for dependency injection
def inject(*dependencies: Union[str, Type]):
    """
    Decorator to inject dependencies into a function or method
    
    Usage:
        @inject('database', 'logger')
        def my_function(database, logger):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            container = get_container()
            
            # Resolve dependencies
            for dep in dependencies:
                if isinstance(dep, str):
                    service = container.get_required_service(dep)
                    kwargs[dep] = service
                    
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions for backward compatibility
def get_service(service_type: Union[str, Type]) -> Optional[Any]:
    """Get a service from the global container"""
    return _container.get_service(service_type)


def get_required_service(service_type: Union[str, Type]) -> Any:
    """Get a required service from the global container"""
    return _container.get_required_service(service_type)