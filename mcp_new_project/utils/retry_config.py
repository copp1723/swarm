"""
Retry configuration and decorators for task retries
"""

from functools import wraps
import time
from typing import Callable, Any, Optional, Tuple, Type
from loguru import logger


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Decorator for retrying functions on failure with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for exponential delay
        exceptions: Tuple of exception types to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            # Re-raise the last exception if all retries failed
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


class RetryConfig:
    """Configuration for Celery task retries"""
    
    # Default retry configuration
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_RETRY_DELAY = 60  # seconds
    DEFAULT_RETRY_BACKOFF = 2
    DEFAULT_RETRY_JITTER = True
    
    # Task-specific configurations
    EMAIL_TASK_MAX_RETRIES = 5
    EMAIL_TASK_RETRY_DELAY = 30
    
    WEBHOOK_MAX_RETRIES = 3
    WEBHOOK_RETRY_DELAY = 10
    
    AGENT_TASK_MAX_RETRIES = 2
    AGENT_TASK_RETRY_DELAY = 120
    
    @classmethod
    def get_retry_kwargs(cls, task_type: str = 'default') -> dict:
        """Get retry configuration for a specific task type"""
        configs = {
            'email': {
                'max_retries': cls.EMAIL_TASK_MAX_RETRIES,
                'default_retry_delay': cls.EMAIL_TASK_RETRY_DELAY,
                'retry_backoff': cls.DEFAULT_RETRY_BACKOFF,
                'retry_jitter': cls.DEFAULT_RETRY_JITTER
            },
            'webhook': {
                'max_retries': cls.WEBHOOK_MAX_RETRIES,
                'default_retry_delay': cls.WEBHOOK_RETRY_DELAY,
                'retry_backoff': cls.DEFAULT_RETRY_BACKOFF,
                'retry_jitter': cls.DEFAULT_RETRY_JITTER
            },
            'agent': {
                'max_retries': cls.AGENT_TASK_MAX_RETRIES,
                'default_retry_delay': cls.AGENT_TASK_RETRY_DELAY,
                'retry_backoff': cls.DEFAULT_RETRY_BACKOFF,
                'retry_jitter': cls.DEFAULT_RETRY_JITTER
            },
            'default': {
                'max_retries': cls.DEFAULT_MAX_RETRIES,
                'default_retry_delay': cls.DEFAULT_RETRY_DELAY,
                'retry_backoff': cls.DEFAULT_RETRY_BACKOFF,
                'retry_jitter': cls.DEFAULT_RETRY_JITTER
            }
        }
        
        return configs.get(task_type, configs['default'])