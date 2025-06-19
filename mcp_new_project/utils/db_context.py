"""
Unified Database Context Management
Provides consistent database session handling and transaction management
"""
import logging
from contextlib import contextmanager
from typing import Generator, Optional, Any, Callable, TypeVar, Union
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from models.core import db

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseError(Exception):
    """Base exception for database operations"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    pass


class DatabaseIntegrityError(DatabaseError):
    """Raised when database integrity constraints are violated"""
    pass


@contextmanager
def db_session() -> Generator[None, None, None]:
    """
    Database session context manager with automatic commit/rollback.
    
    Usage:
        with db_session():
            user = User(name="John")
            db.session.add(user)
            # Automatically commits on success, rolls back on exception
    
    Raises:
        DatabaseError: For database-related errors
    """
    try:
        yield
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error: {e}")
        raise DatabaseIntegrityError(f"Data integrity violation: {str(e)}")
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"Database operational error: {e}")
        raise DatabaseConnectionError(f"Database connection failed: {str(e)}")
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error: {e}")
        raise DatabaseError(f"Database operation failed: {str(e)}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error during database operation: {e}")
        raise
    finally:
        db.session.close()


@contextmanager
def db_transaction() -> Generator[None, None, None]:
    """
    Explicit database transaction context manager.
    
    Usage:
        with db_transaction():
            # Multiple operations that should be atomic
            order = Order(...)
            db.session.add(order)
            
            for item in items:
                order_item = OrderItem(order_id=order.id, ...)
                db.session.add(order_item)
    """
    try:
        yield
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Transaction failed, rolled back: {e}")
        raise
    finally:
        db.session.close()


def with_db_session(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that wraps a function in a database session.
    
    Usage:
        @with_db_session
        def create_user(name: str, email: str) -> User:
            user = User(name=name, email=email)
            db.session.add(user)
            return user
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        with db_session():
            return func(*args, **kwargs)
    return wrapper


def with_db_transaction(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that wraps a function in a database transaction.
    
    Usage:
        @with_db_transaction
        def process_order(order_data: dict) -> Order:
            # Complex multi-step operation
            order = create_order(order_data)
            process_payment(order)
            send_confirmation(order)
            return order
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        with db_transaction():
            return func(*args, **kwargs)
    return wrapper


def safe_db_execute(
    operation: Callable[..., T],
    *args,
    default_value: Optional[T] = None,
    raise_on_error: bool = False,
    **kwargs
) -> Union[T, None]:
    """
    Execute a database operation safely with error handling.
    
    Args:
        operation: Function to execute
        *args: Positional arguments for the operation
        default_value: Value to return on error (if not raising)
        raise_on_error: Whether to raise exceptions or return default
        **kwargs: Keyword arguments for the operation
    
    Returns:
        Result of the operation or default_value on error
    
    Usage:
        user = safe_db_execute(
            User.query.filter_by(email=email).first,
            default_value=None
        )
    """
    try:
        with db_session():
            return operation(*args, **kwargs)
    except DatabaseError as e:
        logger.error(f"Database operation failed: {e}")
        if raise_on_error:
            raise
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error in database operation: {e}")
        if raise_on_error:
            raise DatabaseError(f"Operation failed: {str(e)}")
        return default_value


def bulk_save(objects: list, batch_size: int = 100) -> tuple[int, list]:
    """
    Save multiple objects to database in batches.
    
    Args:
        objects: List of model instances to save
        batch_size: Number of objects to save per batch
    
    Returns:
        Tuple of (number saved successfully, list of failed objects)
    
    Usage:
        users = [User(name=f"User{i}") for i in range(1000)]
        saved_count, failed = bulk_save(users)
    """
    saved_count = 0
    failed_objects = []
    
    for i in range(0, len(objects), batch_size):
        batch = objects[i:i + batch_size]
        try:
            with db_session():
                db.session.bulk_save_objects(batch)
            saved_count += len(batch)
        except Exception as e:
            logger.error(f"Failed to save batch {i//batch_size}: {e}")
            failed_objects.extend(batch)
    
    return saved_count, failed_objects


def get_or_create(model_class, defaults: Optional[dict] = None, **kwargs) -> tuple[Any, bool]:
    """
    Get an existing object or create a new one.
    
    Args:
        model_class: SQLAlchemy model class
        defaults: Default values for creation
        **kwargs: Lookup parameters
    
    Returns:
        Tuple of (instance, created) where created is True if object was created
    
    Usage:
        user, created = get_or_create(
            User,
            defaults={'is_active': True},
            email='user@example.com'
        )
    """
    with db_session():
        instance = db.session.query(model_class).filter_by(**kwargs).first()
        if instance:
            return instance, False
        
        params = dict(kwargs)
        if defaults:
            params.update(defaults)
        
        instance = model_class(**params)
        db.session.add(instance)
        db.session.flush()
        return instance, True


def update_or_create(model_class, defaults: Optional[dict] = None, **kwargs) -> tuple[Any, bool]:
    """
    Update an existing object or create a new one.
    
    Args:
        model_class: SQLAlchemy model class
        defaults: Values to update or use for creation
        **kwargs: Lookup parameters
    
    Returns:
        Tuple of (instance, created) where created is True if object was created
    
    Usage:
        user, created = update_or_create(
            User,
            defaults={'last_login': datetime.now()},
            email='user@example.com'
        )
    """
    with db_session():
        instance = db.session.query(model_class).filter_by(**kwargs).first()
        if instance:
            # Update existing
            if defaults:
                for key, value in defaults.items():
                    setattr(instance, key, value)
            return instance, False
        else:
            # Create new
            params = dict(kwargs)
            if defaults:
                params.update(defaults)
            instance = model_class(**params)
            db.session.add(instance)
            db.session.flush()
            return instance, True