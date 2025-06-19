from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class TaskRecord(db.Model):
    """Persistent storage for in-progress multi-agent task statuses."""
    __tablename__ = 'task_records'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    status = db.Column(db.String(50), nullable=False, index=True)  # running, completed, error
    progress = db.Column(db.Integer, default=0)
    current_phase = db.Column(db.String(255), default="Starting")
    results = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Return task status as dictionary."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "current_phase": self.current_phase,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def update_status(self, status_dict):
        """Update task status with individual fields."""
        self.status = status_dict.get("status", self.status)
        self.progress = status_dict.get("progress", self.progress)
        self.current_phase = status_dict.get("current_phase", self.current_phase)
        self.results = status_dict.get("results", self.results)
        self.updated_at = datetime.utcnow()

class CompletedTask(db.Model):
    """Store completed collaboration tasks for review."""
    __tablename__ = 'completed_tasks'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    task_description = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.String(255), nullable=False, index=True)
    working_directory = db.Column(db.String(1000))
    status = db.Column(db.String(50), nullable=False, index=True)  # completed, error, cancelled
    agents_used = db.Column(db.JSON, default=list)
    model_used = db.Column(db.String(100))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration_seconds = db.Column(db.Float, nullable=False)
    task_summary = db.Column(db.Text)
    agent_conversations = db.Column(db.JSON, default=list)
    results = db.Column(db.JSON, default=dict)
    error_message = db.Column(db.Text)
    total_messages = db.Column(db.Integer, default=0)
    files_modified = db.Column(db.JSON, default=list)
    tools_used = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_description': self.task_description,
            'session_id': self.session_id,
            'working_directory': self.working_directory,
            'status': self.status,
            'agents_used': self.agents_used,
            'model_used': self.model_used,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': self.duration_seconds,
            'task_summary': self.task_summary,
            'agent_conversations': self.agent_conversations,
            'results': self.results,
            'error_message': self.error_message,
            'total_messages': self.total_messages,
            'files_modified': self.files_modified,
            'tools_used': self.tools_used,
            'created_at': self.created_at.isoformat()
        }