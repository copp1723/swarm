"""Async error handling utilities for Flask routes"""
import asyncio
import functools
import logging
import traceback
import uuid
from typing import Dict, Tuple, Any, Callable, Optional
from flask import jsonify, request
from services.error_handler import error_handler, ErrorCategory

logger = logging.getLogger(__name__)


def handle_async_route_errors(error_category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR):
    """
    Decorator for handling errors in async Flask routes.
    
    Args:
        error_category: Default error category for uncategorized errors
        
    Example:
        @app.route('/api/async-endpoint')
        @handle_async_route_errors(ErrorCategory.API_ERROR)
        async def async_endpoint():
            return {'data': 'success'}
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate request ID for tracking
            request_id = str(uuid.uuid4())
            if hasattr(request, 'headers'):
                request_id = request.headers.get('X-Request-ID', request_id)
            
            try:
                # Log request start
                logger.debug(f"Starting async request {request_id} for {func.__name__}")
                
                # Execute the async function
                result = await func(*args, **kwargs)
                
                # If result is already a response tuple, return as-is
                if isinstance(result, tuple) and len(result) == 2:
                    return result
                    
                # If result is a dict, wrap in success response
                if isinstance(result, dict):
                    response_data = {
                        'success': True,
                        'data': result,
                        'request_id': request_id
                    }
                    return jsonify(response_data), 200
                    
                return result
                
            except asyncio.CancelledError:
                # Handle cancelled tasks
                logger.warning(f"Async task cancelled for {func.__name__} (request_id: {request_id})")
                return await async_error_response(
                    Exception("Request was cancelled"),
                    status_code=499,  # Client Closed Request
                    request_id=request_id,
                    error_code="REQUEST_CANCELLED"
                )
                
            except asyncio.TimeoutError:
                # Handle timeout errors
                logger.error(f"Async timeout in {func.__name__} (request_id: {request_id})")
                return await async_error_response(
                    Exception("Request timeout"),
                    status_code=504,  # Gateway Timeout
                    request_id=request_id,
                    error_code="REQUEST_TIMEOUT"
                )
                
            except Exception as e:
                # Log full stack trace
                logger.error(
                    f"Error in async route {func.__name__} (request_id: {request_id}): {e}",
                    exc_info=True
                )
                
                # Use error handler service if available
                error_context = error_handler.handle_error(
                    e, error_category,
                    {
                        'endpoint': func.__name__,
                        'request_id': request_id,
                        'args': args,
                        'kwargs': kwargs
                    }
                )
                
                return await async_error_response(
                    e,
                    status_code=500,
                    request_id=request_id,
                    error_code=error_context.error_category.value,
                    user_message=error_context.user_message,
                    suggestions=error_context.recovery_suggestions
                )
                
        return wrapper
    return decorator


async def async_error_response(
    error: Exception,
    status_code: int = 500,
    request_id: Optional[str] = None,
    error_code: Optional[str] = None,
    user_message: Optional[str] = None,
    suggestions: Optional[list] = None
) -> Tuple[Dict, int]:
    """
    Create standardized error response for async routes.
    
    Args:
        error: The exception that occurred
        status_code: HTTP status code
        request_id: Request tracking ID
        error_code: Specific error code
        user_message: User-friendly error message
        suggestions: Recovery suggestions
        
    Returns:
        Tuple of (response_dict, status_code)
    """
    # Default error message
    if not user_message:
        user_message = "An error occurred processing your request"
        
    # Build error response
    response = {
        'success': False,
        'error': user_message,
        'request_id': request_id or str(uuid.uuid4())
    }
    
    # Add error code if provided
    if error_code:
        response['error_code'] = error_code
        
    # Add recovery suggestions if provided
    if suggestions:
        response['suggestions'] = suggestions
        
    # In development mode, add more details
    if logger.isEnabledFor(logging.DEBUG):
        response['debug'] = {
            'exception_type': type(error).__name__,
            'exception_message': str(error),
            'traceback': traceback.format_exc()
        }
        
    return jsonify(response), status_code


class AsyncRouteHandler:
    """
    Class-based async route handler with error handling.
    
    Example:
        handler = AsyncRouteHandler(error_category=ErrorCategory.API_ERROR)
        
        @app.route('/api/users/<int:user_id>')
        @handler.handle_async
        async def get_user(user_id):
            user = await fetch_user(user_id)
            return {'user': user}
    """
    
    def __init__(self, error_category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR):
        """
        Initialize the async route handler.
        
        Args:
            error_category: Default error category for uncategorized errors
        """
        self.error_category = error_category
        
    def handle_async(self, func: Callable) -> Callable:
        """
        Decorator method for handling async routes.
        
        Args:
            func: The async route function
            
        Returns:
            Wrapped function with error handling
        """
        return handle_async_route_errors(self.error_category)(func)
        
    async def execute_with_timeout(
        self,
        coro: Callable,
        timeout: float = 30.0,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an async function with timeout.
        
        Args:
            coro: Async function to execute
            timeout: Timeout in seconds
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
        """
        try:
            return await asyncio.wait_for(
                coro(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Timeout executing {coro.__name__} after {timeout}s")
            raise
            
    async def gather_with_errors(
        self,
        *coros,
        return_exceptions: bool = True
    ) -> list:
        """
        Gather multiple async operations with error handling.
        
        Args:
            *coros: Async coroutines to execute
            return_exceptions: Whether to return exceptions as results
            
        Returns:
            List of results (and exceptions if return_exceptions=True)
        """
        try:
            results = await asyncio.gather(
                *coros,
                return_exceptions=return_exceptions
            )
            
            # Log any exceptions that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Error in gathered coroutine {i}: {result}")
                    
            return results
        except Exception as e:
            logger.error(f"Error in gather operation: {e}")
            raise


# Utility functions for common async patterns

async def retry_async(
    func: Callable,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Any:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Function result
        
    Raises:
        Last exception if all attempts fail
    """
    attempt = 1
    current_delay = delay
    
    while attempt <= max_attempts:
        try:
            return await func()
        except exceptions as e:
            if attempt == max_attempts:
                logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
                raise
                
            logger.warning(
                f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                f"Retrying in {current_delay}s..."
            )
            
            await asyncio.sleep(current_delay)
            current_delay *= backoff
            attempt += 1


async def run_with_semaphore(
    func: Callable,
    semaphore: asyncio.Semaphore,
    *args,
    **kwargs
) -> Any:
    """
    Run an async function with semaphore for concurrency control.
    
    Args:
        func: Async function to run
        semaphore: Asyncio semaphore
        *args, **kwargs: Arguments for the function
        
    Returns:
        Function result
    """
    async with semaphore:
        return await func(*args, **kwargs)


def create_async_error_handler(
    default_error_category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
    include_debug_info: bool = False,
    log_errors: bool = True
) -> Callable:
    """
    Factory function to create customized async error handlers.
    
    Args:
        default_error_category: Default category for uncategorized errors
        include_debug_info: Whether to include debug info in responses
        log_errors: Whether to log errors
        
    Returns:
        Customized error handler decorator
    """
    def custom_handler(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                    
                response = {
                    'success': False,
                    'error': str(e)
                }
                
                if include_debug_info:
                    response['debug'] = {
                        'function': func.__name__,
                        'exception_type': type(e).__name__,
                        'traceback': traceback.format_exc()
                    }
                    
                return jsonify(response), 500
                
        return wrapper
    return custom_handler