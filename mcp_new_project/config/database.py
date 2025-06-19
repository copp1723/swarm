"""
Database Configuration and Setup
Handles database initialization and configuration for persistent storage
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy
from utils.logging_config import get_logger

logger = get_logger(__name__)

def get_database_url():
    """Get database URL from environment or use default SQLite"""
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        # Handle Heroku-style postgres:// URLs
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    
    # Default to SQLite
    instance_path = Path(__file__).parent.parent / 'instance'
    instance_path.mkdir(exist_ok=True)
    db_path = instance_path / 'mcp_tasks.db'
    return f'sqlite:///{db_path}'

def init_database(app):
    """Initialize database with Flask app"""
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Additional SQLite configuration for better concurrency
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'connect_args': {
                'check_same_thread': False,
                'timeout': 15
            }
        }
    
    logger.info(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")

def create_all_tables(db):
    """Create all database tables"""
    try:
        # Import all models to ensure they're registered
        from models.tasks import TaskRecord, CompletedTask
        from models.core import Conversation, Message, UserPreference, ModelUsage, SystemLog, FileAttachment
        from models.task_storage import CollaborationTask, ConversationHistory, AuditLog
        
        db.create_all()
        logger.info("All database tables created successfully")
        
        # Create indexes for better performance
        with db.engine.connect() as conn:
            # Task-related indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_collab_tasks_session ON collaboration_tasks(session_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_collab_tasks_status ON collaboration_tasks(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_conv_history_task ON conversation_history(task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_task ON audit_logs(task_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_logs_type ON audit_logs(action_type)"))
            conn.commit()
            
        logger.info("Database indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def get_db_session():
    """Get a database session for standalone scripts"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()

def test_database_connection(db):
    """Test database connection and basic operations"""
    try:
        # Test connection
        db.session.execute(text('SELECT 1'))
        db.session.commit()
        logger.info("Database connection test successful")
        
        # Test model operations
        from models.task_storage import CollaborationTask
        test_task = CollaborationTask(
            task_id=f"test_{os.urandom(4).hex()}",
            description="Test task",
            session_id="test_session"
        )
        db.session.add(test_task)
        db.session.commit()
        
        # Verify and cleanup
        found = CollaborationTask.query.filter_by(task_id=test_task.task_id).first()
        if found:
            db.session.delete(found)
            db.session.commit()
            logger.info("Database model operations test successful")
        else:
            logger.error("Database model test failed - could not retrieve test record")
            
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        db.session.rollback()
        raise