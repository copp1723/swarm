"""
Enhanced API Error Handler for Consistent Error Handling
Provides decorators and utilities for standardized error handling across all API endpoints
"""
import logging
import functools
from typing import Callable, Optional, Dict, Any, Union, Type
from flask import jsonify, request, Response
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from utils.error_catalog import (
    ErrorCodes, format_error_response, ErrorBuilder,
    get_status_code, is_client_error, is_server_error
)
from utils.api_response import error_response, validation_error_response
from services.error_handler import ErrorHandler, ErrorCategory

logger = logging.getLogger(__name__)


class APIException(Exception):
    """Base exception for API errors with structured error information"""
    
    def __init__(
        self,
        error_code: str,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code or get_status_code(error_code)
        self.details = details or {}
        self.kwargs = kwargs
        super().__init__(message or error_code)


class ValidationError(APIException):
    """Validation error with field-specific errors"""
    
    def __init__(self, field_errors: Dict[str, str], message: str = "Validation failed"):
        super().__init__(
            ErrorCodes.VALIDATION_ERROR,
            message=message,
            details={'field_errors': field_errors}
        )


class ResourceNotFoundError(APIException):
    """Resource not found error"""
    
    def __init__(self, resource_type: str, resource_id: Union[str, int]):
        super().__init__(
            ErrorCodes.NOT_FOUND,
            resource=f"{resource_type}:{resource_id}",
            details={
                'resource_type': resource_type,
                'resource_id': resource_id
            }
        )


class ServiceUnavailableError(APIException):
    """Service unavailable error"""
    
    def __init__(self, service_name: str, reason: Optional[str] = None):
        super().__init__(
            ErrorCodes.SERVICE_UNAVAILABLE,
            details={
                'service': service_name,
                'reason': reason or 'Service is currently unavailable'
            }
        )


class AgentError(APIException):
    """Agent-specific error"""
    
    def __init__(self, agent_id: str, error_type: str = ErrorCodes.AGENT_ERROR, details: Optional[Dict] = None):
        super().__init__(
            error_type,
            agent_id=agent_id,
            details=details or {}
        )


def handle_api_exception(
    log_errors: bool = True,
    include_stack_trace: bool = False,
    error_handler_instance: Optional[ErrorHandler] = None
):
    """
    Decorator for consistent API error handling with comprehensive exception catching.
    
    Args:
        log_errors: Whether to log errors
        include_stack_trace: Include stack trace in error details (only in debug mode)
        error_handler_instance: Optional ErrorHandler instance for advanced error processing
    
    Usage:
        @agents_bp.route('/endpoint')
        @handle_api_exception()
        def endpoint():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
                
            except APIException as e:
                # Handle custom API exceptions
                if log_errors:
                    logger.warning(
                        f"API error in {func.__name__}: {e.error_code} - {e.message}",
                        extra={
                            'endpoint': request.endpoint,
                            'method': request.method,
                            'error_code': e.error_code,
                            'details': e.details
                        }
                    )
                
                response = format_error_response(
                    e.error_code,
                    status_code=e.status_code,
                    request_id=request.headers.get('X-Request-ID'),
                    details=e.details,
                    **e.kwargs
                )
                return jsonify(response), e.status_code
                
            except ValidationError as e:
                # Handle validation errors
                if log_errors:
                    logger.warning(f"Validation error in {func.__name__}: {e.message}")
                
                return validation_error_response(
                    message=e.message,
                    validation_errors=e.details.get('field_errors', {})
                )
                
            except HTTPException as e:
                # Handle Werkzeug HTTP exceptions
                if log_errors:
                    logger.warning(f"HTTP exception in {func.__name__}: {e.code} - {e.description}")
                
                error_code = {
                    400: ErrorCodes.INVALID_REQUEST,
                    401: ErrorCodes.UNAUTHORIZED,
                    403: ErrorCodes.FORBIDDEN,
                    404: ErrorCodes.NOT_FOUND,
                    405: ErrorCodes.METHOD_NOT_ALLOWED,
                    409: ErrorCodes.CONFLICT,
                    429: ErrorCodes.TOO_MANY_REQUESTS,
                    500: ErrorCodes.INTERNAL_ERROR,
                    503: ErrorCodes.SERVICE_UNAVAILABLE
                }.get(e.code, ErrorCodes.INTERNAL_ERROR)
                
                response = format_error_response(
                    error_code,
                    status_code=e.code,
                    request_id=request.headers.get('X-Request-ID'),
                    details={'description': e.description}
                )
                return jsonify(response), e.code
                
            except IntegrityError as e:
                # Handle database integrity errors
                if log_errors:
                    logger.error(f"Database integrity error in {func.__name__}: {e}")
                
                response = format_error_response(
                    ErrorCodes.DUPLICATE_ENTRY,
                    request_id=request.headers.get('X-Request-ID'),
                    details={'constraint': str(e.orig) if hasattr(e, 'orig') else str(e)}
                )
                return jsonify(response), 409
                
            except SQLAlchemyError as e:
                # Handle other database errors
                if log_errors:
                    logger.error(f"Database error in {func.__name__}: {e}", exc_info=True)
                
                response = format_error_response(
                    ErrorCodes.DATABASE_ERROR,
                    request_id=request.headers.get('X-Request-ID'),
                    details={'error': str(e)} if include_stack_trace else None
                )
                return jsonify(response), 500
                
            except ValueError as e:
                # Handle value errors as validation errors
                if log_errors:
                    logger.warning(f"Value error in {func.__name__}: {e}")
                
                response = format_error_response(
                    ErrorCodes.VALIDATION_ERROR,
                    request_id=request.headers.get('X-Request-ID'),
                    details={'error': str(e)}
                )
                return jsonify(response), 422
                
            except FileNotFoundError as e:
                # Handle file not found errors
                if log_errors:
                    logger.warning(f"File not found in {func.__name__}: {e}")
                
                response = format_error_response(
                    ErrorCodes.FILE_NOT_FOUND,
                    filename=str(e),
                    request_id=request.headers.get('X-Request-ID')
                )
                return jsonify(response), 404
                
            except TimeoutError as e:
                # Handle timeout errors
                if log_errors:
                    logger.error(f"Timeout error in {func.__name__}: {e}")
                
                response = format_error_response(
                    ErrorCodes.TIMEOUT_ERROR,
                    seconds=30,  # Default timeout
                    request_id=request.headers.get('X-Request-ID')
                )
                return jsonify(response), 504
                
            except Exception as e:
                # Handle all other exceptions
                if log_errors:
                    logger.error(
                        f"Unhandled error in {func.__name__}: {type(e).__name__} - {e}",
                        exc_info=True,
                        extra={
                            'endpoint': request.endpoint,
                            'method': request.method,
                            'path': request.path,
                            'remote_addr': request.remote_addr
                        }
                    )
                
                # Use error handler if provided
                if error_handler_instance:
                    from utils.session import get_session_id
                    error_context = error_handler_instance.handle_error(
                        e,
                        ErrorCategory.UNKNOWN_ERROR,
                        {
                            'endpoint': func.__name__,
                            'method': request.method,
                            'path': request.path
                        },
                        get_session_id()
                    )
                    
                    response = format_error_response(
                        ErrorCodes.INTERNAL_ERROR,
                        request_id=request.headers.get('X-Request-ID'),
                        details={
                            'suggestions': error_context.recovery_suggestions,
                            'error_type': type(e).__name__
                        } if include_stack_trace else {
                            'suggestions': error_context.recovery_suggestions
                        }
                    )
                    return jsonify(response), 500
                else:
                    # Fallback error response
                    response = format_error_response(
                        ErrorCodes.INTERNAL_ERROR,
                        request_id=request.headers.get('X-Request-ID'),
                        details={
                            'error_type': type(e).__name__,
                            'message': str(e)
                        } if include_stack_trace else None
                    )
                    return jsonify(response), 500
                    
        return wrapper
    return decorator


def validate_request_data(
    required_fields: Optional[Dict[str, Type]] = None,
    optional_fields: Optional[Dict[str, Type]] = None
):
    """
    Decorator to validate request JSON data.
    
    Args:
        required_fields: Dict of field_name -> expected_type
        optional_fields: Dict of field_name -> expected_type
    
    Usage:
        @validate_request_data(
            required_fields={'task': str, 'agents': list},
            optional_fields={'priority': int, 'enable_real_time': bool}
        )
        def endpoint():
            data = request.get_json()  # Already validated
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            data = request.get_json()
            
            # Check if JSON data is provided
            if data is None:
                raise APIException(
                    ErrorCodes.INVALID_REQUEST,
                    details={'reason': 'No JSON data provided'}
                )
            
            # Validate required fields
            if required_fields:
                field_errors = {}
                
                for field, expected_type in required_fields.items():
                    if field not in data:
                        field_errors[field] = 'This field is required'
                    elif not isinstance(data[field], expected_type):
                        field_errors[field] = f'Expected {expected_type.__name__}, got {type(data[field]).__name__}'
                    elif expected_type == str and not data[field].strip():
                        field_errors[field] = 'This field cannot be empty'
                
                if field_errors:
                    raise ValidationError(field_errors)
            
            # Validate optional fields if provided
            if optional_fields:
                field_errors = {}
                
                for field, expected_type in optional_fields.items():
                    if field in data and not isinstance(data[field], expected_type):
                        field_errors[field] = f'Expected {expected_type.__name__}, got {type(data[field]).__name__}'
                
                if field_errors:
                    raise ValidationError(field_errors)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_service(service_name: str, error_message: Optional[str] = None):
    """
    Decorator to ensure a service is available before executing endpoint.
    
    Args:
        service_name: Name of the service to check
        error_message: Custom error message
    
    Usage:
        @require_service('multi_agent_task_service')
        def endpoint():
            # Service is guaranteed to be available
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from services.service_container import get_service_container
            
            service = get_service_container().get(service_name)
            if not service:
                raise ServiceUnavailableError(
                    service_name,
                    error_message or f'{service_name} is not available'
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_endpoint_access(level: str = 'info'):
    """
    Decorator to log endpoint access with request details.
    
    Args:
        level: Logging level (debug, info, warning, error)
    
    Usage:
        @log_endpoint_access()
        def endpoint():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from utils.session import get_session_id
            
            log_func = getattr(logger, level, logger.info)
            log_func(
                f"Endpoint accessed: {func.__name__}",
                extra={
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'session_id': get_session_id(),
                    'user_agent': request.headers.get('User-Agent')
                }
            )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Helper functions for common error scenarios
def handle_missing_parameter(parameter: str) -> Response:
    """Return standardized response for missing parameter"""
    response = format_error_response(
        ErrorCodes.MISSING_PARAMETER,
        parameter=parameter
    )
    return jsonify(response), response['error']['status_code']


def handle_invalid_parameter(parameter: str, reason: str) -> Response:
    """Return standardized response for invalid parameter"""
    response = format_error_response(
        ErrorCodes.INVALID_PARAMETER,
        parameter=parameter,
        reason=reason
    )
    return jsonify(response), response['error']['status_code']


def handle_resource_not_found(resource_type: str, resource_id: Union[str, int]) -> Response:
    """Return standardized response for resource not found"""
    response = format_error_response(
        ErrorCodes.NOT_FOUND,
        resource=f"{resource_type}:{resource_id}"
    )
    return jsonify(response), response['error']['status_code']


def handle_service_unavailable(service_name: str, reason: Optional[str] = None) -> Response:
    """Return standardized response for service unavailable"""
    response = format_error_response(
        ErrorCodes.SERVICE_UNAVAILABLE,
        details={
            'service': service_name,
            'reason': reason or 'Service is currently unavailable'
        }
    )
    return jsonify(response), response['error']['status_code']