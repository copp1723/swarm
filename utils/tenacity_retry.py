"""
Tenacity Retry Configuration
Provides resilient retry strategies for external API calls
"""

import logging
from typing import Any, Callable, Optional, Type, Union
from functools import wraps
import asyncio

from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_random_exponential,
    retry_if_exception_type,
    retry_if_not_exception_type,
    before_log,
    after_log,
    RetryError,
    Retrying,
    AsyncRetrying
)

from utils.notification_service import get_notification_service

logger = logging.getLogger(__name__)

# Common exception types to retry
RETRIABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,
)

# Exceptions that should NOT be retried
NON_RETRIABLE_EXCEPTIONS = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


def create_retry_decorator(
    max_attempts: int = 3,
    max_delay: int = 300,  # 5 minutes
    exponential_base: float = 2,
    exponential_max: int = 60,
    exceptions: Optional[tuple] = None,
    on_failure_notify: bool = True,
    notification_context: Optional[dict] = None
) -> Callable:
    """
    Create a custom retry decorator with Tenacity.
    
    Args:
        max_attempts: Maximum number of retry attempts
        max_delay: Maximum total delay in seconds
        exponential_base: Base for exponential backoff
        exponential_max: Maximum wait time between retries
        exceptions: Tuple of exceptions to retry (defaults to RETRIABLE_EXCEPTIONS)
        on_failure_notify: Send notification on final failure
        notification_context: Additional context for notifications
        
    Returns:
        Configured retry decorator
    """
    exceptions = exceptions or RETRIABLE_EXCEPTIONS
    
    def notify_on_failure(retry_state):
        """Send notification when all retries are exhausted"""
        if on_failure_notify and retry_state.outcome.failed:
            notification_service = get_notification_service()
            
            error = retry_state.outcome.exception()
            context = notification_context or {}
            
            # Build error details
            error_details = {
                'function': retry_state.fn.__name__ if retry_state.fn else 'Unknown',
                'attempts': retry_state.attempt_number,
                'error_type': type(error).__name__,
                'error_message': str(error),
                **context
            }
            
            # Send notification asynchronously
            asyncio.create_task(
                notification_service.send_critical_alert(
                    title="Critical: Retry Exhausted",
                    message=f"Function {error_details['function']} failed after {error_details['attempts']} attempts",
                    details=error_details
                )
            )
    
    return retry(
        stop=(stop_after_attempt(max_attempts) | stop_after_delay(max_delay)),
        wait=wait_exponential(multiplier=exponential_base, max=exponential_max),
        retry=retry_if_exception_type(exceptions),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.INFO),
        retry_error_callback=notify_on_failure,
        reraise=True
    )


# Pre-configured retry strategies

def retry_api_call(
    max_attempts: int = 5,
    on_failure_notify: bool = True
) -> Callable:
    """
    Retry decorator for external API calls.
    Uses exponential backoff with jitter.
    """
    return create_retry_decorator(
        max_attempts=max_attempts,
        exponential_base=1,
        exponential_max=30,
        exceptions=RETRIABLE_EXCEPTIONS + (Exception,),
        on_failure_notify=on_failure_notify,
        notification_context={'retry_type': 'api_call'}
    )


def retry_database_operation(
    max_attempts: int = 3,
    on_failure_notify: bool = False
) -> Callable:
    """
    Retry decorator for database operations.
    Quick retries with shorter delays.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, max=5),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before=before_log(logger, logging.DEBUG),
        reraise=True
    )


def retry_webhook_delivery(
    max_attempts: int = 5,
    max_delay: int = 600,  # 10 minutes
    on_failure_notify: bool = True
) -> Callable:
    """
    Retry decorator for webhook delivery.
    Longer delays between attempts.
    """
    async def notify_webhook_failure(retry_state):
        """Custom notification for webhook failures"""
        if retry_state.outcome.failed:
            notification_service = get_notification_service()
            
            # Extract webhook details from args/kwargs
            args = retry_state.args
            kwargs = retry_state.kwargs
            webhook_url = kwargs.get('url') or (args[0] if args else 'Unknown')
            
            await notification_service.send_webhook_failure_alert(
                webhook_url=webhook_url,
                attempts=retry_state.attempt_number,
                error=str(retry_state.outcome.exception())
            )
    
    return retry(
        stop=(stop_after_attempt(max_attempts) | stop_after_delay(max_delay)),
        wait=wait_random_exponential(multiplier=1, max=120),
        retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
        before=before_log(logger, logging.WARNING),
        after=after_log(logger, logging.WARNING),
        retry_error_callback=notify_webhook_failure if on_failure_notify else None,
        reraise=True
    )


def retry_memory_operation(
    max_attempts: int = 3,
    on_failure_notify: bool = True
) -> Callable:
    """
    Retry decorator for memory service operations.
    """
    return create_retry_decorator(
        max_attempts=max_attempts,
        exponential_base=2,
        exponential_max=20,
        on_failure_notify=on_failure_notify,
        notification_context={'retry_type': 'memory_operation'}
    )


# Async retry wrapper
def async_retry_with_notification(
    retry_decorator: Callable,
    notification_context: Optional[dict] = None
) -> Callable:
    """
    Wrapper to add notification support to async retry decorators.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Apply retry decorator
                return await retry_decorator(func)(*args, **kwargs)
            except RetryError as e:
                # Send notification on final failure
                notification_service = get_notification_service()
                await notification_service.send_critical_alert(
                    title=f"Async Retry Failed: {func.__name__}",
                    message=str(e.last_attempt.exception()),
                    details=notification_context or {}
                )
                raise
        return wrapper
    return decorator


# Manual retry helper
class RetryManager:
    """
    Manual retry management for complex scenarios.
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        on_failure_notify: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.on_failure_notify = on_failure_notify
        self.attempt = 0
        
    def should_retry(self, exception: Exception) -> bool:
        """Check if we should retry based on exception type and attempts."""
        self.attempt += 1
        
        if self.attempt >= self.max_attempts:
            return False
            
        # Check if exception is retriable
        return isinstance(exception, RETRIABLE_EXCEPTIONS)
    
    def get_delay(self) -> float:
        """Calculate delay before next retry."""
        delay = min(
            self.base_delay * (self.exponential_base ** (self.attempt - 1)),
            self.max_delay
        )
        return delay
    
    async def notify_failure(self, context: dict):
        """Send notification on final failure."""
        if self.on_failure_notify:
            notification_service = get_notification_service()
            await notification_service.send_critical_alert(
                title="Manual Retry Exhausted",
                message=f"Operation failed after {self.attempt} attempts",
                details=context
            )


# Example usage functions
async def example_api_call_with_retry():
    """Example of using retry decorator for API calls."""
    
    @retry_api_call(max_attempts=5)
    async def call_external_api(url: str) -> dict:
        # Simulated API call
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
    
    try:
        result = await call_external_api("https://api.example.com/data")
        return result
    except RetryError:
        logger.error("API call failed after all retries")
        raise


async def example_manual_retry():
    """Example of manual retry management."""
    
    retry_manager = RetryManager(max_attempts=3, base_delay=2.0)
    
    while True:
        try:
            # Your operation here
            result = await some_operation()
            return result
            
        except Exception as e:
            if retry_manager.should_retry(e):
                delay = retry_manager.get_delay()
                logger.info(f"Retrying after {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                await retry_manager.notify_failure({
                    'operation': 'some_operation',
                    'error': str(e)
                })
                raise