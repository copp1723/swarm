"""
Unified Database Access Layer
Provides a clean interface for both sync and async database operations
Handles proper connection pooling, session management, and error handling
"""
import asyncio
import functools
import logging
from contextlib import contextmanager, asynccontextmanager
from typing import TypeVar, Callable, Optional, Any, Union
from threading import local
import time

from flask import current_app, has_app_context
from sqlalchemy import text, create_engine, pool
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
from sqlalchemy.pool import NullPool, QueuePool

from utils.error_catalog import ErrorCodes
from utils.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

T = TypeVar('T')

# Thread-local storage for sync sessions
_thread_local = local()

# Circuit breakers for database connections
_sync_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    expected_exception=OperationalError
)
_async_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    expected_exception=OperationalError
)


class DatabaseAccessLayer:
    """
    Unified database access layer that handles both sync and async operations
    with proper connection pooling and session management
    """
    
    def __init__(self):
        self._sync_engine = None
        self._async_engine = None
        self._sync_session_factory = None
        self._async_session_factory = None
        self._scoped_session = None
        self._initialized = False
        
    def initialize(self, app=None):
        """Initialize both sync and async database engines"""
        if self._initialized:
            return
            
        try:
            # Get database URL from app config or environment
            if app and hasattr(app, 'config'):
                db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
            else:
                import os
                db_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/mcp_executive.db')
            
            # Initialize sync engine
            self._init_sync_engine(db_url)
            
            # Initialize async engine
            self._init_async_engine(db_url)
            
            self._initialized = True
            logger.info("Database access layer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database access layer: {e}")
            raise
    
    def _init_sync_engine(self, db_url: str):
        """Initialize synchronous database engine with optimal settings"""
        engine_kwargs = {
            'echo': False,
            'future': True,
        }
        
        if 'postgresql' in db_url or 'postgres' in db_url:
            # PostgreSQL optimizations
            engine_kwargs.update({
                'pool_size': 20,
                'max_overflow': 40,
                'pool_pre_ping': True,
                'pool_recycle': 3600,
                'poolclass': QueuePool,
            })
        else:
            # SQLite optimizations
            engine_kwargs.update({
                'poolclass': NullPool,  # SQLite doesn't benefit from connection pooling
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 30
                }
            })
        
        self._sync_engine = create_engine(db_url, **engine_kwargs)
        self._sync_session_factory = sessionmaker(
            bind=self._sync_engine,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        self._scoped_session = scoped_session(self._sync_session_factory)
        
    def _init_async_engine(self, db_url: str):
        """Initialize asynchronous database engine with optimal settings"""
        # Convert sync URL to async format
        if db_url.startswith('sqlite:///'):
            async_url = db_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
        elif db_url.startswith('postgresql://'):
            async_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
        elif db_url.startswith('postgres://'):
            async_url = db_url.replace('postgres://', 'postgresql+asyncpg://')
        else:
            async_url = db_url
        
        engine_kwargs = {
            'echo': False,
            'future': True,
        }
        
        if 'postgresql' in async_url:
            # PostgreSQL async optimizations
            engine_kwargs.update({
                'pool_size': 20,
                'max_overflow': 40,
                'pool_pre_ping': True,
                'pool_recycle': 3600,
            })
        else:
            # SQLite async doesn't support connection pooling
            engine_kwargs['poolclass'] = NullPool
        
        self._async_engine = create_async_engine(async_url, **engine_kwargs)
        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
    
    @contextmanager
    def get_sync_session(self) -> Session:
        """Get a synchronous database session with proper lifecycle management"""
        if not self._initialized:
            self.initialize()
        
        # Create session through circuit breaker for resilience
        def create_session():
            return self._scoped_session()
        
        session = _sync_circuit_breaker.call(create_session)
        try:
            yield session
            session.commit()
        except IntegrityError:
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self._scoped_session.remove()
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncSession:
        """Get an asynchronous database session with proper lifecycle management"""
        if not self._initialized:
            self.initialize()
        
        # Create session through circuit breaker for resilience
        def create_session():
            return self._async_session_factory()
        
        async_session_factory = await _async_circuit_breaker.call_async(lambda: self._async_session_factory)
        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise
            except Exception:
                await session.rollback()
                raise
    
    def execute_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a function with a sync database session"""
        with self.get_sync_session() as session:
            return func(session, *args, **kwargs)
    
    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a function with an async database session"""
        async with self.get_async_session() as session:
            return await func(session, *args, **kwargs)
    
    def sync_to_async_bridge(self, sync_func: Callable) -> Callable:
        """
        Bridge synchronous database operations to async context
        Useful for Flask routes that need to call async database operations
        """
        @functools.wraps(sync_func)
        def wrapper(*args, **kwargs):
            try:
                # Check if there's already a running event loop
                loop = asyncio.get_running_loop()
                
                # If we're in an async context with a running loop,
                # create a new loop in a thread to avoid conflicts
                def run_in_new_loop():
                    # Create a new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(sync_func(*args, **kwargs))
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
                
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_new_loop)
                    return future.result()
                    
            except RuntimeError:
                # No running loop, we can safely create and run one
                try:
                    return asyncio.run(sync_func(*args, **kwargs))
                except RuntimeError as e:
                    if "cannot be called from a running event loop" in str(e):
                        # Fallback: run in a new thread with a new loop
                        def run_in_new_loop():
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                return new_loop.run_until_complete(sync_func(*args, **kwargs))
                            finally:
                                new_loop.close()
                                asyncio.set_event_loop(None)
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_in_new_loop)
                            return future.result()
                    else:
                        raise
        
        return wrapper
    
    async def async_to_sync_bridge(self, async_func: Callable) -> Any:
        """
        Bridge asynchronous database operations to sync context
        Useful for background tasks that need to use async database
        """
        # This runs the async function in the current event loop
        return await async_func()
    
    def health_check_sync(self) -> dict:
        """Perform synchronous database health check"""
        try:
            start_time = time.time()
            with self.get_sync_session() as session:
                result = session.execute(text('SELECT 1'))
                result.scalar()
            
            return {
                'status': 'healthy',
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error(f"Sync database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    async def health_check_async(self) -> dict:
        """Perform asynchronous database health check"""
        try:
            start_time = time.time()
            async with self.get_async_session() as session:
                result = await session.execute(text('SELECT 1'))
                result.scalar()
            
            return {
                'status': 'healthy',
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error(f"Async database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def close(self):
        """Close all database connections"""
        if self._sync_engine:
            self._sync_engine.dispose()
        
        if self._async_engine:
            # Async engine disposal needs to be run in async context
            asyncio.create_task(self._async_engine.dispose())
        
        self._initialized = False
        logger.info("Database access layer closed")


# Global database access instance
db_access = DatabaseAccessLayer()


# Convenience decorators for database operations
def with_sync_session(func: Callable) -> Callable:
    """Decorator to automatically inject a sync database session"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return db_access.execute_sync(func, *args, **kwargs)
    return wrapper


def with_async_session(func: Callable) -> Callable:
    """Decorator to automatically inject an async database session"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await db_access.execute_async(func, *args, **kwargs)
    return wrapper


# Helper functions for common database operations
def get_db_session() -> Session:
    """Get a sync database session (for backward compatibility)"""
    if not hasattr(_thread_local, 'session') or _thread_local.session is None:
        _thread_local.session = db_access._scoped_session()
    return _thread_local.session


def close_db_session():
    """Close the current thread's database session"""
    if hasattr(_thread_local, 'session') and _thread_local.session:
        _thread_local.session.close()
        db_access._scoped_session.remove()
        _thread_local.session = None