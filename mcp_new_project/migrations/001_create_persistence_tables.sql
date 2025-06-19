-- Migration: Create persistence tables for task storage
-- Date: 2025-06-19
-- Description: Replaces in-memory TASKS dictionary with persistent database storage

-- Create collaboration_tasks table
CREATE TABLE IF NOT EXISTS collaboration_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    agents_involved JSON DEFAULT '[]',
    primary_agent VARCHAR(100),
    sequential BOOLEAN DEFAULT FALSE,
    
    -- Results and output
    results JSON DEFAULT '{}',
    summary TEXT,
    error_message TEXT,
    final_result TEXT,
    
    -- File tracking
    files_created JSON DEFAULT '[]',
    files_modified JSON DEFAULT '[]',
    files_deleted JSON DEFAULT '[]',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Performance metrics
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    execution_time_seconds FLOAT,
    
    -- Additional metadata
    metadata JSON DEFAULT '{}',
    tags JSON DEFAULT '[]',
    priority VARCHAR(20) DEFAULT 'medium',
    
    -- Legacy fields for compatibility
    agents JSON DEFAULT '[]',
    conversations JSON DEFAULT '[]',
    all_communications JSON DEFAULT '[]',
    messages JSON DEFAULT '[]',
    task_description TEXT
);

-- Create indexes for performance
CREATE INDEX idx_task_task_id ON collaboration_tasks(task_id);
CREATE INDEX idx_task_session_status ON collaboration_tasks(session_id, status);
CREATE INDEX idx_task_created ON collaboration_tasks(created_at);
CREATE INDEX idx_task_status ON collaboration_tasks(status);

-- Create conversation_history table
CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    tools_used JSON DEFAULT '[]',
    tool_results JSON DEFAULT '{}',
    
    -- Performance metrics
    tokens_used INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional context
    metadata JSON DEFAULT '{}',
    
    FOREIGN KEY (task_id) REFERENCES collaboration_tasks(task_id) ON DELETE CASCADE
);

-- Create indexes for conversation history
CREATE INDEX idx_conv_task_id ON conversation_history(task_id);
CREATE INDEX idx_conv_agent_id ON conversation_history(agent_id);
CREATE INDEX idx_conv_created ON conversation_history(created_at);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    files_affected JSON DEFAULT '[]',
    
    -- API/Tool usage
    api_calls_made JSON DEFAULT '[]',
    tools_invoked JSON DEFAULT '[]',
    
    -- Performance
    execution_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Additional data
    metadata JSON DEFAULT '{}',
    
    FOREIGN KEY (task_id) REFERENCES collaboration_tasks(task_id) ON DELETE SET NULL
);

-- Create indexes for audit logs
CREATE INDEX idx_audit_audit_id ON audit_logs(audit_id);
CREATE INDEX idx_audit_task_id ON audit_logs(task_id);
CREATE INDEX idx_audit_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_agent_id ON audit_logs(agent_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);
CREATE INDEX idx_audit_session ON audit_logs(session_id);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER update_task_timestamp 
AFTER UPDATE ON collaboration_tasks
FOR EACH ROW
WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE collaboration_tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;