"""Add chat history table to database"""
from sqlalchemy import text

def add_chat_history_table(database_url=None):
    """Add the agent_chat_history table"""
    import os
    from sqlalchemy import create_engine
    
    if not database_url:
        database_url = os.environ.get(
            'DATABASE_URL',
            'sqlite:///instance/mcp_executive.db'
        )
    
    engine = create_engine(database_url)
    
    # SQL for creating the table
    if database_url.startswith('sqlite'):
        create_sql = """
        CREATE TABLE IF NOT EXISTS agent_chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id VARCHAR(100) NOT NULL,
            session_id VARCHAR(255),
            message_id VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_chat_agent_id ON agent_chat_history(agent_id);
        CREATE INDEX IF NOT EXISTS idx_chat_session_id ON agent_chat_history(session_id);
        CREATE INDEX IF NOT EXISTS idx_chat_created_at ON agent_chat_history(created_at);
        """
    else:
        # PostgreSQL
        create_sql = """
        CREATE TABLE IF NOT EXISTS agent_chat_history (
            id SERIAL PRIMARY KEY,
            agent_id VARCHAR(100) NOT NULL,
            session_id VARCHAR(255),
            message_id VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE INDEX IF NOT EXISTS idx_chat_agent_id ON agent_chat_history(agent_id);
        CREATE INDEX IF NOT EXISTS idx_chat_session_id ON agent_chat_history(session_id);
        CREATE INDEX IF NOT EXISTS idx_chat_created_at ON agent_chat_history(created_at);
        """
    
    with engine.connect() as conn:
        for statement in create_sql.split(';'):
            if statement.strip():
                conn.execute(text(statement))
        conn.commit()
    
    print("Chat history table created successfully")


if __name__ == "__main__":
    add_chat_history_table()