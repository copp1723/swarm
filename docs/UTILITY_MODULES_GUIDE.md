# New Utility Modules Documentation

## Overview

Five new utility modules have been created to reduce code duplication and improve maintainability in the MCP Agent project. All utilities follow the existing coding patterns and include comprehensive error handling, type hints, and logging.

## 1. File I/O Utility (`utils/file_io.py`)

Provides safe, consistent file operations with proper error handling.

### Key Features:
- Atomic write operations to prevent partial writes
- Safe JSON/YAML reading with default values
- Automatic directory creation
- Comprehensive error handling and logging

### Example Usage:
```python
from utils import safe_read_json, safe_write_json, ensure_directory_exists

# Read JSON with fallback
config = safe_read_json('config.json', default_value={})

# Write JSON atomically
success = safe_write_json('output.json', {'data': 'value'})

# Ensure directory exists
ensure_directory_exists('data/uploads')
```

## 2. Async Error Handler (`utils/async_error_handler.py`)

Provides consistent error handling for async Flask routes.

### Key Features:
- Decorator for async route error handling
- Request ID tracking for debugging
- Automatic timeout and cancellation handling
- Retry mechanism with exponential backoff

### Example Usage:
```python
from utils import handle_async_route_errors, AsyncRouteHandler

# Using decorator
@app.route('/api/async-endpoint')
@handle_async_route_errors
async def async_endpoint():
    result = await some_async_operation()
    return {'data': result}

# Using class-based handler
handler = AsyncRouteHandler()

@app.route('/api/users/<int:user_id>')
@handler.handle_async
async def get_user(user_id):
    user = await fetch_user(user_id)
    return {'user': user}
```

## 3. Batch Operations (`utils/batch_operations.py`)

Handles database batch operations efficiently with proper error handling and rollback.

### Key Features:
- Batch insert/update/delete operations
- Automatic transaction management
- Chunked query processing for memory efficiency
- Progress logging for large operations
- Async support with concurrency control

### Example Usage:
```python
from utils import batch_insert, batch_update, BatchProcessor

# Batch insert
result = await batch_insert(
    db_session,
    User,
    records=[
        {'name': 'User1', 'email': 'user1@example.com'},
        {'name': 'User2', 'email': 'user2@example.com'}
    ],
    batch_size=1000
)

# Batch update
updates = [
    {'id': 1, 'status': 'active'},
    {'id': 2, 'status': 'inactive'}
]
result = await batch_update(db_session, User, updates)

# Process items with concurrency control
processor = BatchProcessor(batch_size=100)
results = await processor.process_async(
    items,
    process_func,
    max_concurrent=10
)
```

## 4. Configuration Validator (`utils/config_validator.py`)

Validates configuration files and environment variables at startup.

### Key Features:
- JSON Schema validation
- Environment variable checking
- API credential validation
- Default config generation from schema
- Support for JSON and YAML files

### Example Usage:
```python
from utils import load_and_validate_config, check_required_env_variables

# Load and validate config
config = load_and_validate_config(
    'config.yaml',
    'schemas/config_schema.json',
    required_env_vars=['DATABASE_URL', 'SECRET_KEY']
)

# Check environment variables
valid, missing = check_required_env_variables([
    'OPENAI_API_KEY',
    'REDIS_URL'
])
```

## 5. Error Catalog (`utils/error_catalog.py`)

Centralizes error codes and messages for consistent API responses.

### Key Features:
- Comprehensive error code constants
- Standardized error response format
- HTTP status code mapping
- Error builder for complex responses
- Support for field-level errors

### Example Usage:
```python
from utils import ErrorCodes, format_error_response, ErrorBuilder

# Simple error response
error = format_error_response(
    ErrorCodes.NOT_FOUND,
    resource='agent'
)

# Complex error with field validation
error = (ErrorBuilder()
    .with_code(ErrorCodes.VALIDATION_ERROR)
    .with_field_errors({
        'email': 'Invalid format',
        'age': 'Must be positive'
    })
    .build())
```

## Integration Guidelines

### Import Pattern
All utilities can be imported directly from the `utils` package:
```python
from utils import safe_read_json, batch_insert, ErrorCodes
```

### Error Handling Pattern
All utilities follow consistent error handling:
- Operations return success/failure indicators
- Errors are logged with appropriate levels
- Exceptions are caught and handled gracefully

### Async Support
Utilities with async support use modern Python async/await patterns:
- Async functions are clearly marked with `async def`
- Support for concurrent operations with semaphores
- Proper timeout handling

## Best Practices

1. **Always handle errors**: Check return values and handle failures appropriately
2. **Use type hints**: All functions include comprehensive type annotations
3. **Configure logging**: Utilities use the existing logging configuration
4. **Consider performance**: Use batch operations for large datasets
5. **Validate early**: Use config validation at startup to catch issues early

## Migration Guide

To migrate existing code to use these utilities:

1. **File Operations**: Replace direct `open()` calls with `safe_read_json/safe_write_json`
2. **Error Responses**: Replace custom error formatting with `format_error_response`
3. **Batch DB Operations**: Replace loops with `batch_insert/batch_update`
4. **Config Loading**: Replace manual config parsing with `load_and_validate_config`
5. **Async Routes**: Add `@handle_async_route_errors` to async endpoints

## Testing

Each utility module should have corresponding tests in `/tests/utils/`:
- `test_file_io.py`
- `test_async_error_handler.py`
- `test_batch_operations.py`
- `test_config_validator.py`
- `test_error_catalog.py`

## Performance Considerations

- **File I/O**: Uses atomic writes to prevent corruption
- **Batch Operations**: Default batch sizes optimized for PostgreSQL
- **Async Operations**: Includes concurrency limits to prevent overload
- **Config Validation**: Validates once at startup, not per request