"""
Database migration to add email tables
Run this script to create email_drafts, email_logs, and email_templates tables
"""

from sqlalchemy import create_engine, text
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='config/.env')

def create_email_tables():
    """Create email-related tables"""
    
    # Get database URL
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/mcp_executive.db')
    
    # Create engine
    engine = create_engine(database_url)
    
    # SQL for creating tables
    sql_statements = [
        # Email drafts table
        """
        CREATE TABLE IF NOT EXISTS email_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            draft_id VARCHAR(36) UNIQUE NOT NULL,
            recipients JSON NOT NULL,
            subject VARCHAR(500) NOT NULL,
            body TEXT NOT NULL,
            html TEXT,
            attachments JSON DEFAULT '[]',
            email_metadata JSON DEFAULT '{}',
            status VARCHAR(20) DEFAULT 'draft',
            created_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_by VARCHAR(100),
            reviewed_at TIMESTAMP,
            sent_at TIMESTAMP,
            review_comments TEXT,
            revisions JSON
        );
        """,
        
        # Email logs table
        """
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient VARCHAR(255) NOT NULL,
            subject VARCHAR(500) NOT NULL,
            status VARCHAR(20) NOT NULL,
            provider VARCHAR(50),
            message_id VARCHAR(255),
            sent_at TIMESTAMP,
            delivered_at TIMESTAMP,
            opened_at TIMESTAMP,
            clicked_at TIMESTAMP,
            open_count INTEGER DEFAULT 0,
            click_count INTEGER DEFAULT 0,
            error TEXT,
            error_code VARCHAR(50),
            email_metadata JSON DEFAULT '{}'
        );
        """,
        
        # Email templates table
        """
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id VARCHAR(100) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            subject_template VARCHAR(500) NOT NULL,
            body_template TEXT NOT NULL,
            html_template TEXT,
            variables_schema JSON,
            category VARCHAR(50),
            tags JSON DEFAULT '[]',
            is_active BOOLEAN DEFAULT 1,
            created_by VARCHAR(100) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usage_count INTEGER DEFAULT 0,
            last_used_at TIMESTAMP
        );
        """,
        
        # Indexes
        "CREATE INDEX IF NOT EXISTS idx_email_drafts_draft_id ON email_drafts(draft_id);",
        "CREATE INDEX IF NOT EXISTS idx_email_drafts_status ON email_drafts(status);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_recipient ON email_logs(recipient);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_message_id ON email_logs(message_id);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at_status ON email_logs(sent_at, status);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_recipient_sent_at ON email_logs(recipient, sent_at);",
        "CREATE INDEX IF NOT EXISTS idx_email_templates_template_id ON email_templates(template_id);",
        "CREATE INDEX IF NOT EXISTS idx_email_templates_category ON email_templates(category);"
    ]
    
    # Execute each statement
    with engine.connect() as conn:
        for sql in sql_statements:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"Successfully executed: {sql.split()[0]} {sql.split()[1]} ...")
            except Exception as e:
                print(f"Error executing SQL: {e}")
                print(f"SQL: {sql[:100]}...")
    
    print("\nEmail tables created successfully!")
    
    # Verify tables
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'email_%'
            ORDER BY name;
        """))
        tables = [row[0] for row in result]
        print(f"\nCreated tables: {tables}")


if __name__ == "__main__":
    create_email_tables()