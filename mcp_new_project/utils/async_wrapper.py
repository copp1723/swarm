"""Async/sync bridge utilities to eliminate event loop duplication"""
import asyncio
import functools
import logging
from typing import Callable, Any, TypeVar, Coroutine

logger = logging.getLogger(__name__)
T = TypeVar('T')

class AsyncManager:
    """Centralized async event loop management"""
    
    @staticmethod
    def run_sync(coro: Coroutine[Any, Any, T]) -> T:
        """Run async coroutine in sync context safely"""
        try:
            # Try to get existing loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, use asyncio.run_coroutine_threadsafe
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # No existing loop, create new one
            return asyncio.run(coro)
    
    @staticmethod
    def async_route(func: Callable) -> Callable:
        """Decorator to handle async functions in Flask routes"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return AsyncManager.run_sync(func(*args, **kwargs))
            return func(*args, **kwargs)
        return wrapper

# Global instance
async_manager = AsyncManager()