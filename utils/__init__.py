"""Utilities package for the MCP Agent project"""

# Existing utilities
from .response_handler import response_handler, ResponseHandler
from .validation import validate_request_data, validate_message_required, validate_json_data
from .database import (
    db_transaction,
    db_session_scope,
    safe_db_operation,
    create_and_save,
    update_and_save,
    delete_instance
)

# New utilities
from .file_io import (
    safe_read_json,
    safe_write_json,
    safe_read_yaml,
    safe_write_yaml,
    atomic_write,
    ensure_directory_exists,
    safe_file_operation,
    read_file_lines,
    append_to_file,
    file_exists,
    get_file_size,
    copy_file,
    move_file,
    delete_file
)

from .async_error_handler import (
    handle_async_route_errors,
    async_error_response,
    AsyncRouteHandler,
    retry_async,
    run_with_semaphore,
    create_async_error_handler
)

from .batch_operations import (
    batch_insert,
    batch_update,
    batch_delete,
    transaction_with_rollback,
    chunked_query,
    async_chunked_query,
    BatchProcessor
)

from .config_validator import (
    validate_config_schema,
    check_required_env_variables,
    validate_api_credentials,
    load_and_validate_config,
    validate_config_value,
    create_default_config,
    ConfigValidationError
)

from .error_catalog import (
    ErrorCodes,
    ERROR_MESSAGES,
    ERROR_STATUS_CODES,
    get_error_message,
    format_error_response,
    get_status_code,
    is_client_error,
    is_server_error,
    ErrorBuilder,
    ErrorMessages
)

__all__ = [
    # Existing utilities
    'response_handler',
    'ResponseHandler',
    'validate_request_data',
    'validate_message_required',
    'validate_json_data',
    'db_transaction',
    'db_session_scope',
    'safe_db_operation',
    'create_and_save',
    'update_and_save',
    'delete_instance',
    
    # File I/O utilities
    'safe_read_json',
    'safe_write_json',
    'safe_read_yaml',
    'safe_write_yaml',
    'atomic_write',
    'ensure_directory_exists',
    'safe_file_operation',
    'read_file_lines',
    'append_to_file',
    'file_exists',
    'get_file_size',
    'copy_file',
    'move_file',
    'delete_file',
    
    # Async error handling
    'handle_async_route_errors',
    'async_error_response',
    'AsyncRouteHandler',
    'retry_async',
    'run_with_semaphore',
    'create_async_error_handler',
    
    # Batch operations
    'batch_insert',
    'batch_update',
    'batch_delete',
    'transaction_with_rollback',
    'chunked_query',
    'async_chunked_query',
    'BatchProcessor',
    
    # Config validation
    'validate_config_schema',
    'check_required_env_variables',
    'validate_api_credentials',
    'load_and_validate_config',
    'validate_config_value',
    'create_default_config',
    'ConfigValidationError',
    
    # Error catalog
    'ErrorCodes',
    'ERROR_MESSAGES',
    'ERROR_STATUS_CODES',
    'get_error_message',
    'format_error_response',
    'get_status_code',
    'is_client_error',
    'is_server_error',
    'ErrorBuilder',
    'ErrorMessages'
]