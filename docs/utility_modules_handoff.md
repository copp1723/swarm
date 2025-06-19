# Utility Modules Creation Handoff Document

## Overview
This document provides specifications for creating new utility modules to reduce code duplication and improve maintainability in the MCP Agent project. These utilities should be created in the `/utils/` directory.

## Context
The codebase has several repeated patterns that need to be abstracted into reusable utilities. Existing utilities like `response_handler.py`, `validation.py`, and `database.py` serve as good examples of the coding style and patterns to follow.

## Utility Modules to Create

### 1. **File I/O Utility** (`/utils/file_io.py`)

**Purpose**: Provide safe, consistent file operations with proper error handling.

**Required Functions**:

```python
def safe_read_json(file_path: str, default_value: Any = None) -> Any:
    """
    Safely read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file
        default_value: Value to return if file doesn't exist or parsing fails
        
    Returns:
        Parsed JSON data or default_value
        
    Example:
        config = safe_read_json('config.json', default_value={})
    """
    pass

def safe_write_json(file_path: str, data: Any, indent: int = 2) -> bool:
    """
    Safely write data to a JSON file with atomic write operation.
    
    Args:
        file_path: Path to write the JSON file
        data: Data to serialize to JSON
        indent: JSON indentation level
        
    Returns:
        True if successful, False otherwise
    """
    pass

def safe_read_yaml(file_path: str, default_value: Any = None) -> Any:
    """
    Safely read and parse a YAML file.
    Similar to safe_read_json but for YAML files.
    """
    pass

def safe_write_yaml(file_path: str, data: Any) -> bool:
    """
    Safely write data to a YAML file.
    Similar to safe_write_json but for YAML files.
    """
    pass

def atomic_write(file_path: str, content: str) -> bool:
    """
    Perform atomic file write to prevent partial writes.
    Should write to temp file first, then rename.
    """
    pass

def ensure_directory_exists(directory_path: str) -> bool:
    """
    Create directory and all parent directories if they don't exist.
    """
    pass
```

**Implementation Notes**:
- Use context managers for file operations
- Implement atomic writes using temporary files and rename
- Log all errors using the existing `logging_config.get_logger()`
- Handle common exceptions: FileNotFoundError, PermissionError, JSONDecodeError

### 2. **Async Error Handler** (`/utils/async_error_handler.py`)

**Purpose**: Provide consistent error handling for async routes, similar to the existing `response_handler.py` but for async functions.

**Required Components**:

```python
def handle_async_route_errors(func):
    """
    Decorator for handling errors in async Flask routes.
    
    Example:
        @app.route('/api/async-endpoint')
        @handle_async_route_errors
        async def async_endpoint():
            return {'data': 'success'}
    """
    pass

async def async_error_response(error: Exception, status_code: int = 500) -> Tuple[Dict, int]:
    """
    Create standardized error response for async routes.
    """
    pass

class AsyncRouteHandler:
    """
    Class-based async route handler with error handling.
    """
    pass
```

**Implementation Notes**:
- Follow the pattern in `response_handler.py` but make it async-compatible
- Use `functools.wraps` to preserve function metadata
- Include request ID tracking for debugging
- Log errors with full stack traces

### 3. **Batch Operations Utility** (`/utils/batch_operations.py`)

**Purpose**: Handle database batch operations efficiently with proper error handling and rollback.

**Required Functions**:

```python
async def batch_insert(db_session, model_class, records: List[Dict], batch_size: int = 1000):
    """
    Insert multiple records in batches.
    
    Args:
        db_session: SQLAlchemy session
        model_class: SQLAlchemy model class
        records: List of dictionaries containing record data
        batch_size: Number of records per batch
        
    Returns:
        Dict with success count and failed records
    """
    pass

async def batch_update(db_session, model_class, updates: List[Dict], batch_size: int = 500):
    """
    Update multiple records in batches.
    
    Args:
        updates: List of dicts with 'id' and fields to update
    """
    pass

async def batch_delete(db_session, model_class, ids: List[Any], batch_size: int = 1000):
    """
    Delete multiple records by ID in batches.
    """
    pass

@contextmanager
def transaction_with_rollback(db_session):
    """
    Context manager for database transactions with automatic rollback on error.
    """
    pass

def chunked_query(query, chunk_size: int = 1000):
    """
    Generator that yields query results in chunks to avoid memory issues.
    """
    pass
```

**Implementation Notes**:
- Use SQLAlchemy bulk operations where possible
- Implement progress logging for long operations
- Handle database-specific exceptions
- Provide rollback capability for failed batches

### 4. **Configuration Validator** (`/utils/config_validator.py`)

**Purpose**: Validate configuration files and environment variables at startup.

**Required Functions**:

```python
def validate_config_schema(config: Dict, schema: Dict) -> Tuple[bool, List[str]]:
    """
    Validate configuration against a JSON schema.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    pass

def check_required_env_variables(required_vars: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if all required environment variables are set.
    
    Returns:
        Tuple of (all_present, missing_vars)
    """
    pass

def validate_api_credentials(credentials: Dict) -> Tuple[bool, Dict[str, str]]:
    """
    Validate API credentials format and basic connectivity.
    
    Returns:
        Tuple of (is_valid, service_status_dict)
    """
    pass

def load_and_validate_config(config_path: str, schema_path: str) -> Dict:
    """
    Load configuration file and validate against schema.
    
    Raises:
        ConfigValidationError if validation fails
    """
    pass

class ConfigValidationError(Exception):
    """Custom exception for configuration validation errors."""
    pass
```

**Implementation Notes**:
- Use `jsonschema` library for schema validation
- Provide clear error messages indicating what's missing/invalid
- Support both JSON and YAML configuration files
- Log validation results

### 5. **Error Catalog** (`/utils/error_catalog.py`)

**Purpose**: Centralize error codes and messages for consistent API responses.

**Required Components**:

```python
# Error code constants
class ErrorCodes:
    # Client errors (4xx)
    INVALID_REQUEST = "INVALID_REQUEST"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Server errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"

# Error message templates
ERROR_MESSAGES = {
    ErrorCodes.INVALID_REQUEST: "Invalid request: {details}",
    ErrorCodes.MISSING_PARAMETER: "Missing required parameter: {parameter}",
    ErrorCodes.UNAUTHORIZED: "Authentication required",
    ErrorCodes.FORBIDDEN: "Access forbidden: {reason}",
    ErrorCodes.NOT_FOUND: "Resource not found: {resource}",
    ErrorCodes.RATE_LIMITED: "Rate limit exceeded. Try again in {seconds} seconds",
    ErrorCodes.INTERNAL_ERROR: "An internal error occurred",
    ErrorCodes.SERVICE_UNAVAILABLE: "Service temporarily unavailable",
    ErrorCodes.DATABASE_ERROR: "Database operation failed",
    ErrorCodes.EXTERNAL_API_ERROR: "External API error: {service}"
}

def get_error_message(error_code: str, **kwargs) -> str:
    """
    Get formatted error message for a given error code.
    
    Args:
        error_code: One of the ErrorCodes constants
        **kwargs: Parameters to format the message
        
    Returns:
        Formatted error message
    """
    pass

def format_error_response(error_code: str, status_code: int, **kwargs) -> Dict:
    """
    Create standardized error response format.
    
    Returns:
        Dict with error, message, code, and optional details
    """
    pass
```

**Implementation Notes**:
- Ensure error codes are unique and descriptive
- Support internationalization (i18n) in the future
- Include request ID in error responses for tracking
- Follow REST API error response best practices

## Integration Guidelines

1. **Import Pattern**: All utilities should be importable from `utils` package:
   ```python
   from utils.file_io import safe_read_json
   from utils.error_catalog import ErrorCodes, get_error_message
   ```

2. **Logging**: Use the existing logging configuration:
   ```python
   from utils.logging_config import get_logger
   logger = get_logger(__name__)
   ```

3. **Testing**: Create corresponding test files in `/tests/utils/`:
   - `test_file_io.py`
   - `test_async_error_handler.py`
   - `test_batch_operations.py`
   - `test_config_validator.py`
   - `test_error_catalog.py`

4. **Documentation**: Include docstrings with examples for all public functions

5. **Dependencies**: Add any new dependencies to `requirements.txt`:
   - `jsonschema` for config validation
   - `pyyaml` for YAML support (already included)

## Existing Patterns to Follow

Look at these existing utilities for coding style and patterns:
- `/utils/response_handler.py` - Error handling patterns
- `/utils/validation.py` - Decorator patterns
- `/utils/database.py` - Database context managers
- `/utils/logging_config.py` - Logging setup

## Success Criteria

1. All functions have comprehensive error handling
2. All functions are properly typed with type hints
3. All modules have 80%+ test coverage
4. Documentation includes usage examples
5. Integration doesn't break existing functionality
6. Performance is considered (especially for batch operations)

## Questions to Consider

1. Should file I/O operations support S3/cloud storage in addition to local files?
2. Should batch operations support async and sync database sessions?
3. Should error messages support multiple languages?
4. What should be the default batch sizes for optimal performance?

## Delivery

Please create these utilities with:
1. Full implementation of all specified functions
2. Comprehensive docstrings
3. Type hints for all parameters and returns
4. Basic unit tests
5. Integration examples

The utilities should be production-ready and follow the existing code style in the project.