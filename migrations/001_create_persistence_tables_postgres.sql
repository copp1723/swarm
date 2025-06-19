-- Migration: Create persistence tables for task storage (PostgreSQL version)
-- Date: 2025-06-19
-- Description: Replaces in-memory TASKS dictionary with persistent database storage

-- Create collaboration_tasks table
CREATE TABLE IF NOT EXISTS collaboration_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Task metadata
    description TEXT NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    working_directory VARCHAR(1000),
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    current_phase VARCHAR(255) DEFAULT 'Initializing',
    
    -- Agent information
    model_id VARCHAR(100) DEFAULT 'openai/gpt-4',
    agents_involved JSONB DEFAULT '[]'::jsonb,
    primary_agent VARCHAR(100),
    sequential BOOLEAN DEFAULT FALSE,
    
    -- Results and output
    results JSONB DEFAULT '{}'::jsonb,
    summary TEXT,
    error_message TEXT,
    final_result TEXT,
    
    -- File tracking
    files_created JSONB DEFAULT '[]'::jsonb,
    files_modified JSONB DEFAULT '[]'::jsonb,
    files_deleted JSONB DEFAULT '[]'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Performance metrics
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    execution_time_seconds FLOAT,
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    tags JSONB DEFAULT '[]'::jsonb,
    priority VARCHAR(20) DEFAULT 'medium',
    
    -- Legacy fields for compatibility
    agents JSONB DEFAULT '[]'::jsonb,
    conversations JSONB DEFAULT '[]'::jsonb,
    all_communications JSONB DEFAULT '[]'::jsonb,
    messages JSONB DEFAULT '[]'::jsonb,
    task_description TEXT
);

-- Create indexes for performance
CREATE INDEX idx_task_task_id ON collaboration_tasks(task_id);
CREATE INDEX idx_task_session_status ON collaboration_tasks(session_id, status);
CREATE INDEX idx_task_created ON collaboration_tasks(created_at);
CREATE INDEX idx_task_status ON collaboration_tasks(status);
CREATE INDEX idx_task_agents_gin ON collaboration_tasks USING gin(agents_involved);
CREATE INDEX idx_task_tags_gin ON collaboration_tasks USING gin(tags);

-- Create conversation_history table
CREATE TABLE IF NOT EXISTS conversation_history (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    conversation_id VARCHAR(255) UNIQUE NOT NULL,
    
    -- Conversation metadata
    agent_id VARCHAR(100) NOT NULL,
    agent_role VARCHAR(100),
    phase VARCHAR(255),
    
    -- Message content
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    
    -- Tool usage
    tools_used JSONB DEFAULT '[]'::jsonb,
    tool_results JSONB DEFAULT '{}'::jsonb,
    
    -- Performance metrics
    tokens_used INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional context
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_conversation_task
        FOREIGN KEY (task_id) 
        REFERENCES collaboration_tasks(task_id) 
        ON DELETE CASCADE
);

-- Create indexes for conversation history
CREATE INDEX idx_conv_task_id ON conversation_history(task_id);
CREATE INDEX idx_conv_agent_id ON conversation_history(agent_id);
CREATE INDEX idx_conv_created ON conversation_history(created_at);
CREATE INDEX idx_conv_metadata_gin ON conversation_history USING gin(metadata);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    audit_id VARCHAR(255) UNIQUE NOT NULL,
    task_id VARCHAR(255),
    
    -- Action details
    action_type VARCHAR(100) NOT NULL,
    action_description TEXT NOT NULL,
    agent_id VARCHAR(100) NOT NULL,
    
    -- Context
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    ip_address VARCHAR(45),
    
    -- Results
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- File operations
    files_affected JSONB DEFAULT '[]'::jsonb,
    
    -- API/Tool usage
    api_calls_made JSONB DEFAULT '[]'::jsonb,
    tools_invoked JSONB DEFAULT '[]'::jsonb,
    
    -- Performance
    execution_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional data
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT fk_audit_task
        FOREIGN KEY (task_id) 
        REFERENCES collaboration_tasks(task_id) 
        ON DELETE SET NULL
);

-- Create indexes for audit logs
CREATE INDEX idx_audit_audit_id ON audit_logs(audit_id);
CREATE INDEX idx_audit_task_id ON audit_logs(task_id);
CREATE INDEX idx_audit_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_agent_id ON audit_logs(agent_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_audit_session ON audit_logs(session_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to update updated_at timestamp
CREATE TRIGGER update_collaboration_tasks_updated_at 
    BEFORE UPDATE ON collaboration_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE collaboration_tasks IS 'Main task storage replacing in-memory TASKS dictionary';
COMMENT ON TABLE conversation_history IS 'Agent conversation history for task persistence';
COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all agent actions';

-- Create view for active tasks
CREATE OR REPLACE VIEW active_tasks AS
SELECT 
    task_id,
    description,
    status,
    progress,
    current_phase,
    agents_involved,
    created_at,
    updated_at
FROM collaboration_tasks
WHERE status IN ('running', 'pending')
ORDER BY created_at DESC;

-- Create view for task statistics
CREATE OR REPLACE VIEW task_statistics AS
SELECT 
    COUNT(*) as total_tasks,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_tasks,
    COUNT(CASE WHEN status = 'running' THEN 1 END) as running_tasks,
    AVG(execution_time_seconds) as avg_execution_time,
    SUM(total_messages) as total_messages,
    SUM(total_tokens) as total_tokens
FROM collaboration_tasks;