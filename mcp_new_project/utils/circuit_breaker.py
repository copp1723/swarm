"""Circuit Breaker pattern implementation for resilient service calls"""
import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, Optional, Dict
from functools import wraps
import logging
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures exceeded threshold, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures
    
    The circuit breaker can be in one of three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected immediately
    - HALF_OPEN: Testing phase to see if the service has recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: Optional[str] = None
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch (others pass through)
            name: Optional name for logging
        """
        self.name = name or "CircuitBreaker"
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        # State tracking
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
        self._half_open_call_in_progress = False
        
        # Metrics
        self.call_count = 0
        self.success_count = 0
        self.failure_count_total = 0
        self.rejection_count = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker (sync)"""
        return async_manager.run_sync(self.call_async(func, *args, **kwargs))
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker (async)"""
        self.call_count += 1
        
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"{self.name}: Attempting reset (moving to HALF_OPEN)")
            else:
                self.rejection_count += 1
                raise CircuitOpenError(
                    f"{self.name} is OPEN. Service unavailable. "
                    f"Retry after {self._get_remaining_timeout()} seconds"
                )
        
        # Handle HALF_OPEN state
        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_call_in_progress:
                # Reject additional calls during half-open test
                self.rejection_count += 1
                raise CircuitOpenError(f"{self.name} is testing recovery. Please retry.")
            self._half_open_call_in_progress = True
        
        # Execute the function
        try:
            # Support both sync and async functions
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
        finally:
            if self.state == CircuitState.HALF_OPEN:
                self._half_open_call_in_progress = False
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try reset"""
        return (
            self.last_failure_time is not None and
            datetime.utcnow() >= self.last_failure_time + timedelta(seconds=self.recovery_timeout)
        )
    
    def _get_remaining_timeout(self) -> int:
        """Get seconds remaining until reset attempt"""
        if self.last_failure_time is None:
            return 0
        
        reset_time = self.last_failure_time + timedelta(seconds=self.recovery_timeout)
        remaining = (reset_time - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))
    
    def _on_success(self):
        """Handle successful call"""
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            # Success in HALF_OPEN means service recovered
            logger.info(f"{self.name}: Service recovered (moving to CLOSED)")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.failure_count_total += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failure in HALF_OPEN means service still down
            logger.warning(f"{self.name}: Service still failing (moving to OPEN)")
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"{self.name}: Failure threshold reached "
                    f"({self.failure_count}/{self.failure_threshold}), moving to OPEN"
                )
                self.state = CircuitState.OPEN
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'call_count': self.call_count,
            'success_count': self.success_count,
            'failure_count_total': self.failure_count_total,
            'rejection_count': self.rejection_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'remaining_timeout': self._get_remaining_timeout() if self.state == CircuitState.OPEN else 0
        }
    
    def reset(self):
        """Manually reset the circuit breaker"""
        logger.info(f"{self.name}: Manual reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None


class CircuitOpenError(Exception):
    """Exception raised when circuit is open"""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one"""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                name=name
            )
        return self.breakers[name]
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            name: breaker.get_status()
            for name, breaker in self.breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()


# Global circuit breaker manager
circuit_manager = CircuitBreakerManager()


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator to add circuit breaker to a function
    
    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before retry
        expected_exception: Exception to catch
    """
    def decorator(func):
        breaker = circuit_manager.get_or_create(
            name,
            failure_threshold,
            recovery_timeout,
            expected_exception
        )
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator