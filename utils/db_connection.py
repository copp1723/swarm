"""
Centralized Database Connection Management
Eliminates duplicate database connection logic across the application
"""
import os
import logging
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine, event, pool
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Centralized database connection manager"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv(
            'DATABASE_URL',
            'sqlite:///instance/mcp_executive.db'
        )
        self._engine: Optional[Engine] = None
        self._async_engine = None
        self._session_factory = None
        self._async_session_factory = None
        self._scoped_session = None
        
    @property
    def engine(self) -> Engine:
        """Get or create sync engine"""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
    
    @property
    def async_engine(self):
        """Get or create async engine"""
        if self._async_engine is None:
            self._async_engine = self._create_async_engine()
        return self._async_engine
    
    def _create_engine(self) -> Engine:
        """Create sync database engine with optimized settings"""
        connect_args = {}
        pool_kwargs = {}
        
        if self.database_url.startswith('sqlite'):
            connect_args = {
                'check_same_thread': False,
                'timeout': 30
            }
            pool_kwargs = {
                'poolclass': pool.StaticPool,
                'connect_args': connect_args
            }
        else:
            pool_kwargs = {
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
                'pool_recycle': 3600,
                'pool_pre_ping': True
            }
            
        engine = create_engine(
            self.database_url,
            echo=os.getenv('SQL_ECHO', 'false').lower() == 'true',
            **pool_kwargs
        )
        
        # Add connection event listeners
        if self.database_url.startswith('sqlite'):
            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
                
        logger.info(f"Created database engine for: {self._sanitize_url(self.database_url)}")
        return engine
    
    def _create_async_engine(self):
        """Create async database engine"""
        # Convert sync URL to async URL
        async_url = self._convert_to_async_url(self.database_url)
        
        connect_args = {}
        if async_url.startswith('sqlite'):
            connect_args = {'check_same_thread': False}
            
        return create_async_engine(
            async_url,
            echo=os.getenv('SQL_ECHO', 'false').lower() == 'true',
            connect_args=connect_args,
            pool_size=10,
            max_overflow=20
        )
    
    def _convert_to_async_url(self, url: str) -> str:
        """Convert sync database URL to async"""
        conversions = {
            'postgresql://': 'postgresql+asyncpg://',
            'postgres://': 'postgresql+asyncpg://',
            'sqlite:///': 'sqlite+aiosqlite:///',
            'mysql://': 'mysql+aiomysql://'
        }
        
        for sync_prefix, async_prefix in conversions.items():
            if url.startswith(sync_prefix):
                return url.replace(sync_prefix, async_prefix, 1)
        return url
    
    def get_session(self) -> Session:
        """Get a new database session"""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory()
    
    def get_scoped_session(self) -> scoped_session:
        """Get scoped session for web requests"""
        if self._scoped_session is None:
            self._scoped_session = scoped_session(
                sessionmaker(bind=self.engine)
            )
        return self._scoped_session
    
    async def get_async_session(self) -> AsyncSession:
        """Get async database session"""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                self.async_engine,
                expire_on_commit=False
            )
        return self._async_session_factory()
    
    @contextmanager
    def session_scope(self):
        """Provide transactional scope for database operations"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def transaction(self, session: Optional[Session] = None):
        """Execute operations within a transaction"""
        if session:
            # Use existing session
            yield session
        else:
            # Create new session with transaction
            with self.session_scope() as new_session:
                yield new_session
    
    def execute_with_retry(self, func: Callable, max_retries: int = 3, *args, **kwargs):
        """Execute database operation with retry logic"""
        retries = 0
        while retries < max_retries:
            try:
                with self.session_scope() as session:
                    return func(session, *args, **kwargs)
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    logger.error(f"Database operation failed after {max_retries} retries: {str(e)}")
                    raise
                logger.warning(f"Database operation failed, retrying ({retries}/{max_retries}): {str(e)}")
                
    def _sanitize_url(self, url: str) -> str:
        """Remove sensitive info from database URL for logging"""
        if '@' in url:
            # Hide password in connection string
            parts = url.split('@')
            if '://' in parts[0]:
                protocol, rest = parts[0].split('://', 1)
                if ':' in rest:
                    user = rest.split(':')[0]
                    return f"{protocol}://{user}:****@{parts[1]}"
        return url
    
    def close(self):
        """Close database connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._async_engine:
            asyncio.create_task(self._async_engine.dispose())
            self._async_engine = None
        logger.info("Database connections closed")


# Global instance
_db_manager: Optional[DatabaseManager] = None


@lru_cache(maxsize=1)
def get_db_manager() -> DatabaseManager:
    """Get or create global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# Convenience functions
def get_db_session() -> Session:
    """Get a new database session"""
    return get_db_manager().get_session()


def get_scoped_db_session() -> scoped_session:
    """Get scoped session for web requests"""
    return get_db_manager().get_scoped_session()


@contextmanager
def db_transaction():
    """Execute operations within a database transaction"""
    with get_db_manager().session_scope() as session:
        yield session


# Flask integration
def init_db(app):
    """Initialize database for Flask app"""
    db_manager = get_db_manager()
    
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Remove scoped session after request"""
        if db_manager._scoped_session:
            db_manager._scoped_session.remove()
            
    return db_manager