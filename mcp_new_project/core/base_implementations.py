"""
Base implementations for common service patterns
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime
from collections import defaultdict
import weakref

from .interfaces import (
    IService, IEventBus, Event, EventHandler,
    ICacheService, IMonitoringService, Metric
)

logger = logging.getLogger(__name__)


class BaseService(IService):
    """Base implementation for services with lifecycle management"""
    
    def __init__(self):
        self._initialized = False
        self._shutdown = False
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the service"""
        async with self._lock:
            if self._initialized:
                return
                
            await self._do_initialize()
            self._initialized = True
            logger.info(f"{self.__class__.__name__} initialized")
    
    async def shutdown(self) -> None:
        """Cleanup and shutdown the service"""
        async with self._lock:
            if self._shutdown:
                return
                
            await self._do_shutdown()
            self._shutdown = True
            logger.info(f"{self.__class__.__name__} shutdown")
    
    async def _do_initialize(self) -> None:
        """Override this method to implement initialization logic"""
        pass
    
    async def _do_shutdown(self) -> None:
        """Override this method to implement shutdown logic"""
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized"""
        return self._initialized
    
    @property
    def is_shutdown(self) -> bool:
        """Check if service is shutdown"""
        return self._shutdown


class InMemoryEventBus(BaseService, IEventBus):
    """In-memory implementation of event bus"""
    
    def __init__(self):
        super().__init__()
        self._handlers: Dict[str, Set[EventHandler]] = defaultdict(set)
        self._weak_handlers: Dict[str, Set[weakref.ref]] = defaultdict(set)
        
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to an event type"""
        self._handlers[event_type].add(handler)
        
    def subscribe_weak(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe with weak reference (auto-cleanup when handler is garbage collected)"""
        weak_ref = weakref.ref(handler, lambda ref: self._cleanup_weak_handler(event_type, ref))
        self._weak_handlers[event_type].add(weak_ref)
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from an event type"""
        self._handlers[event_type].discard(handler)
        
        # Also check weak handlers
        to_remove = []
        for weak_ref in self._weak_handlers[event_type]:
            if weak_ref() == handler:
                to_remove.append(weak_ref)
        
        for ref in to_remove:
            self._weak_handlers[event_type].discard(ref)
    
    async def publish(self, event: Event) -> None:
        """Publish an event"""
        handlers = list(self._handlers.get(event.event_type, []))
        
        # Add weak handlers that are still alive
        for weak_ref in self._weak_handlers.get(event.event_type, []):
            handler = weak_ref()
            if handler:
                handlers.append(handler)
        
        # Also check for wildcard handlers
        handlers.extend(self._handlers.get("*", []))
        
        # Execute handlers
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(event))
            else:
                # Run sync handlers in executor
                loop = asyncio.get_event_loop()
                tasks.append(loop.run_in_executor(None, handler, event))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in event handler for {event.event_type}: {result}")
    
    def _cleanup_weak_handler(self, event_type: str, ref: weakref.ref) -> None:
        """Clean up dead weak references"""
        self._weak_handlers[event_type].discard(ref)


class InMemoryCacheService(BaseService, ICacheService):
    """Simple in-memory cache implementation"""
    
    def __init__(self):
        super().__init__()
        self._cache: Dict[str, tuple[Any, Optional[datetime]]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def _do_initialize(self) -> None:
        """Start cleanup task"""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        
    async def _do_shutdown(self) -> None:
        """Stop cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key not in self._cache:
            return None
            
        value, expires_at = self._cache[key]
        
        # Check if expired
        if expires_at and datetime.utcnow() > expires_at:
            del self._cache[key]
            return None
            
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL in seconds"""
        expires_at = None
        if ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
        self._cache[key] = (value, expires_at)
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    async def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    async def _cleanup_expired(self) -> None:
        """Periodically clean up expired entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                now = datetime.utcnow()
                expired_keys = [
                    key for key, (_, expires_at) in self._cache.items()
                    if expires_at and now > expires_at
                ]
                
                for key in expired_keys:
                    del self._cache[key]
                    
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")


class InMemoryMonitoringService(BaseService, IMonitoringService):
    """Simple in-memory monitoring service"""
    
    def __init__(self, max_metrics_per_name: int = 10000):
        super().__init__()
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)
        self._events: List[Dict[str, Any]] = []
        self._max_metrics_per_name = max_metrics_per_name
        
    async def record_metric(self, metric: Metric) -> None:
        """Record a metric"""
        metrics_list = self._metrics[metric.name]
        metrics_list.append(metric)
        
        # Limit memory usage by keeping only recent metrics
        if len(metrics_list) > self._max_metrics_per_name:
            # Keep the most recent metrics
            self._metrics[metric.name] = metrics_list[-self._max_metrics_per_name:]
    
    async def get_metrics(self, name: str, start_time: datetime, end_time: datetime) -> List[Metric]:
        """Get metrics for a time range"""
        metrics = self._metrics.get(name, [])
        
        # Filter by time range
        filtered = [
            m for m in metrics
            if start_time <= m.timestamp <= end_time
        ]
        
        return filtered
    
    async def record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Record an event"""
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow()
        }
        
        self._events.append(event)
        
        # Limit memory usage
        if len(self._events) > 10000:
            self._events = self._events[-10000:]


class ServiceLifecycleManager:
    """Manages lifecycle of multiple services"""
    
    def __init__(self):
        self._services: List[IService] = []
        
    def add_service(self, service: IService) -> None:
        """Add a service to be managed"""
        self._services.append(service)
        
    async def initialize_all(self) -> None:
        """Initialize all services"""
        tasks = [service.initialize() for service in self._services]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for initialization errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_name = self._services[i].__class__.__name__
                logger.error(f"Failed to initialize {service_name}: {result}")
                raise RuntimeError(f"Service initialization failed: {service_name}")
    
    async def shutdown_all(self) -> None:
        """Shutdown all services in reverse order"""
        # Shutdown in reverse order of initialization
        for service in reversed(self._services):
            try:
                await service.shutdown()
            except Exception as e:
                service_name = service.__class__.__name__
                logger.error(f"Error shutting down {service_name}: {e}")


from datetime import timedelta


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise RuntimeError("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _on_success(self) -> None:
        """Handle successful call"""
        self.failure_count = 0
        self.state = "closed"
        
    def _on_failure(self) -> None:
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")