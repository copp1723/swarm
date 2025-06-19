-- Initialize MCP Executive Database
-- This script runs on first PostgreSQL container startup

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE agent_status AS ENUM ('idle', 'busy', 'error', 'offline');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE task_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE mcp_db TO mcp_user;
GRANT ALL ON SCHEMA public TO mcp_user;

-- Create indexes for better performance (if tables exist)
DO $$
BEGIN
    -- Check if tables exist before creating indexes
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversations') THEN
        CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'messages') THEN
        CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
    END IF;
    
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'system_logs') THEN
        CREATE INDEX IF NOT EXISTS idx_system_logs_event_type ON system_logs(event_type);
        CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
    END IF;
END
$$;

-- Create email_events table for email agent (if using PostgreSQL instead of SQLite)
CREATE TABLE IF NOT EXISTS email_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(50),
    sender VARCHAR(255),
    recipient VARCHAR(255),
    subject TEXT,
    body_plain TEXT,
    body_html TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for email queries
CREATE INDEX IF NOT EXISTS idx_email_events_message_id ON email_events(message_id);
CREATE INDEX IF NOT EXISTS idx_email_events_sender ON email_events(sender);
CREATE INDEX IF NOT EXISTS idx_email_events_recipient ON email_events(recipient);
CREATE INDEX IF NOT EXISTS idx_email_events_timestamp ON email_events(timestamp);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_email_events_updated_at BEFORE UPDATE
    ON email_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();