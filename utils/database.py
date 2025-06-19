"""Database utilities and context managers"""
import logging
from contextlib import contextmanager
from typing import Generator, Optional, Any
from models.core import db

logger = logging.getLogger(__name__)


@contextmanager
def db_transaction() -> Generator[None, None, None]:
    """
    Database transaction context manager that automatically handles commit/rollback.
    
    Usage:
        with db_transaction():
            db.session.add(obj)
            # Automatically commits on success, rolls back on exception
    """
    try:
        yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database transaction failed, rolled back: {e}")
        raise


@contextmanager
def db_session_scope() -> Generator[None, None, None]:
    """
    Database session scope context manager for more complex operations.
    
    Usage:
        with db_session_scope():
            obj1 = Model1(...)
            db.session.add(obj1)
            db.session.flush()  # Get ID without committing
            
            obj2 = Model2(related_id=obj1.id)
            db.session.add(obj2)
            # Automatically commits on success, rolls back on exception
    """
    try:
        yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database session failed, rolled back: {e}")
        raise


def safe_db_operation(operation_func, *args, **kwargs) -> tuple[bool, Optional[Any], Optional[str]]:
    """
    Execute a database operation safely with automatic error handling.
    
    Args:
        operation_func: Function to execute that performs database operations
        *args, **kwargs: Arguments to pass to the operation function
    
    Returns:
        Tuple of (success, result, error_message)
    """
    try:
        with db_transaction():
            result = operation_func(*args, **kwargs)
        return True, result, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Database operation failed: {error_msg}")
        return False, None, error_msg


def create_and_save(model_class, **kwargs) -> tuple[bool, Optional[Any], Optional[str]]:
    """
    Create and save a model instance safely.
    
    Args:
        model_class: The SQLAlchemy model class
        **kwargs: Keyword arguments for model creation
    
    Returns:
        Tuple of (success, instance, error_message)
    """
    def _create_operation():
        instance = model_class(**kwargs)
        db.session.add(instance)
        db.session.flush()  # Get the ID
        return instance
    
    return safe_db_operation(_create_operation)


def update_and_save(instance, **kwargs) -> tuple[bool, Optional[Any], Optional[str]]:
    """
    Update and save a model instance safely.
    
    Args:
        instance: The model instance to update
        **kwargs: Fields to update
    
    Returns:
        Tuple of (success, instance, error_message)
    """
    def _update_operation():
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance
    
    return safe_db_operation(_update_operation)


def delete_instance(instance) -> tuple[bool, None, Optional[str]]:
    """
    Delete a model instance safely.
    
    Args:
        instance: The model instance to delete
    
    Returns:
        Tuple of (success, None, error_message)
    """
    def _delete_operation():
        db.session.delete(instance)
        return None
    
    return safe_db_operation(_delete_operation)
