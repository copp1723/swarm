"""
Database initialization utilities
Handles both sync and async database setup
"""
import logging
import asyncio
from flask import Flask
from models.core import db
from utils.async_database import async_db_manager
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)


def init_sync_db(app: Flask):
    """Initialize synchronous database"""
    with app.app_context():
        db.create_all()
        logger.info("Synchronous database initialized")


async def init_async_db():
    """Initialize asynchronous database"""
    try:
        await async_db_manager.initialize()
        
        # Create tables in async database
        from models.core import db
        from sqlalchemy.ext.asyncio import AsyncEngine
        
        if async_db_manager._engine:
            async with async_db_manager._engine.begin() as conn:
                # Use sync metadata from SQLAlchemy models
                await conn.run_sync(db.metadata.create_all)
        
        logger.info("Asynchronous database initialized with tables")
    except Exception as e:
        logger.error(f"Failed to initialize async database: {e}")
        raise


def initialize_databases(app: Flask):
    """Initialize both sync and async databases"""
    # Initialize sync database
    init_sync_db(app)
    
    # Initialize async database
    async_manager.run_sync(init_async_db())