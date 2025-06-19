# Code Refactoring Guide: Eliminating Duplicate Patterns

This guide helps you refactor the codebase to use the new unified utilities for database operations, error handling, API responses, and logging.

## 1. Database Operations Refactoring

### Old Pattern (Found in multiple files):
```python
# In services/database_task_storage.py, routes/agents.py, etc.
try:
    # Database operation
    db.session.add(obj)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    logger.error(f"Database error: {e}")
    raise
```

### New Pattern:
```python
from utils.db_context import db_session, with_db_session, get_or_create

# Using context manager
with db_session():
    task = Task(name="example")
    db.session.add(task)
    # Auto-commits on success, rolls back on error

# Using decorator
@with_db_session
def create_task(name: str) -> Task:
    task = Task(name=name)
    db.session.add(task)
    return task

# Using get_or_create
user, created = get_or_create(
    User,
    defaults={'is_active': True},
    email='user@example.com'
)
```

## 2. Error Handling Refactoring

### Old Pattern (Found in routes/*.py):
```python
try:
    # Some operation
    result = process_data()
    return jsonify({'success': True, 'data': result})
except Exception as e:
    logger.error(f"Error: {e}")
    return jsonify({'error': str(e)}), 500
```

### New Pattern:
```python
from utils.error_handling import api_error_handler, ApplicationError, ResourceNotFoundError
from utils.api_response import success_response, error_response

@app.route('/api/resource/<int:id>')
@api_error_handler()
def get_resource(id):
    resource = Resource.query.get(id)
    if not resource:
        raise ResourceNotFoundError('Resource', id)
    return success_response(data=resource.to_dict())
```

## 3. API Response Formatting Refactoring

### Old Pattern (Inconsistent across routes):
```python
# Different response formats in different files
return jsonify({'success': True, 'profiles': profiles})  # routes/agents.py
return jsonify({'error': 'Invalid input'}), 400  # routes/tasks.py
return {'data': results}, 200  # routes/workflows.py
```

### New Pattern:
```python
from utils.api_response import (
    success_response, error_response, created_response,
    not_found_response, paginated_response, handle_api_errors
)

# Success response
return success_response(
    data={'users': users},
    message='Users retrieved successfully'
)

# Error response
return error_response(
    message='Invalid email format',
    http_status=400,
    error_code='VALIDATION_ERROR'
)

# Created response (201)
return created_response(
    data={'id': user.id},
    message='User created',
    location=f'/api/users/{user.id}'
)

# With decorator for automatic error handling
@handle_api_errors(default_message="Failed to process request")
def process_endpoint():
    # Your logic here
    return {'result': 'success'}
```

## 4. Logging Setup Refactoring

### Old Pattern (Duplicated in many files):
```python
import logging
logger = logging.getLogger(__name__)

# Or with loguru in some files
from loguru import logger
```

### New Pattern:
```python
from utils.unified_logging import get_logger, log_function_call, LogContext

# Simple module logger
logger = get_logger(__name__)

# With function call logging
@log_function_call()
def process_data(data):
    return transform(data)

# With context
with LogContext(logger, user_id=123, request_id='abc'):
    logger.info("Processing user request")
```

## Migration Steps

### Step 1: Update Imports
```python
# Add to the top of your files
from utils.db_context import db_session, with_db_session
from utils.error_handling import api_error_handler, ApplicationError
from utils.api_response import success_response, error_response
from utils.unified_logging import get_logger
```

### Step 2: Replace Database Patterns
Search for patterns like:
- `db.session.commit()`
- `db.session.rollback()`
- `try:...except:` blocks around database operations

Replace with `db_session()` context manager or decorators.

### Step 3: Standardize Error Handling
Search for:
- `except Exception as e:`
- `return jsonify({'error':...})`
- Custom error handling in routes

Replace with `@api_error_handler()` decorator and structured exceptions.

### Step 4: Unify API Responses
Search for:
- `jsonify({'success': True...})`
- `jsonify({'error':...})`
- Direct dictionary returns

Replace with appropriate response functions.

### Step 5: Consolidate Logging
Search for:
- `logging.getLogger(__name__)`
- `logger = logging.Logger(...)`
- Different logging configurations

Replace with `get_logger(__name__)`.

## Example: Refactoring a Route

### Before:
```python
@agents_bp.route('/profiles', methods=['GET'])
def get_agent_profiles():
    try:
        profiles = []
        for role, profile in AGENT_PROFILES.items():
            profiles.append({...})
        
        return jsonify({
            'success': True,
            'profiles': profiles,
            'total': len(profiles)
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500
```

### After:
```python
from utils.api_response import success_response, handle_api_errors
from utils.unified_logging import get_logger

logger = get_logger(__name__)

@agents_bp.route('/profiles', methods=['GET'])
@handle_api_errors(default_message="Failed to get agent profiles")
def get_agent_profiles():
    profiles = []
    for role, profile in AGENT_PROFILES.items():
        profiles.append({...})
    
    return success_response(
        data={'profiles': profiles, 'total': len(profiles)},
        message='Agent profiles retrieved successfully'
    )
```

## Testing the Refactored Code

After refactoring, ensure:
1. All endpoints return consistent response formats
2. Errors are properly logged with context
3. Database transactions are properly handled
4. Response status codes are appropriate

Run the test suite to verify functionality:
```bash
pytest tests/ -v
```

## Benefits of This Refactoring

1. **Consistency**: All endpoints follow the same patterns
2. **Maintainability**: Changes to response format or error handling only need to be made in one place
3. **Reliability**: Automatic transaction handling reduces database errors
4. **Debugging**: Structured logging and error context make debugging easier
5. **Code Reduction**: Less boilerplate code in routes and services