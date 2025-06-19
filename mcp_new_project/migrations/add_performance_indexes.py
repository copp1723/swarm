"""Add performance indexes to database tables

Run this script to add indexes for improved query performance.
"""
import logging
from sqlalchemy import text, create_engine
from sqlalchemy.exc import OperationalError
import os

logger = logging.getLogger(__name__)


def add_indexes(database_url=None):
    """Add performance indexes to all tables"""
    
    if not database_url:
        database_url = os.environ.get(
            'DATABASE_URL',
            'sqlite:///instance/mcp_executive.db'
        )
    
    engine = create_engine(database_url)
    
    # Index definitions
    indexes = [
        # Conversations table
        ("idx_conversation_session_id", "conversations", ["session_id"]),
        ("idx_conversation_updated", "conversations", ["updated_at"]),
        ("idx_conversation_active", "conversations", ["is_active", "updated_at"]),
        
        # Messages table
        ("idx_message_conversation_id", "messages", ["conversation_id"]),
        ("idx_message_created", "messages", ["created_at"]),
        ("idx_message_conv_created", "messages", ["conversation_id", "created_at"]),
        
        # User preferences
        ("idx_user_pref_session", "user_preferences", ["session_id"]),
        ("idx_user_pref_key", "user_preferences", ["preference_key"]),
        
        # Model usage
        ("idx_model_usage_date", "model_usage", ["date_created"]),
        ("idx_model_usage_model", "model_usage", ["model_id", "date_created"]),
        
        # System logs
        ("idx_system_log_created", "system_logs", ["created_at"]),
        ("idx_system_log_type", "system_logs", ["event_type", "created_at"]),
        ("idx_system_log_source", "system_logs", ["event_source"]),
        
        # File attachments
        ("idx_file_attachment_session", "file_attachments", ["session_id"]),
        ("idx_file_attachment_message", "file_attachments", ["message_id"]),
        
        # Agent tasks (if table exists)
        ("idx_agent_task_status", "agent_assignments", ["status"]),
        ("idx_agent_task_created", "agent_assignments", ["created_at"]),
        ("idx_agent_task_agent", "agent_assignments", ["agent_id", "status"]),
    ]
    
    created_count = 0
    skipped_count = 0
    
    with engine.connect() as conn:
        for index_name, table_name, columns in indexes:
            try:
                # Check if table exists
                if database_url.startswith('sqlite'):
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:table"),
                        {"table": table_name}
                    )
                    if not result.fetchone():
                        logger.info(f"Table {table_name} does not exist, skipping index {index_name}")
                        skipped_count += 1
                        continue
                
                # Create index
                columns_str = ", ".join(columns)
                
                if database_url.startswith('sqlite'):
                    # SQLite syntax
                    create_sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns_str})"
                else:
                    # PostgreSQL syntax
                    create_sql = f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_name} ON {table_name} ({columns_str})"
                
                conn.execute(text(create_sql))
                conn.commit()
                logger.info(f"Created index: {index_name} on {table_name}({columns_str})")
                created_count += 1
                
            except OperationalError as e:
                if "already exists" in str(e).lower():
                    logger.info(f"Index {index_name} already exists")
                    skipped_count += 1
                else:
                    logger.error(f"Error creating index {index_name}: {e}")
                    skipped_count += 1
            except Exception as e:
                logger.error(f"Unexpected error creating index {index_name}: {e}")
                skipped_count += 1
    
    logger.info(f"Index creation complete: {created_count} created, {skipped_count} skipped")
    return created_count, skipped_count


def check_indexes(database_url=None):
    """Check which indexes exist"""
    
    if not database_url:
        database_url = os.environ.get(
            'DATABASE_URL',
            'sqlite:///instance/mcp_executive.db'
        )
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        if database_url.startswith('sqlite'):
            # SQLite
            result = conn.execute(
                text("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            )
            indexes = result.fetchall()
            
            logger.info("Existing indexes:")
            for idx in indexes:
                logger.info(f"  - {idx[0]} on {idx[1]}")
                
        else:
            # PostgreSQL
            result = conn.execute(
                text("""
                    SELECT indexname, tablename 
                    FROM pg_indexes 
                    WHERE schemaname = 'public' 
                    AND indexname LIKE 'idx_%'
                """)
            )
            indexes = result.fetchall()
            
            logger.info("Existing indexes:")
            for idx in indexes:
                logger.info(f"  - {idx[0]} on {idx[1]}")
    
    return len(indexes)


if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Check existing indexes
        count = check_indexes()
        print(f"\nTotal indexes found: {count}")
    else:
        # Create indexes
        print("Creating database indexes...")
        created, skipped = add_indexes()
        print(f"\nSummary: {created} indexes created, {skipped} skipped")
        
        # Show current indexes
        print("\nCurrent indexes:")
        check_indexes()