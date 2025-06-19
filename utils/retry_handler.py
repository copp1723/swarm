"""Advanced retry mechanisms with exponential backoff and jitter"""
import asyncio
import random
import time
from functools import wraps
from typing import Union, Tuple, Type, Callable, Optional, List, Any
import logging
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        retry_on_result: Optional[Callable] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.exceptions = exceptions
        self.retry_on_result = retry_on_result


class RetryHandler:
    """Advanced retry handler with various strategies"""
    
    @staticmethod
    def calculate_delay(
        attempt: int,
        base_delay: float,
        max_delay: float,
        exponential_base: float,
        jitter: bool
    ) -> float:
        """Calculate delay for next retry attempt"""
        # Exponential backoff
        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
        
        # Add jitter to prevent thundering herd
        if jitter:
            # Full jitter strategy: delay = random(0, calculated_delay)
            delay = delay * random.random()
            # Ensure minimum delay
            delay = max(delay, base_delay * 0.1)
        
        return delay
    
    @staticmethod
    def should_retry(
        exception: Optional[Exception],
        result: Any,
        config: RetryConfig,
        attempt: int
    ) -> bool:
        """Determine if we should retry based on exception or result"""
        # Check if we've exhausted attempts
        if attempt >= config.max_attempts:
            return False
        
        # Check exception
        if exception:
            return isinstance(exception, config.exceptions)
        
        # Check result if predicate provided
        if config.retry_on_result:
            return config.retry_on_result(result)
        
        return False
    
    @classmethod
    def retry(cls, config: Optional[RetryConfig] = None, **kwargs):
        """
        Retry decorator for sync and async functions
        
        Args:
            config: RetryConfig object or None
            **kwargs: Override config parameters
        """
        # Create config
        if config is None:
            config = RetryConfig(**kwargs)
        else:
            # Override config with kwargs
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **func_kwargs):
                last_exception = None
                
                for attempt in range(1, config.max_attempts + 1):
                    try:
                        result = await func(*args, **func_kwargs)
                        
                        # Check if result should trigger retry
                        if cls.should_retry(None, result, config, attempt):
                            if attempt < config.max_attempts:
                                delay = cls.calculate_delay(
                                    attempt,
                                    config.base_delay,
                                    config.max_delay,
                                    config.exponential_base,
                                    config.jitter
                                )
                                logger.warning(
                                    f"Retry {attempt}/{config.max_attempts} for {func.__name__} "
                                    f"due to result check, waiting {delay:.2f}s"
                                )
                                await asyncio.sleep(delay)
                                continue
                        
                        return result
                        
                    except config.exceptions as e:
                        last_exception = e
                        
                        if attempt >= config.max_attempts:
                            logger.error(
                                f"All {config.max_attempts} attempts failed for {func.__name__}: {e}"
                            )
                            raise
                        
                        delay = cls.calculate_delay(
                            attempt,
                            config.base_delay,
                            config.max_delay,
                            config.exponential_base,
                            config.jitter
                        )
                        
                        logger.warning(
                            f"Retry {attempt}/{config.max_attempts} for {func.__name__} "
                            f"after {type(e).__name__}: {e}, waiting {delay:.2f}s"
                        )
                        
                        await asyncio.sleep(delay)
                
                # Should never reach here
                if last_exception:
                    raise last_exception
                    
            @wraps(func)
            def sync_wrapper(*args, **func_kwargs):
                last_exception = None
                
                for attempt in range(1, config.max_attempts + 1):
                    try:
                        result = func(*args, **func_kwargs)
                        
                        # Check if result should trigger retry
                        if cls.should_retry(None, result, config, attempt):
                            if attempt < config.max_attempts:
                                delay = cls.calculate_delay(
                                    attempt,
                                    config.base_delay,
                                    config.max_delay,
                                    config.exponential_base,
                                    config.jitter
                                )
                                logger.warning(
                                    f"Retry {attempt}/{config.max_attempts} for {func.__name__} "
                                    f"due to result check, waiting {delay:.2f}s"
                                )
                                time.sleep(delay)
                                continue
                        
                        return result
                        
                    except config.exceptions as e:
                        last_exception = e
                        
                        if attempt >= config.max_attempts:
                            logger.error(
                                f"All {config.max_attempts} attempts failed for {func.__name__}: {e}"
                            )
                            raise
                        
                        delay = cls.calculate_delay(
                            attempt,
                            config.base_delay,
                            config.max_delay,
                            config.exponential_base,
                            config.jitter
                        )
                        
                        logger.warning(
                            f"Retry {attempt}/{config.max_attempts} for {func.__name__} "
                            f"after {type(e).__name__}: {e}, waiting {delay:.2f}s"
                        )
                        
                        time.sleep(delay)
                
                # Should never reach here
                if last_exception:
                    raise last_exception
            
            # Return appropriate wrapper
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator


# Convenience decorators with common configurations

def retry_on_network_error(func):
    """Retry on common network errors"""
    network_errors = (
        ConnectionError,
        TimeoutError,
        OSError,
    )
    return RetryHandler.retry(
        max_attempts=3,
        base_delay=1,
        exceptions=network_errors
    )(func)


def retry_on_db_error(func):
    """Retry on database errors"""
    # Import here to avoid circular imports
    from sqlalchemy.exc import OperationalError, DisconnectionError
    
    db_errors = (
        OperationalError,
        DisconnectionError,
    )
    return RetryHandler.retry(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5,
        exceptions=db_errors
    )(func)


def aggressive_retry(func):
    """Aggressive retry for critical operations"""
    return RetryHandler.retry(
        max_attempts=5,
        base_delay=2,
        max_delay=120,
        exponential_base=2,
        jitter=True
    )(func)


class RetryWithFallback:
    """Retry with fallback strategies"""
    
    def __init__(self, fallback_chain: List[Callable], retry_config: Optional[RetryConfig] = None):
        """
        Initialize retry with fallback
        
        Args:
            fallback_chain: List of functions to try in order
            retry_config: Retry configuration for each function
        """
        self.fallback_chain = fallback_chain
        self.retry_config = retry_config or RetryConfig(max_attempts=2)
    
    async def execute_async(self, *args, **kwargs):
        """Execute with fallback chain (async)"""
        last_exception = None
        
        for i, func in enumerate(self.fallback_chain):
            try:
                logger.info(f"Attempting function {i+1}/{len(self.fallback_chain)}: {func.__name__}")
                
                # Apply retry to each function
                retried_func = RetryHandler.retry(self.retry_config)(func)
                
                if asyncio.iscoroutinefunction(func):
                    return await retried_func(*args, **kwargs)
                else:
                    return retried_func(*args, **kwargs)
                    
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Function {func.__name__} failed: {e}. "
                    f"Trying next fallback..." if i < len(self.fallback_chain) - 1 else "No more fallbacks."
                )
        
        # All fallbacks failed
        raise Exception(f"All fallback strategies failed. Last error: {last_exception}")
    
    def execute(self, *args, **kwargs):
        """Execute with fallback chain (sync)"""
        if any(asyncio.iscoroutinefunction(f) for f in self.fallback_chain):
            # If any function is async, run in async context
            return async_manager.run_sync(self.execute_async(*args, **kwargs))
        
        last_exception = None
        
        for i, func in enumerate(self.fallback_chain):
            try:
                logger.info(f"Attempting function {i+1}/{len(self.fallback_chain)}: {func.__name__}")
                
                # Apply retry to each function
                retried_func = RetryHandler.retry(self.retry_config)(func)
                return retried_func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Function {func.__name__} failed: {e}. "
                    f"Trying next fallback..." if i < len(self.fallback_chain) - 1 else "No more fallbacks."
                )
        
        # All fallbacks failed
        raise Exception(f"All fallback strategies failed. Last error: {last_exception}")