"""Centralized error catalog for consistent API responses"""
import logging
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCodes:
    """Error code constants for consistent error handling"""
    
    # Client errors (4xx)
    INVALID_REQUEST = "INVALID_REQUEST"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    GONE = "GONE"
    UNPROCESSABLE_ENTITY = "UNPROCESSABLE_ENTITY"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    
    # Business logic errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INSUFFICIENT_RESOURCES = "INSUFFICIENT_RESOURCES"
    OPERATION_NOT_PERMITTED = "OPERATION_NOT_PERMITTED"
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    
    # Authentication/Authorization errors
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    INSUFFICIENT_PRIVILEGES = "INSUFFICIENT_PRIVILEGES"
    
    # Agent-specific errors
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    AGENT_UNAVAILABLE = "AGENT_UNAVAILABLE"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    AGENT_ERROR = "AGENT_ERROR"
    WORKFLOW_ERROR = "WORKFLOW_ERROR"
    TASK_FAILED = "TASK_FAILED"
    
    # File/Resource errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    STORAGE_ERROR = "STORAGE_ERROR"
    
    # WebSocket errors
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    CONNECTION_CLOSED = "CONNECTION_CLOSED"
    INVALID_MESSAGE_FORMAT = "INVALID_MESSAGE_FORMAT"


# Error message templates
ERROR_MESSAGES = {
    # Client errors
    ErrorCodes.INVALID_REQUEST: "Invalid request: {details}",
    ErrorCodes.MISSING_PARAMETER: "Missing required parameter: {parameter}",
    ErrorCodes.INVALID_PARAMETER: "Invalid parameter '{parameter}': {reason}",
    ErrorCodes.UNAUTHORIZED: "Authentication required",
    ErrorCodes.FORBIDDEN: "Access forbidden: {reason}",
    ErrorCodes.NOT_FOUND: "Resource not found: {resource}",
    ErrorCodes.METHOD_NOT_ALLOWED: "Method {method} not allowed for this endpoint",
    ErrorCodes.CONFLICT: "Conflict: {details}",
    ErrorCodes.GONE: "Resource no longer available: {resource}",
    ErrorCodes.UNPROCESSABLE_ENTITY: "Cannot process request: {reason}",
    ErrorCodes.TOO_MANY_REQUESTS: "Too many requests. Please try again later",
    ErrorCodes.RATE_LIMITED: "Rate limit exceeded. Try again in {seconds} seconds",
    
    # Server errors
    ErrorCodes.INTERNAL_ERROR: "An internal error occurred",
    ErrorCodes.SERVICE_UNAVAILABLE: "Service temporarily unavailable",
    ErrorCodes.DATABASE_ERROR: "Database operation failed",
    ErrorCodes.EXTERNAL_API_ERROR: "External API error: {service}",
    ErrorCodes.CONFIGURATION_ERROR: "Configuration error: {details}",
    ErrorCodes.TIMEOUT_ERROR: "Operation timed out after {seconds} seconds",
    
    # Business logic errors
    ErrorCodes.VALIDATION_ERROR: "Validation failed: {details}",
    ErrorCodes.BUSINESS_RULE_VIOLATION: "Business rule violation: {rule}",
    ErrorCodes.INSUFFICIENT_RESOURCES: "Insufficient resources: {resource}",
    ErrorCodes.OPERATION_NOT_PERMITTED: "Operation not permitted: {operation}",
    ErrorCodes.DUPLICATE_ENTRY: "Duplicate entry: {field} already exists",
    
    # Authentication/Authorization errors
    ErrorCodes.INVALID_CREDENTIALS: "Invalid credentials provided",
    ErrorCodes.TOKEN_EXPIRED: "Authentication token has expired",
    ErrorCodes.TOKEN_INVALID: "Invalid authentication token",
    ErrorCodes.INSUFFICIENT_PRIVILEGES: "Insufficient privileges for this operation",
    
    # Agent-specific errors
    ErrorCodes.AGENT_NOT_FOUND: "Agent not found: {agent_id}",
    ErrorCodes.AGENT_UNAVAILABLE: "Agent {agent_id} is currently unavailable",
    ErrorCodes.AGENT_TIMEOUT: "Agent {agent_id} response timeout",
    ErrorCodes.AGENT_ERROR: "Agent error: {details}",
    ErrorCodes.WORKFLOW_ERROR: "Workflow execution error: {workflow}",
    ErrorCodes.TASK_FAILED: "Task execution failed: {task_id}",
    
    # File/Resource errors
    ErrorCodes.FILE_NOT_FOUND: "File not found: {filename}",
    ErrorCodes.FILE_TOO_LARGE: "File too large. Maximum size: {max_size}",
    ErrorCodes.INVALID_FILE_TYPE: "Invalid file type. Allowed types: {allowed_types}",
    ErrorCodes.STORAGE_ERROR: "Storage operation failed: {operation}",
    
    # WebSocket errors
    ErrorCodes.WEBSOCKET_ERROR: "WebSocket error: {details}",
    ErrorCodes.CONNECTION_CLOSED: "Connection closed: {reason}",
    ErrorCodes.INVALID_MESSAGE_FORMAT: "Invalid message format: {details}"
}


# HTTP status code mapping
ERROR_STATUS_CODES = {
    # 400 Bad Request
    ErrorCodes.INVALID_REQUEST: 400,
    ErrorCodes.MISSING_PARAMETER: 400,
    ErrorCodes.INVALID_PARAMETER: 400,
    ErrorCodes.INVALID_MESSAGE_FORMAT: 400,
    
    # 401 Unauthorized
    ErrorCodes.UNAUTHORIZED: 401,
    ErrorCodes.INVALID_CREDENTIALS: 401,
    ErrorCodes.TOKEN_EXPIRED: 401,
    ErrorCodes.TOKEN_INVALID: 401,
    
    # 403 Forbidden
    ErrorCodes.FORBIDDEN: 403,
    ErrorCodes.INSUFFICIENT_PRIVILEGES: 403,
    ErrorCodes.OPERATION_NOT_PERMITTED: 403,
    
    # 404 Not Found
    ErrorCodes.NOT_FOUND: 404,
    ErrorCodes.AGENT_NOT_FOUND: 404,
    ErrorCodes.FILE_NOT_FOUND: 404,
    
    # 405 Method Not Allowed
    ErrorCodes.METHOD_NOT_ALLOWED: 405,
    
    # 409 Conflict
    ErrorCodes.CONFLICT: 409,
    ErrorCodes.DUPLICATE_ENTRY: 409,
    
    # 410 Gone
    ErrorCodes.GONE: 410,
    
    # 422 Unprocessable Entity
    ErrorCodes.UNPROCESSABLE_ENTITY: 422,
    ErrorCodes.VALIDATION_ERROR: 422,
    ErrorCodes.BUSINESS_RULE_VIOLATION: 422,
    
    # 429 Too Many Requests
    ErrorCodes.TOO_MANY_REQUESTS: 429,
    ErrorCodes.RATE_LIMITED: 429,
    
    # 500 Internal Server Error
    ErrorCodes.INTERNAL_ERROR: 500,
    ErrorCodes.DATABASE_ERROR: 500,
    ErrorCodes.CONFIGURATION_ERROR: 500,
    ErrorCodes.STORAGE_ERROR: 500,
    
    # 502 Bad Gateway
    ErrorCodes.EXTERNAL_API_ERROR: 502,
    
    # 503 Service Unavailable
    ErrorCodes.SERVICE_UNAVAILABLE: 503,
    ErrorCodes.AGENT_UNAVAILABLE: 503,
    ErrorCodes.INSUFFICIENT_RESOURCES: 503,
    
    # 504 Gateway Timeout
    ErrorCodes.TIMEOUT_ERROR: 504,
    ErrorCodes.AGENT_TIMEOUT: 504,
}


def get_error_message(error_code: str, **kwargs) -> str:
    """
    Get formatted error message for a given error code.
    
    Args:
        error_code: One of the ErrorCodes constants
        **kwargs: Parameters to format the message
        
    Returns:
        Formatted error message
        
    Example:
        message = get_error_message(
            ErrorCodes.MISSING_PARAMETER,
            parameter='user_id'
        )
    """
    template = ERROR_MESSAGES.get(error_code, "Unknown error occurred")
    
    try:
        # Format message with provided parameters
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing parameter for error message {error_code}: {e}")
        return template
    except Exception as e:
        logger.error(f"Error formatting message for {error_code}: {e}")
        return template


def format_error_response(
    error_code: str,
    status_code: Optional[int] = None,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict:
    """
    Create standardized error response format.
    
    Args:
        error_code: One of the ErrorCodes constants
        status_code: HTTP status code (auto-determined if not provided)
        request_id: Request tracking ID
        details: Additional error details
        **kwargs: Parameters for error message formatting
        
    Returns:
        Dict with error, message, code, and optional details
        
    Example:
        response = format_error_response(
            ErrorCodes.NOT_FOUND,
            resource='user',
            request_id='123-456'
        )
    """
    # Determine status code if not provided
    if status_code is None:
        status_code = ERROR_STATUS_CODES.get(error_code, 500)
    
    # Get formatted error message
    message = get_error_message(error_code, **kwargs)
    
    # Build response
    response = {
        'success': False,
        'error': {
            'code': error_code,
            'message': message,
            'status_code': status_code
        }
    }
    
    # Add optional fields
    if request_id:
        response['request_id'] = request_id
        
    if details:
        response['error']['details'] = details
        
    # Add timestamp
    from datetime import datetime
    response['timestamp'] = datetime.utcnow().isoformat()
    
    return response


def get_status_code(error_code: str) -> int:
    """
    Get HTTP status code for an error code.
    
    Args:
        error_code: One of the ErrorCodes constants
        
    Returns:
        HTTP status code (defaults to 500 if not found)
    """
    return ERROR_STATUS_CODES.get(error_code, 500)


def is_client_error(error_code: str) -> bool:
    """
    Check if an error code represents a client error (4xx).
    
    Args:
        error_code: Error code to check
        
    Returns:
        True if client error, False otherwise
    """
    status_code = get_status_code(error_code)
    return 400 <= status_code < 500


def is_server_error(error_code: str) -> bool:
    """
    Check if an error code represents a server error (5xx).
    
    Args:
        error_code: Error code to check
        
    Returns:
        True if server error, False otherwise
    """
    status_code = get_status_code(error_code)
    return 500 <= status_code < 600


class ErrorBuilder:
    """
    Builder class for constructing complex error responses.
    
    Example:
        error = (ErrorBuilder()
            .with_code(ErrorCodes.VALIDATION_ERROR)
            .with_message("Invalid user data")
            .with_field_errors({
                'email': 'Invalid email format',
                'age': 'Must be at least 18'
            })
            .build())
    """
    
    def __init__(self):
        self._error_code = ErrorCodes.INTERNAL_ERROR
        self._status_code = None
        self._message = None
        self._details = {}
        self._field_errors = {}
        self._request_id = None
        
    def with_code(self, error_code: str) -> 'ErrorBuilder':
        """Set the error code."""
        self._error_code = error_code
        return self
        
    def with_status(self, status_code: int) -> 'ErrorBuilder':
        """Set custom HTTP status code."""
        self._status_code = status_code
        return self
        
    def with_message(self, message: str) -> 'ErrorBuilder':
        """Set custom error message."""
        self._message = message
        return self
        
    def with_detail(self, key: str, value: Any) -> 'ErrorBuilder':
        """Add a detail field."""
        self._details[key] = value
        return self
        
    def with_field_error(self, field: str, error: str) -> 'ErrorBuilder':
        """Add a field-specific error."""
        self._field_errors[field] = error
        return self
        
    def with_field_errors(self, field_errors: Dict[str, str]) -> 'ErrorBuilder':
        """Add multiple field errors."""
        self._field_errors.update(field_errors)
        return self
        
    def with_request_id(self, request_id: str) -> 'ErrorBuilder':
        """Set request ID."""
        self._request_id = request_id
        return self
        
    def build(self) -> Dict:
        """Build the error response."""
        # Prepare details
        details = self._details.copy()
        if self._field_errors:
            details['field_errors'] = self._field_errors
            
        # Get base response
        response = format_error_response(
            self._error_code,
            status_code=self._status_code,
            request_id=self._request_id,
            details=details if details else None
        )
        
        # Override message if custom one provided
        if self._message:
            response['error']['message'] = self._message
            
        return response


# Internationalization support (future enhancement)
class ErrorMessages:
    """
    Class for managing error messages with potential i18n support.
    """
    
    def __init__(self, locale: str = 'en'):
        self.locale = locale
        self._messages = ERROR_MESSAGES.copy()
        
    def get(self, error_code: str, **kwargs) -> str:
        """Get localized error message."""
        # For now, just use default messages
        # In future, could load from locale-specific files
        return get_error_message(error_code, **kwargs)
        
    def set_locale(self, locale: str):
        """Change the locale for messages."""
        self.locale = locale
        # Future: reload messages for new locale