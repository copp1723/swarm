"""
Database initialization utilities
Handles both sync and async database setup with proper connection management
"""
import logging
import asyncio
from flask import Flask
from models.core import db
from utils.async_database import async_db_manager
from utils.async_wrapper import async_manager
from utils.database_access import db_access
from utils.db_operations import DatabaseUtils

logger = logging.getLogger(__name__)


def init_sync_db(app: Flask):
    """Initialize synchronous database with optimized settings"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Run a test query to ensure connection is working
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            logger.info("Synchronous database initialized and verified")
        except Exception as e:
            logger.error(f"Sync database verification failed: {e}")
            raise


async def init_async_db():
    """Initialize asynchronous database with optimized settings"""
    try:
        await async_db_manager.initialize()
        
        # Create tables in async database
        from models.core import db
        from sqlalchemy.ext.asyncio import AsyncEngine
        
        if async_db_manager._engine:
            async with async_db_manager._engine.begin() as conn:
                # Use sync metadata from SQLAlchemy models
                await conn.run_sync(db.metadata.create_all)
            
            # Run a test query to ensure connection is working
            from sqlalchemy import text
            async with async_db_manager.get_session() as session:
                await session.execute(text('SELECT 1'))
                await session.commit()
        
        logger.info("Asynchronous database initialized and verified")
    except Exception as e:
        logger.error(f"Failed to initialize async database: {e}")
        raise


def initialize_databases(app: Flask):
    """Initialize both sync and async databases with unified access layer"""
    try:
        # Initialize the unified database access layer
        DatabaseUtils.initialize_database(app)
        logger.info("Unified database access layer initialized")
        
        # Initialize sync database
        init_sync_db(app)
        
        # Initialize async database
        async_manager.run_sync(init_async_db())
        
        # Verify both databases are accessible
        health_check = DatabaseUtils.run_in_sync_context(db_access.health_check_async)
        if health_check['status'] != 'healthy':
            logger.warning(f"Database health check returned unhealthy status: {health_check}")
        
        logger.info("All databases initialized and verified successfully")
        
    except Exception as e:
        logger.error(f"Critical error during database initialization: {e}")
        # Don't re-raise in production to allow graceful degradation
        if app.debug:
            raise