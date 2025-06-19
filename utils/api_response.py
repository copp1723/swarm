"""
Unified API Response Formatting
Provides consistent API response structure across all endpoints
"""
from flask import jsonify, Response
from typing import Any, Optional, Dict, Union, List
from functools import wraps
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """Standard response statuses"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class HTTPStatus:
    """HTTP status codes for consistency"""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


def api_response(
    data: Any = None,
    message: Optional[str] = None,
    status: ResponseStatus = ResponseStatus.SUCCESS,
    http_status: int = HTTPStatus.OK,
    meta: Optional[Dict[str, Any]] = None,
    errors: Optional[List[Dict[str, Any]]] = None
) -> Response:
    """
    Create a standardized API response.
    
    Args:
        data: The response payload
        message: Human-readable message
        status: Response status (success/error/warning/info)
        http_status: HTTP status code
        meta: Additional metadata (pagination, etc.)
        errors: List of error details
    
    Returns:
        Flask JSON response
    
    Usage:
        return api_response(
            data={'user': user.to_dict()},
            message='User created successfully',
            status=ResponseStatus.SUCCESS,
            http_status=HTTPStatus.CREATED
        )
    """
    response_body = {
        'status': status.value,
        'timestamp': datetime.utcnow().isoformat(),
    }
    
    if message:
        response_body['message'] = message
    
    if data is not None:
        response_body['data'] = data
    
    if meta:
        response_body['meta'] = meta
    
    if errors:
        response_body['errors'] = errors
    
    return jsonify(response_body), http_status


def success_response(
    data: Any = None,
    message: str = "Operation successful",
    http_status: int = HTTPStatus.OK,
    meta: Optional[Dict[str, Any]] = None
) -> Response:
    """
    Create a success response.
    
    Usage:
        return success_response(
            data={'users': users},
            message='Users retrieved successfully'
        )
    """
    return api_response(
        data=data,
        message=message,
        status=ResponseStatus.SUCCESS,
        http_status=http_status,
        meta=meta
    )


def error_response(
    message: str = "An error occurred",
    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR,
    error_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    errors: Optional[List[Dict[str, Any]]] = None
) -> Response:
    """
    Create an error response.
    
    Usage:
        return error_response(
            message='Invalid email format',
            http_status=HTTPStatus.BAD_REQUEST,
            error_code='VALIDATION_ERROR',
            details={'field': 'email', 'value': email}
        )
    """
    error_list = errors or []
    
    if error_code or details:
        error_entry = {}
        if error_code:
            error_entry['code'] = error_code
        if details:
            error_entry['details'] = details
        error_list.append(error_entry)
    
    return api_response(
        message=message,
        status=ResponseStatus.ERROR,
        http_status=http_status,
        errors=error_list if error_list else None
    )


def created_response(
    data: Any,
    message: str = "Resource created successfully",
    location: Optional[str] = None
) -> Response:
    """
    Create a 201 Created response.
    
    Usage:
        return created_response(
            data={'id': user.id, 'email': user.email},
            message='User account created',
            location=f'/api/users/{user.id}'
        )
    """
    response = success_response(
        data=data,
        message=message,
        http_status=HTTPStatus.CREATED
    )
    
    if location:
        response.headers['Location'] = location
    
    return response


def not_found_response(
    message: str = "Resource not found",
    resource_type: Optional[str] = None,
    resource_id: Optional[Union[str, int]] = None
) -> Response:
    """
    Create a 404 Not Found response.
    
    Usage:
        return not_found_response(
            message='User not found',
            resource_type='User',
            resource_id=user_id
        )
    """
    details = {}
    if resource_type:
        details['resource_type'] = resource_type
    if resource_id:
        details['resource_id'] = resource_id
    
    return error_response(
        message=message,
        http_status=HTTPStatus.NOT_FOUND,
        error_code='RESOURCE_NOT_FOUND',
        details=details if details else None
    )


def validation_error_response(
    message: str = "Validation failed",
    validation_errors: Optional[Dict[str, List[str]]] = None
) -> Response:
    """
    Create a validation error response.
    
    Usage:
        return validation_error_response(
            message='Invalid input data',
            validation_errors={
                'email': ['Invalid email format'],
                'age': ['Must be at least 18']
            }
        )
    """
    errors = []
    if validation_errors:
        for field, messages in validation_errors.items():
            for msg in messages:
                errors.append({
                    'field': field,
                    'message': msg
                })
    
    return error_response(
        message=message,
        http_status=HTTPStatus.UNPROCESSABLE_ENTITY,
        error_code='VALIDATION_ERROR',
        errors=errors if errors else None
    )


def paginated_response(
    data: List[Any],
    page: int,
    per_page: int,
    total: int,
    message: str = "Data retrieved successfully"
) -> Response:
    """
    Create a paginated response.
    
    Usage:
        return paginated_response(
            data=[user.to_dict() for user in users],
            page=1,
            per_page=20,
            total=100
        )
    """
    total_pages = (total + per_page - 1) // per_page
    
    meta = {
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }
    
    return success_response(
        data=data,
        message=message,
        meta=meta
    )


def handle_api_errors(default_message: str = "An error occurred"):
    """
    Decorator for consistent error handling in API endpoints.
    
    Usage:
        @app.route('/api/users/<int:user_id>')
        @handle_api_errors(default_message="Failed to get user")
        def get_user(user_id):
            user = User.query.get_or_404(user_id)
            return success_response(data=user.to_dict())
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                logger.warning(f"Validation error in {func.__name__}: {e}")
                return validation_error_response(str(e))
            except PermissionError as e:
                logger.warning(f"Permission denied in {func.__name__}: {e}")
                return error_response(
                    message="Permission denied",
                    http_status=HTTPStatus.FORBIDDEN,
                    error_code='PERMISSION_DENIED'
                )
            except FileNotFoundError as e:
                logger.warning(f"Resource not found in {func.__name__}: {e}")
                return not_found_response(str(e))
            except Exception as e:
                logger.error(f"Unhandled error in {func.__name__}: {e}", exc_info=True)
                return error_response(
                    message=default_message,
                    details={'error': str(e)} if logger.isEnabledFor(logging.DEBUG) else None
                )
        return wrapper
    return decorator


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime for API responses"""
    return dt.isoformat() if dt else None


def format_model_response(model_instance, fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Format a SQLAlchemy model instance for API response.
    
    Args:
        model_instance: SQLAlchemy model instance
        fields: List of fields to include (None for all)
    
    Returns:
        Dictionary representation of the model
    
    Usage:
        user_data = format_model_response(user, fields=['id', 'email', 'name'])
    """
    if hasattr(model_instance, 'to_dict'):
        data = model_instance.to_dict()
    else:
        # Basic serialization for models without to_dict
        data = {}
        for column in model_instance.__table__.columns:
            value = getattr(model_instance, column.name)
            if isinstance(value, datetime):
                value = format_datetime(value)
            data[column.name] = value
    
    if fields:
        data = {k: v for k, v in data.items() if k in fields}
    
    return data