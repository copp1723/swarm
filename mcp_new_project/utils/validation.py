"""Request validation utilities"""
from functools import wraps
from flask import request, jsonify
from typing import List, Optional, Callable, Any


def validate_request_data(required_fields: Optional[List[str]] = None, 
                         allow_empty_data: bool = False) -> Callable:
    """
    Decorator to validate request data with common patterns.
    
    Args:
        required_fields: List of required field names in the JSON data
        allow_empty_data: Whether to allow empty/missing JSON data
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get JSON data
            data = request.get_json()
            
            # Check if data is provided when required
            if not allow_empty_data and not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # If data is None but empty data is allowed, set to empty dict
            if data is None and allow_empty_data:
                data = {}
            
            # Check required fields
            if required_fields and data is not None:
                for field in required_fields:
                    if field not in data:
                        return jsonify({'error': f'{field.capitalize()} is required'}), 400
                    
                    # Check for empty string values on required fields
                    value = data.get(field)
                    if isinstance(value, str) and not value.strip():
                        return jsonify({'error': f'{field.capitalize()} cannot be empty'}), 400
            
            # Add validated data to kwargs for the route function
            kwargs['validated_data'] = data
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_message_required(func: Callable) -> Callable:
    """
    Convenience decorator for routes that require a 'message' field.
    Equivalent to @validate_request_data(required_fields=['message'])
    """
    return validate_request_data(required_fields=['message'])(func)


def validate_json_data(func: Callable) -> Callable:
    """
    Convenience decorator for routes that just need JSON data validation.
    Equivalent to @validate_request_data()
    """
    return validate_request_data()(func)
