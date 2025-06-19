"""
Improved Async/Sync Bridge
More efficient and reliable event loop handling
"""
import asyncio
import functools
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, TypeVar, Coroutine, Optional

logger = logging.getLogger(__name__)
T = TypeVar('T')


class AsyncBridge:
    """
    Improved async/sync bridge with:
    - Cached thread pool executor
    - Better event loop detection
    - Proper cleanup
    - Error handling
    """
    
    def __init__(self):
        self._executor: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()
    
    def _get_executor(self) -> ThreadPoolExecutor:
        """Get or create thread pool executor"""
        if self._executor is None:
            with self._lock:
                if self._executor is None:
                    self._executor = ThreadPoolExecutor(
                        max_workers=4,
                        thread_name_prefix="async_bridge"
                    )
        return self._executor
    
    def run_sync(self, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run async coroutine in sync context safely
        
        Handles three cases:
        1. No event loop exists -> create new one
        2. Event loop exists but not running -> use it
        3. Event loop exists and running -> run in thread pool
        """
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, need to run in separate thread
            future = self._get_executor().submit(asyncio.run, coro)
            return future.result()
        except RuntimeError:
            # No running loop, check if one exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
                return loop.run_until_complete(coro)
            except RuntimeError:
                # No event loop at all, create new one
                return asyncio.run(coro)
    
    def async_route(self, func: Callable) -> Callable:
        """
        Decorator for Flask routes that handles async functions
        
        Usage:
            @app.route('/path')
            @async_bridge.async_route
            async def my_route():
                await some_async_operation()
                return jsonify(result)
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                return self.run_sync(func(*args, **kwargs))
            return func(*args, **kwargs)
        return wrapper
    
    def ensure_async(self, func: Callable) -> Callable:
        """
        Ensure a function is async (wraps sync functions)
        
        Usage:
            async_func = async_bridge.ensure_async(potentially_sync_func)
            await async_func()
        """
        if asyncio.iscoroutinefunction(func):
            return func
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._get_executor(),
                functools.partial(func, *args, **kwargs)
            )
        
        return async_wrapper
    
    def cleanup(self):
        """Clean up resources"""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# Global instance with backward compatibility
async_bridge = AsyncBridge()

# Backward compatibility
class AsyncManager:
    """Backward compatibility wrapper"""
    
    @staticmethod
    def run_sync(coro: Coroutine[Any, Any, T]) -> T:
        return async_bridge.run_sync(coro)
    
    @staticmethod
    def async_route(func: Callable) -> Callable:
        return async_bridge.async_route(func)


# Global instance for backward compatibility
async_manager = AsyncManager()