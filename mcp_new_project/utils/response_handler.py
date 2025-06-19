"""Centralized response handling with consistent error patterns"""
from flask import jsonify
from functools import wraps
import logging
from typing import Dict, Any, Optional, Callable
from services.error_handler import error_handler, ErrorCategory

logger = logging.getLogger(__name__)

class ResponseHandler:
    """Standardized API response handling"""
    
    @staticmethod
    def success(data: Any = None, message: str = None, status_code: int = 200) -> tuple:
        """Standard success response"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return jsonify(response), status_code
    
    @staticmethod
    def error(message: str, status_code: int = 500, error_code: str = None, details: Dict = None) -> tuple:
        """Standard error response"""
        response = {
            'success': False,
            'error': message
        }
        if error_code:
            response['error_code'] = error_code
        if details:
            response['details'] = details
        return jsonify(response), status_code
    
    @staticmethod
    def handle_route_errors(error_category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR):
        """Decorator for consistent route error handling"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    result = func(*args, **kwargs)
                    # If result is already a response tuple, return as-is
                    if isinstance(result, tuple) and len(result) == 2:
                        return result
                    # If result is a dict, wrap in success response
                    if isinstance(result, dict):
                        return ResponseHandler.success(result)
                    return result
                except Exception as e:
                    logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                    error_context = error_handler.handle_error(
                        e, error_category, 
                        {'endpoint': func.__name__, 'args': args, 'kwargs': kwargs}
                    )
                    return ResponseHandler.error(
                        error_context.user_message,
                        500,
                        error_context.error_category.value,
                        {'suggestions': error_context.recovery_suggestions}
                    )
            return wrapper
        return decorator

# Global instance
response_handler = ResponseHandler()