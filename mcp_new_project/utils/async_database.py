"""
Async Database Configuration and Session Management
Provides async database operations alongside existing sync operations
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv(dotenv_path='../config/.env')
logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    """Manages async database connections and sessions"""
    
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker | None = None
        self._initialized = False
    
    def _get_async_database_url(self) -> str:
        """Convert sync database URL to async format"""
        sync_url = os.environ.get('DATABASE_URL', '')
        
        # Handle different database types
        if sync_url.startswith('sqlite:///'):
            # Convert sqlite:/// to sqlite+aiosqlite:///
            return sync_url.replace('sqlite:///', 'sqlite+aiosqlite:///')
        elif sync_url.startswith('postgresql://'):
            # Convert postgresql:// to postgresql+asyncpg://
            return sync_url.replace('postgresql://', 'postgresql+asyncpg://')
        elif sync_url.startswith('postgres://'):
            # Handle Heroku-style postgres URLs
            return sync_url.replace('postgres://', 'postgresql+asyncpg://')
        else:
            # Default to aiosqlite for development
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            instance_dir = os.path.join(backend_dir, "instance")
            os.makedirs(instance_dir, exist_ok=True)
            return f'sqlite+aiosqlite:///{os.path.join(instance_dir, "mcp_executive_async.db")}'
    
    async def initialize(self):
        """Initialize the async database engine and sessionmaker"""
        if self._initialized:
            return
        
        try:
            database_url = self._get_async_database_url()
            logger.info(f"Initializing async database with URL pattern: {database_url.split('@')[0]}...")
            
            # Create async engine with appropriate settings
            engine_kwargs = {
                "echo": False,
                "future": True,
            }
            
            # Use NullPool for SQLite to avoid connection issues
            if 'sqlite' in database_url:
                engine_kwargs["poolclass"] = NullPool
            else:
                # For PostgreSQL, use connection pooling
                engine_kwargs.update({
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_pre_ping": True,
                    "pool_recycle": 300,
                })
            
            self._engine = create_async_engine(database_url, **engine_kwargs)
            
            # Create async sessionmaker
            self._sessionmaker = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self._initialized = True
            logger.info("Async database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize async database: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session"""
        if not self._initialized:
            await self.initialize()
        
        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self):
        """Close the async database engine"""
        if self._engine:
            await self._engine.dispose()
            self._initialized = False
            logger.info("Async database connections closed")


# Global async database manager instance
async_db_manager = AsyncDatabaseManager()


# Convenience function for getting async sessions
def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get an async database session using the global manager"""
    return async_db_manager.get_session()