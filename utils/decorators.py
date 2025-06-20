"""
Utility decorators for API endpoints and service management
"""
import logging
import functools
from typing import Callable, Optional, Any
from flask import request, jsonify
from services.service_container import get_service_container
from utils.logging import log_system_event
from utils.session import get_session_id

logger = logging.getLogger(__name__)


def require_service(service_name: str):
    """
    Decorator to ensure a service is available before executing the endpoint.
    
    Args:
        service_name: Name of the required service
        
    Returns:
        HTTP 503 if service is unavailable, otherwise executes the endpoint
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            service = get_service_container().get(service_name)
            if not service:
                return jsonify({
                    'success': False,
                    'error': f'Required service "{service_name}" is not available',
                    'error_code': 'SERVICE_UNAVAILABLE'
                }), 503
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_endpoint_access(log_level: str = 'info'):
    """
    Decorator to log endpoint access with request details.
    
    Args:
        log_level: Logging level ('info', 'debug', etc.)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            session_id = get_session_id()
            endpoint = request.endpoint or func.__name__
            method = request.method
            
            # Log the access
            log_system_event(
                log_level,
                'endpoint_access',
                f"{method} {endpoint} accessed",
                session_id,
                additional_data={
                    'endpoint': endpoint,
                    'method': method,
                    'user_agent': request.headers.get('User-Agent'),
                    'remote_addr': request.remote_addr
                }
            )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def cache_result(duration_seconds: int = 300):
    """
    Simple in-memory cache decorator for expensive operations.
    
    Args:
        duration_seconds: How long to cache the result
    """
    cache = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            import hashlib
            import json
            
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hashlib.md5(json.dumps(str(args) + str(sorted(kwargs.items()))).encode()).hexdigest()}"
            
            # Check if we have a valid cached result
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < duration_seconds:
                    return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            
            return result
        return wrapper
    return decorator


def retry_on_failure(max_retries: int = 3, delay_seconds: float = 1.0):
    """
    Decorator to retry function execution on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay_seconds: Delay between retries
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                        time.sleep(delay_seconds)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
            
            raise last_exception
        return wrapper
    return decorator


def validate_json_payload(required_fields: Optional[list] = None, optional_fields: Optional[list] = None):
    """
    Decorator to validate JSON payload structure.
    
    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No JSON payload provided',
                    'error_code': 'MISSING_PAYLOAD'
                }), 400
            
            # Check required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing_fields)}',
                        'error_code': 'MISSING_FIELDS',
                        'missing_fields': missing_fields
                    }), 400
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def measure_execution_time(log_slow_requests: bool = True, slow_threshold_seconds: float = 1.0):
    """
    Decorator to measure and optionally log slow endpoint execution times.
    
    Args:
        log_slow_requests: Whether to log requests that exceed the threshold
        slow_threshold_seconds: Threshold for considering a request slow
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if log_slow_requests and execution_time > slow_threshold_seconds:
                session_id = get_session_id()
                log_system_event(
                    'warning',
                    'slow_request',
                    f"Slow request: {func.__name__} took {execution_time:.2f}s",
                    session_id,
                    additional_data={
                        'execution_time': execution_time,
                        'endpoint': request.endpoint,
                        'method': request.method
                    }
                )
            
            return result
        return wrapper
    return decorator

