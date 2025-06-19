"""
Task Storage Models for Persistent Multi-Agent Collaboration
Enhanced database-backed storage replacing in-memory TASKS dictionary
"""

from datetime import datetime
from sqlalchemy import Column, String, JSON, DateTime, Text, Integer, Float, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from models.core import db
import uuid


class CollaborationTask(db.Model):
    """
    Main task storage model replacing the TASKS dictionary
    Enhanced version with full persistence and relationships
    """
    __tablename__ = 'collaboration_tasks'
    
    # Primary identifiers
    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Task metadata
    description = Column(Text, nullable=False)
    session_id = Column(String(255), nullable=False, index=True)
    working_directory = Column(String(1000))
    
    # Status tracking
    status = Column(String(50), nullable=False, default='pending', index=True)
    progress = Column(Integer, default=0)
    current_phase = Column(String(255), default='Initializing')
    
    # Agent information
    model_id = Column(String(100), default='openai/gpt-4')
    agents_involved = Column(JSON, default=list)
    primary_agent = Column(String(100))
    sequential = Column(Boolean, default=False)
    
    # Results and output
    results = Column(JSON, default=dict)
    summary = Column(Text)
    error_message = Column(Text)
    final_result = Column(Text)
    
    # File tracking
    files_created = Column(JSON, default=list)
    files_modified = Column(JSON, default=list)
    files_deleted = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Performance metrics
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    execution_time_seconds = Column(Float)
    
    # Additional metadata
    task_metadata = Column(JSON, default=dict)  # renamed from `metadata`
    tags = Column(JSON, default=list)
    priority = Column(String(20), default='medium')
    
    # Legacy fields for compatibility
    agents = Column(JSON, default=list)  # List of agent IDs
    conversations = Column(JSON, default=list)
    all_communications = Column(JSON, default=list)
    messages = Column(JSON, default=list)
    
    # Relationships
    conversation_history = relationship('ConversationHistory', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = relationship('AuditLog', backref='task', lazy='dynamic', cascade='all, delete-orphan')
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_task_session_status', 'session_id', 'status'),
        Index('idx_task_created', 'created_at'),
    )
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'status': self.status,
            'progress': self.progress,
            'current_phase': self.current_phase,
            'task_description': self.task_description,
            'agents': self.agents or [],
            'working_directory': self.working_directory,
            'sequential': self.sequential,
            'conversations': self.conversations or [],
            'all_communications': self.all_communications or [],
            'messages': self.messages or [],
            'results': self.results or {},
            'final_result': self.final_result,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            # keep external contract
            'metadata': self.task_metadata
        }
    
    @classmethod
    def create_task(cls, task_id, task_description=None, agents=None, working_directory=None, sequential=False):
        """Create a new task"""
        task = cls(
            id=task_id,
            task_description=task_description,
            agents=agents or [],
            working_directory=working_directory,
            sequential=sequential
        )
        db.session.add(task)
        db.session.commit()
        return task
    
    @classmethod
    def get_task(cls, task_id):
        """Get a task by ID"""
        return cls.query.get(task_id)
    
    @classmethod
    def update_task(cls, task_id, **kwargs):
        """Update a task"""
        task = cls.query.get(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.utcnow()
            db.session.commit()
        return task
    
    def update_status(self, status, phase=None, progress=None):
        """Update task status and optionally phase/progress"""
        self.status = status
        if phase is not None:
            self.current_phase = phase
        if progress is not None:
            self.progress = progress
        if status in ['completed', 'error', 'cancelled']:
            self.completed_at = datetime.utcnow()
            if self.created_at:
                self.execution_time_seconds = (self.completed_at - self.created_at).total_seconds()
    
    @classmethod
    def delete_old_tasks(cls, days=30):
        """Delete tasks older than specified days"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        old_tasks = cls.query.filter(cls.created_at < cutoff).all()
        for task in old_tasks:
            db.session.delete(task)
        db.session.commit()
        return len(old_tasks)


class ConversationHistory(db.Model):
    """
    Store conversation history between agents for each task
    Enables agents to remember past interactions
    """
    __tablename__ = 'conversation_history'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(255), ForeignKey('collaboration_tasks.task_id'), nullable=False, index=True)
    conversation_id = Column(String(255), unique=True, nullable=False)
    
    # Conversation metadata
    agent_id = Column(String(100), nullable=False, index=True)
    agent_role = Column(String(100))
    phase = Column(String(255))
    
    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Tool usage
    tools_used = Column(JSON, default=list)
    tool_results = Column(JSON, default=dict)
    
    # Performance metrics
    tokens_used = Column(Integer, default=0)
    response_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Additional context
    conversation_metadata = Column(JSON, default=dict)
    
    def __init__(self, **kwargs):
        """Initialize with auto-generated conversation ID"""
        if 'conversation_id' not in kwargs:
            kwargs['conversation_id'] = f"conv_{uuid.uuid4().hex[:8]}"
        if 'metadata' in kwargs:
            kwargs['conversation_metadata'] = kwargs.pop('metadata')
        super().__init__(**kwargs)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'conversation_id': self.conversation_id,
            'task_id': self.task_id,
            'agent_id': self.agent_id,
            'agent_role': self.agent_role,
            'phase': self.phase,
            'role': self.role,
            'content': self.content,
            'tools_used': self.tools_used,
            'tool_results': self.tool_results,
            'tokens_used': self.tokens_used,
            'response_time_ms': self.response_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.conversation_metadata
        }


class AuditLog(db.Model):
    """
    Comprehensive audit trail for all actions performed by agents
    Provides permanent record of all operations
    """
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    audit_id = Column(String(255), unique=True, nullable=False, index=True)
    task_id = Column(String(255), ForeignKey('collaboration_tasks.task_id'), nullable=True, index=True)
    
    # Action details
    action_type = Column(String(100), nullable=False, index=True)
    action_description = Column(Text, nullable=False)
    agent_id = Column(String(100), nullable=False, index=True)
    
    # Context
    session_id = Column(String(255), index=True)
    user_id = Column(String(255))
    ip_address = Column(String(45))
    
    # Results
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # File operations
    files_affected = Column(JSON, default=list)
    
    # API/Tool usage
    api_calls_made = Column(JSON, default=list)
    tools_invoked = Column(JSON, default=list)
    
    # Performance
    execution_time_ms = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Additional data
    task_metadata = Column(JSON, default=dict)  # renamed from `metadata`
    
    def __init__(self, **kwargs):
        """Initialize with auto-generated audit ID"""
        if 'audit_id' not in kwargs:
            kwargs['audit_id'] = f"audit_{uuid.uuid4().hex[:8]}"
        super().__init__(**kwargs)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'audit_id': self.audit_id,
            'task_id': self.task_id,
            'action_type': self.action_type,
            'action_description': self.action_description,
            'agent_id': self.agent_id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'success': self.success,
            'error_message': self.error_message,
            'files_affected': self.files_affected,
            'api_calls_made': self.api_calls_made,
            'tools_invoked': self.tools_invoked,
            'execution_time_ms': self.execution_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            # Preserve API contract
            'metadata': self.task_metadata
        }


# Compatibility alias for existing code
TaskStorage = CollaborationTask


# Helper functions for common operations

def create_task(description, session_id, **kwargs):
    """Create and persist a new task"""
    task_id = kwargs.pop('task_id', f"task_{uuid.uuid4().hex[:8]}")
    task = CollaborationTask(
        task_id=task_id,
        description=description,
        session_id=session_id,
        **kwargs
    )
    db.session.add(task)
    db.session.commit()
    return task

def get_task(task_id):
    """Get task by ID"""
    return CollaborationTask.query.filter_by(task_id=task_id).first()

def update_task_status(task_id, status, **kwargs):
    """Update task status and other fields"""
    task = get_task(task_id)
    if task:
        task.status = status
        task.updated_at = datetime.utcnow()
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        db.session.commit()
    return task

def add_conversation(task_id, agent_id, role, content, **kwargs):
    """Add conversation history entry"""
    conv = ConversationHistory(
        task_id=task_id,
        agent_id=agent_id,
        role=role,
        content=content,
        **kwargs
    )
    db.session.add(conv)
    db.session.commit()
    return conv

def log_action(action_type, action_description, agent_id, **kwargs):
    """Log an action for audit trail"""
    log = AuditLog(
        action_type=action_type,
        action_description=action_description,
        agent_id=agent_id,
        **kwargs
    )
    db.session.add(log)
    db.session.commit()
    return log

def get_task_conversations(task_id):
    """Get all conversations for a task"""
    return ConversationHistory.query.filter_by(task_id=task_id).order_by(ConversationHistory.created_at).all()

def get_agent_history(agent_id, limit=50):
    """Get recent conversation history for an agent"""
    return ConversationHistory.query.filter_by(agent_id=agent_id).order_by(ConversationHistory.created_at.desc()).limit(limit).all()