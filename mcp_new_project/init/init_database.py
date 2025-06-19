#!/usr/bin/env python3
"""Initialize database with performance optimizations"""
import os
import sys
import logging

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

from app import app, db
from migrations.add_performance_indexes import add_indexes, check_indexes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database with all optimizations"""
    
    with app.app_context():
        # Create all tables
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created")
        
        # Add performance indexes
        logger.info("Adding performance indexes...")
        created, skipped = add_indexes()
        logger.info(f"Indexes: {created} created, {skipped} skipped")
        
        # Show current state
        logger.info("\nCurrent database indexes:")
        check_indexes()
        
        # Run ANALYZE to update statistics (PostgreSQL)
        if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
            try:
                db.session.execute("ANALYZE")
                db.session.commit()
                logger.info("Database statistics updated (ANALYZE)")
            except Exception as e:
                logger.warning(f"Could not run ANALYZE: {e}")
        
        logger.info("\nDatabase initialization complete!")


if __name__ == "__main__":
    initialize_database()