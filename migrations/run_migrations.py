#!/usr/bin/env python3
"""
Database Migration Runner
Applies database migrations for persistence layer
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from models.core import db
from config.database import init_database, create_all_tables
from utils.logging_config import get_logger

logger = get_logger(__name__)

def run_migrations():
    """Run database migrations"""
    # Create minimal Flask app for database context
    app = Flask(__name__)
    init_database(app)
    
    with app.app_context():
        try:
            # Create all tables using SQLAlchemy
            logger.info("Creating database tables...")
            create_all_tables(db)
            
            # Run any custom SQL migrations if needed
            if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
                logger.info("Detected PostgreSQL database")
                # PostgreSQL-specific optimizations could go here
            else:
                logger.info("Detected SQLite database")
                # SQLite-specific optimizations
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    conn.execute(text("PRAGMA journal_mode=WAL"))
                    conn.execute(text("PRAGMA synchronous=NORMAL"))
                    conn.execute(text("PRAGMA cache_size=10000"))
                    conn.execute(text("PRAGMA temp_store=MEMORY"))
                    conn.commit()
            
            # Verify tables were created
            from models.task_storage import CollaborationTask, ConversationHistory, AuditLog
            
            # Test queries
            task_count = CollaborationTask.query.count()
            logger.info(f"Collaboration tasks table ready. Current tasks: {task_count}")
            
            conv_count = ConversationHistory.query.count()
            logger.info(f"Conversation history table ready. Current conversations: {conv_count}")
            
            audit_count = AuditLog.query.count()
            logger.info(f"Audit log table ready. Current audit entries: {audit_count}")
            
            logger.info("✅ All database migrations completed successfully!")
            
            # Create sample data if database is empty
            if task_count == 0:
                logger.info("Creating sample task for testing...")
                from models.task_storage import create_task
                sample_task = create_task(
                    description="Sample task - Database persistence test",
                    session_id="sample_session",
                    agents_involved=["general_01", "coding_01"],
                    status="completed",
                    summary="This is a sample task to verify database persistence is working correctly."
                )
                logger.info(f"Created sample task: {sample_task.task_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False

if __name__ == "__main__":
    print("🔄 Running database migrations...")
    print("-" * 50)
    
    success = run_migrations()
    
    if success:
        print("\n✅ Migrations completed successfully!")
        print("\nDatabase features enabled:")
        print("  • Tasks persist across server restarts")
        print("  • Full conversation history tracking")
        print("  • Comprehensive audit trail")
        print("  • Agent memory across sessions")
    else:
        print("\n❌ Migration failed! Check logs for details.")
        sys.exit(1)