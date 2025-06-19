"""Security utilities for file path validation and other security checks"""
import os
from typing import Tuple, Optional
from flask import jsonify


def secure_path(path: str, base_directory: str = '.') -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate file path to prevent directory traversal attacks.
    
    Args:
        path: The file path to validate
        base_directory: The base directory to restrict access to (default: current directory)
    
    Returns:
        Tuple of (is_valid, absolute_path, error_message)
        - is_valid: True if path is safe, False otherwise
        - absolute_path: The absolute path if valid, None if invalid
        - error_message: Error message if invalid, None if valid
    """
    try:
        # Get absolute paths
        abs_path = os.path.abspath(path)
        abs_base = os.path.abspath(base_directory)
        
        # Check if the path is within the allowed base directory
        if not abs_path.startswith(abs_base):
            return False, None, 'Invalid path: Access outside allowed directory'
        
        return True, abs_path, None
        
    except Exception as e:
        return False, None, f'Path validation error: {str(e)}'


def validate_file_path(path: str, base_directory: str = '.', 
                      must_exist: bool = True, must_be_file: bool = False) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Comprehensive file path validation with security checks.
    
    Args:
        path: The file path to validate
        base_directory: The base directory to restrict access to
        must_exist: Whether the path must exist
        must_be_file: Whether the path must be a file (not directory)
    
    Returns:
        Tuple of (is_valid, absolute_path, error_response)
        - is_valid: True if all validations pass
        - absolute_path: The absolute path if valid
        - error_response: Flask JSON error response if invalid
    """
    # Security check
    is_secure, abs_path, security_error = secure_path(path, base_directory)
    if not is_secure:
        return False, None, jsonify({'error': security_error}), 403
    
    # Existence check
    if must_exist and not os.path.exists(abs_path):
        if must_be_file:
            return False, None, jsonify({'error': 'File not found'}), 404
        else:
            return False, None, jsonify({'error': 'Path not found'}), 404
    
    # File type check
    if must_be_file and os.path.exists(abs_path) and not os.path.isfile(abs_path):
        return False, None, jsonify({'error': 'Not a file'}), 400
    
    return True, abs_path, None


def secure_filename_check(filename: str, allowed_extensions: Optional[set] = None) -> Tuple[bool, Optional[str]]:
    """
    Check if filename is secure and has allowed extension.
    
    Args:
        filename: The filename to check
        allowed_extensions: Set of allowed file extensions (e.g., {'txt', 'pdf'})
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename or filename == '':
        return False, 'No filename provided'
    
    # Check for dangerous characters
    dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        if char in filename:
            return False, f'Filename contains invalid character: {char}'
    
    # Check extension if restrictions are provided
    if allowed_extensions:
        if '.' not in filename:
            return False, 'File must have an extension'
        
        extension = filename.rsplit('.', 1)[1].lower()
        if extension not in allowed_extensions:
            return False, f'File type not allowed. Allowed: {", ".join(allowed_extensions)}'
    
    return True, None
