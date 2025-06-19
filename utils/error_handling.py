"""
Unified Error Handling Utilities
Provides consistent error handling patterns across the application
"""
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union, TypeVar
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from flask import jsonify, Response
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorCategory(Enum):
    """Standard error categories"""
    VALIDATION_ERROR = "validation_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    DATABASE_ERROR = "database_error"
    CONNECTION_ERROR = "connection_error"
    EXTERNAL_API_ERROR = "external_api_error"
    RESOURCE_NOT_FOUND = "resource_not_found"
    CONFLICT_ERROR = "conflict_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    CONFIGURATION_ERROR = "configuration_error"
    INTERNAL_ERROR = "internal_error"


@dataclass
class ErrorContext:
    """Structured error information"""
    category: ErrorCategory
    message: str
    details: Optional[Dict[str, Any]] = None
    user_message: Optional[str] = None
    error_code: Optional[str] = None
    timestamp: Optional[datetime] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.user_message is None:
            self.user_message = self._get_default_user_message()
    
    def _get_default_user_message(self) -> str:
        """Get user-friendly message based on category"""
        user_messages = {
            ErrorCategory.VALIDATION_ERROR: "Invalid input provided. Please check your data.",
            ErrorCategory.AUTHENTICATION_ERROR: "Authentication failed. Please check your credentials.",
            ErrorCategory.AUTHORIZATION_ERROR: "You don't have permission to perform this action.",
            ErrorCategory.DATABASE_ERROR: "A database error occurred. Please try again later.",
            ErrorCategory.CONNECTION_ERROR: "Connection failed. Please check your network.",
            ErrorCategory.EXTERNAL_API_ERROR: "External service unavailable. Please try again later.",
            ErrorCategory.RESOURCE_NOT_FOUND: "The requested resource was not found.",
            ErrorCategory.CONFLICT_ERROR: "A conflict occurred. The resource may have been modified.",
            ErrorCategory.RATE_LIMIT_ERROR: "Too many requests. Please slow down.",
            ErrorCategory.CONFIGURATION_ERROR: "System configuration error. Please contact support.",
            ErrorCategory.INTERNAL_ERROR: "An internal error occurred. Please try again later."
        }
        return user_messages.get(self.category, "An unexpected error occurred.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        result = {
            'error': {
                'category': self.category.value,
                'message': self.user_message,
                'timestamp': self.timestamp.isoformat()
            }
        }
        
        if self.error_code:
            result['error']['code'] = self.error_code
        
        if self.details and logger.isEnabledFor(logging.DEBUG):
            result['error']['details'] = self.details
        
        if self.request_id:
            result['error']['request_id'] = self.request_id
        
        return result


class ApplicationError(Exception):
    """Base application exception with error context"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.context = ErrorContext(
            category=category,
            message=message,
            details=details,
            user_message=user_message,
            error_code=error_code
        )


class ValidationError(ApplicationError):
    """Raised for validation failures"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop('details', {})
        if field:
            details['field'] = field
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION_ERROR,
            details=details,
            **kwargs
        )


class AuthenticationError(ApplicationError):
    """Raised for authentication failures"""
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION_ERROR,
            **kwargs
        )


class AuthorizationError(ApplicationError):
    """Raised for authorization failures"""
    def __init__(self, message: str = "Insufficient permissions", **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION_ERROR,
            **kwargs
        )


class ResourceNotFoundError(ApplicationError):
    """Raised when a resource is not found"""
    def __init__(self, resource_type: str, resource_id: Optional[Union[str, int]] = None, **kwargs):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        
        details = kwargs.pop('details', {})
        details.update({
            'resource_type': resource_type,
            'resource_id': resource_id
        })
        
        super().__init__(
            message,
            category=ErrorCategory.RESOURCE_NOT_FOUND,
            details=details,
            **kwargs
        )


class ExternalAPIError(ApplicationError):
    """Raised for external API failures"""
    def __init__(self, service_name: str, message: str, status_code: Optional[int] = None, **kwargs):
        details = kwargs.pop('details', {})
        details.update({
            'service': service_name,
            'status_code': status_code
        })
        
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_API_ERROR,
            details=details,
            **kwargs
        )


def handle_errors(
    default_message: str = "An error occurred",
    log_errors: bool = True,
    include_traceback: bool = False
):
    """
    Decorator for consistent error handling in functions.
    
    Args:
        default_message: Default error message
        log_errors: Whether to log errors
        include_traceback: Include traceback in logs (debug mode)
    
    Usage:
        @handle_errors(default_message="Failed to process request")
        def process_data(data):
            # Process data that might raise exceptions
            return processed_data
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except ApplicationError:
                # Re-raise application errors as they already have context
                raise
            except ValidationError as e:
                if log_errors:
                    logger.warning(f"Validation error in {func.__name__}: {e}")
                raise
            except IntegrityError as e:
                if log_errors:
                    logger.error(f"Database integrity error in {func.__name__}: {e}")
                raise ApplicationError(
                    "Database constraint violation",
                    category=ErrorCategory.DATABASE_ERROR,
                    details={'original_error': str(e)}
                )
            except OperationalError as e:
                if log_errors:
                    logger.error(f"Database operational error in {func.__name__}: {e}")
                raise ApplicationError(
                    "Database connection failed",
                    category=ErrorCategory.CONNECTION_ERROR,
                    details={'original_error': str(e)}
                )
            except SQLAlchemyError as e:
                if log_errors:
                    logger.error(f"Database error in {func.__name__}: {e}")
                raise ApplicationError(
                    "Database operation failed",
                    category=ErrorCategory.DATABASE_ERROR,
                    details={'original_error': str(e)}
                )
            except Exception as e:
                if log_errors:
                    logger.error(
                        f"Unhandled error in {func.__name__}: {e}",
                        exc_info=include_traceback
                    )
                raise ApplicationError(
                    default_message,
                    details={'original_error': str(e), 'function': func.__name__}
                )
        return wrapper
    return decorator


def api_error_handler(
    default_status: int = 500,
    include_request_id: bool = True
):
    """
    Decorator for API endpoint error handling with automatic response formatting.
    
    Args:
        default_status: Default HTTP status code for errors
        include_request_id: Include request ID in error response
    
    Usage:
        @app.route('/api/users/<int:user_id>')
        @api_error_handler(default_status=404)
        def get_user(user_id):
            user = User.query.get(user_id)
            if not user:
                raise ResourceNotFoundError('User', user_id)
            return success_response(data=user.to_dict())
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Response:
            try:
                return func(*args, **kwargs)
            except ApplicationError as e:
                status_code = _get_status_code_for_category(e.context.category)
                return jsonify(e.context.to_dict()), status_code
            except ValueError as e:
                error = ErrorContext(
                    category=ErrorCategory.VALIDATION_ERROR,
                    message=str(e)
                )
                return jsonify(error.to_dict()), 400
            except PermissionError as e:
                error = ErrorContext(
                    category=ErrorCategory.AUTHORIZATION_ERROR,
                    message=str(e)
                )
                return jsonify(error.to_dict()), 403
            except FileNotFoundError as e:
                error = ErrorContext(
                    category=ErrorCategory.RESOURCE_NOT_FOUND,
                    message=str(e)
                )
                return jsonify(error.to_dict()), 404
            except Exception as e:
                logger.error(f"Unhandled error in API endpoint {func.__name__}: {e}", exc_info=True)
                error = ErrorContext(
                    category=ErrorCategory.INTERNAL_ERROR,
                    message="An internal server error occurred",
                    details={'endpoint': func.__name__}
                )
                return jsonify(error.to_dict()), default_status
        return wrapper
    return decorator


def _get_status_code_for_category(category: ErrorCategory) -> int:
    """Map error categories to HTTP status codes"""
    status_map = {
        ErrorCategory.VALIDATION_ERROR: 400,
        ErrorCategory.AUTHENTICATION_ERROR: 401,
        ErrorCategory.AUTHORIZATION_ERROR: 403,
        ErrorCategory.RESOURCE_NOT_FOUND: 404,
        ErrorCategory.CONFLICT_ERROR: 409,
        ErrorCategory.RATE_LIMIT_ERROR: 429,
        ErrorCategory.DATABASE_ERROR: 500,
        ErrorCategory.CONNECTION_ERROR: 503,
        ErrorCategory.EXTERNAL_API_ERROR: 502,
        ErrorCategory.CONFIGURATION_ERROR: 500,
        ErrorCategory.INTERNAL_ERROR: 500
    }
    return status_map.get(category, 500)


def safe_execute(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    exceptions: tuple = (Exception,),
    log_error: bool = True,
    **kwargs
) -> Optional[T]:
    """
    Execute a function safely, returning a default value on error.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        default: Default value to return on error
        exceptions: Tuple of exceptions to catch
        log_error: Whether to log errors
        **kwargs: Keyword arguments
    
    Returns:
        Function result or default value
    
    Usage:
        result = safe_execute(
            parse_json,
            json_string,
            default={},
            exceptions=(JSONDecodeError,)
        )
    """
    try:
        return func(*args, **kwargs)
    except exceptions as e:
        if log_error:
            logger.warning(f"Error in {func.__name__}: {e}")
        return default


def retry_on_error(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to retry a function on specific exceptions.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts in seconds
        backoff: Delay multiplier for each retry
        exceptions: Exceptions to retry on
    
    Usage:
        @retry_on_error(max_attempts=3, exceptions=(ConnectionError,))
        def fetch_data():
            return requests.get('https://api.example.com/data')
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        import time
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator