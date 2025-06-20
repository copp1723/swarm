"""
Database Error Handler
Provides comprehensive error handling for database operations
"""
import logging
import functools
from typing import Optional, Callable, Any, Type, Union, Dict
from datetime import datetime

from sqlalchemy.exc import (
    SQLAlchemyError, IntegrityError, OperationalError, 
    DataError, ProgrammingError, InternalError,
    InterfaceError, DatabaseError, DBAPIError,
    TimeoutError as SQLTimeoutError,
    DisconnectionError, InvalidRequestError,
    NoResultFound, MultipleResultsFound
)
from flask import current_app
from werkzeug.exceptions import ServiceUnavailable, InternalServerError

from utils.error_catalog import ErrorCodes
from utils.notification_service import NotificationService

logger = logging.getLogger(__name__)


class DatabaseErrorHandler:
    """Handles database errors with retry logic and notifications"""
    
    # Error categorization
    RETRYABLE_ERRORS = (
        OperationalError,
        DisconnectionError,
        TimeoutError,
        SQLTimeoutError,
        DBAPIError
    )
    
    INTEGRITY_ERRORS = (
        IntegrityError,
        DataError
    )
    
    PROGRAMMING_ERRORS = (
        ProgrammingError,
        InvalidRequestError
    )
    
    def __init__(self):
        self.notification_service = None
        self._error_counts = {}
        self._last_notification = {}
        self.notification_threshold = 5  # Send notification after 5 errors
        self.notification_cooldown = 300  # 5 minutes between notifications
    
    def set_notification_service(self, service: NotificationService):
        """Set the notification service for critical errors"""
        self.notification_service = service
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle database errors with appropriate response
        
        Args:
            error: The exception that occurred
            context: Additional context about the operation
            
        Returns:
            Error response dictionary
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Log the error with context
        logger.error(f"Database error ({error_type}): {error_message}", 
                    extra={'context': context})
        
        # Track error frequency
        self._track_error(error_type)
        
        # Determine error category and response
        if isinstance(error, self.RETRYABLE_ERRORS):
            return self._handle_retryable_error(error, context)
        elif isinstance(error, self.INTEGRITY_ERRORS):
            return self._handle_integrity_error(error, context)
        elif isinstance(error, self.PROGRAMMING_ERRORS):
            return self._handle_programming_error(error, context)
        elif isinstance(error, (NoResultFound, MultipleResultsFound)):
            return self._handle_query_error(error, context)
        else:
            return self._handle_unknown_error(error, context)
    
    def _handle_retryable_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """Handle errors that can be retried"""
        error_response = {
            'error_code': ErrorCodes.DATABASE_CONNECTION_ERROR,
            'message': 'Database connection error. The operation will be retried.',
            'retryable': True,
            'details': {
                'error_type': type(error).__name__,
                'should_retry': True
            }
        }
        
        # Check if we should send notification
        if self._should_notify(type(error).__name__):
            self._send_error_notification(error, context, 'retryable')
        
        return error_response
    
    def _handle_integrity_error(self, error: IntegrityError, context: Dict) -> Dict[str, Any]:
        """Handle data integrity violations"""
        # Parse the error to provide user-friendly message
        error_str = str(error)
        
        if 'UNIQUE constraint failed' in error_str or 'duplicate key' in error_str:
            message = 'This record already exists. Please use unique values.'
            error_code = ErrorCodes.DUPLICATE_ENTRY
        elif 'FOREIGN KEY constraint failed' in error_str:
            message = 'Related record not found. Please check your references.'
            error_code = ErrorCodes.INVALID_REFERENCE
        elif 'NOT NULL constraint failed' in error_str:
            message = 'Required field is missing. Please provide all required data.'
            error_code = ErrorCodes.MISSING_REQUIRED_FIELD
        else:
            message = 'Data validation failed. Please check your input.'
            error_code = ErrorCodes.VALIDATION_ERROR
        
        return {
            'error_code': error_code,
            'message': message,
            'retryable': False,
            'details': {
                'error_type': 'IntegrityError',
                'constraint': self._extract_constraint_name(error_str)
            }
        }
    
    def _handle_programming_error(self, error: ProgrammingError, context: Dict) -> Dict[str, Any]:
        """Handle programming/SQL errors"""
        return {
            'error_code': ErrorCodes.INVALID_QUERY,
            'message': 'Invalid database operation. Please contact support.',
            'retryable': False,
            'details': {
                'error_type': 'ProgrammingError',
                'should_report': True
            }
        }
    
    def _handle_query_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """Handle query result errors"""
        if isinstance(error, NoResultFound):
            return {
                'error_code': ErrorCodes.NOT_FOUND,
                'message': 'Requested resource not found.',
                'retryable': False
            }
        else:  # MultipleResultsFound
            return {
                'error_code': ErrorCodes.MULTIPLE_RESULTS,
                'message': 'Multiple records found when expecting one.',
                'retryable': False
            }
    
    def _handle_unknown_error(self, error: Exception, context: Dict) -> Dict[str, Any]:
        """Handle unknown database errors"""
        # Send notification for unknown errors
        if self._should_notify('UnknownDatabaseError'):
            self._send_error_notification(error, context, 'unknown')
        
        return {
            'error_code': ErrorCodes.DATABASE_ERROR,
            'message': 'An unexpected database error occurred.',
            'retryable': False,
            'details': {
                'error_type': type(error).__name__,
                'should_report': True
            }
        }
    
    def _track_error(self, error_type: str):
        """Track error frequency"""
        current_time = datetime.utcnow()
        
        if error_type not in self._error_counts:
            self._error_counts[error_type] = []
        
        # Add current error
        self._error_counts[error_type].append(current_time)
        
        # Clean up old errors (older than 1 hour)
        cutoff = current_time.timestamp() - 3600
        self._error_counts[error_type] = [
            t for t in self._error_counts[error_type] 
            if t.timestamp() > cutoff
        ]
    
    def _should_notify(self, error_type: str) -> bool:
        """Check if we should send a notification for this error"""
        if not self.notification_service:
            return False
        
        # Check error frequency
        error_count = len(self._error_counts.get(error_type, []))
        if error_count < self.notification_threshold:
            return False
        
        # Check cooldown
        last_notification = self._last_notification.get(error_type)
        if last_notification:
            time_since_last = (datetime.utcnow() - last_notification).total_seconds()
            if time_since_last < self.notification_cooldown:
                return False
        
        return True
    
    def _send_error_notification(self, error: Exception, context: Dict, error_category: str):
        """Send notification for critical errors"""
        try:
            if not self.notification_service:
                return
            
            error_type = type(error).__name__
            
            # Update last notification time
            self._last_notification[error_type] = datetime.utcnow()
            
            # Prepare notification
            error_count = len(self._error_counts.get(error_type, []))
            
            notification_data = {
                'subject': f'Database Error Alert: {error_type}',
                'message': f'''
                A database error has occurred multiple times:
                
                Error Type: {error_type}
                Category: {error_category}
                Occurrences: {error_count} in the last hour
                
                Error Message: {str(error)}
                
                Context: {context}
                
                Please investigate immediately.
                ''',
                'priority': 'high',
                'tags': ['database', 'error', error_category]
            }
            
            # Send notification asynchronously
            from tasks.maintenance_tasks import send_error_notification
            send_error_notification.delay(notification_data)
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def _extract_constraint_name(self, error_str: str) -> Optional[str]:
        """Extract constraint name from error message"""
        # Common patterns for constraint names
        import re
        
        patterns = [
            r'constraint "([^"]+)"',
            r'constraint failed: ([^\s]+)',
            r'key \(([^)]+)\)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_str)
            if match:
                return match.group(1)
        
        return None
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics"""
        stats = {}
        current_time = datetime.utcnow()
        
        for error_type, timestamps in self._error_counts.items():
            # Count errors in different time windows
            last_5_min = sum(1 for t in timestamps 
                           if (current_time - t).total_seconds() < 300)
            last_hour = len(timestamps)
            
            stats[error_type] = {
                'last_5_minutes': last_5_min,
                'last_hour': last_hour,
                'last_notification': self._last_notification.get(error_type, 'Never')
            }
        
        return stats


# Global error handler instance
db_error_handler = DatabaseErrorHandler()


def with_db_error_handling(func: Callable) -> Callable:
    """
    Decorator to add comprehensive error handling to database operations
    """
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = {
                'function': func.__name__,
                'args': str(args)[:100],  # Truncate for logging
                'kwargs': str(kwargs)[:100]
            }
            error_response = db_error_handler.handle_error(e, context)
            
            # Re-raise with additional context
            if error_response.get('retryable'):
                raise ServiceUnavailable(error_response['message'])
            else:
                raise InternalServerError(error_response['message'])
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            context = {
                'function': func.__name__,
                'args': str(args)[:100],
                'kwargs': str(kwargs)[:100]
            }
            error_response = db_error_handler.handle_error(e, context)
            
            # Re-raise with additional context
            if error_response.get('retryable'):
                raise ServiceUnavailable(error_response['message'])
            else:
                raise InternalServerError(error_response['message'])
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper