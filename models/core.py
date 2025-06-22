from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from typing import TYPE_CHECKING

# Type checking import to resolve mypy issues
if TYPE_CHECKING:
    from flask_sqlalchemy.model import Model

db = SQLAlchemy()

def _safe_json_loads(data):
    """Safely load JSON data, returning None if invalid"""
    if data is None:
        return None
    if isinstance(data, dict):
        return data
    try:
        return json.loads(data) if isinstance(data, str) else data
    except (json.JSONDecodeError, TypeError):
        return None

class Conversation(db.Model):
    """Store conversation sessions"""
    __tablename__ = 'conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(500))
    model_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'title': self.title,
            'model_id': self.model_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'message_count': db.session.query(Message).filter_by(conversation_id=self.id).count()
        }

class Message(db.Model):
    """Store individual messages in conversations"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    message_id = db.Column(db.String(255), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(100))
    tools_used = db.Column(db.JSON, default=list)
    message_metadata = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'role': self.role,
            'content': self.content,
            'model_used': self.model_used,
            'tools_used': self.tools_used,
            'message_metadata': self.message_metadata,
            'created_at': self.created_at.isoformat()
        }

class UserPreference(db.Model):
    """Store user preferences and settings"""
    __tablename__ = 'user_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False)
    preference_key = db.Column(db.String(100), nullable=False)
    preference_value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('session_id', 'preference_key', name='unique_user_preference'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'preference_key': self.preference_key,
            'preference_value': self.preference_value,
            'updated_at': self.updated_at.isoformat()
        }

class ModelUsage(db.Model):
    """Track model usage statistics"""
    __tablename__ = 'model_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.String(100), nullable=False)
    session_id = db.Column(db.String(255))
    usage_count = db.Column(db.Integer, default=1)
    total_tokens = db.Column(db.Integer, default=0)
    total_messages = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    date_created = db.Column(db.Date, default=datetime.utcnow().date())
    
    __table_args__ = (db.UniqueConstraint('model_id', 'session_id', 'date_created', name='unique_daily_usage'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'model_id': self.model_id,
            'session_id': self.session_id,
            'usage_count': self.usage_count,
            'total_tokens': self.total_tokens,
            'total_messages': self.total_messages,
            'last_used': self.last_used.isoformat(),
            'date_created': self.date_created.isoformat()
        }

class SystemLog(db.Model):
    """Store system logs and events"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    event_type = db.Column(db.String(50), nullable=False)
    event_source = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.String(255))
    additional_data = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_source': self.event_source,
            'message': self.message,
            'session_id': self.session_id,
            'additional_data': self.additional_data,
            'created_at': self.created_at.isoformat()
        }

class FileAttachment(db.Model):
    """Store file attachments for messages"""
    __tablename__ = 'file_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255), unique=True, nullable=False)
    original_filename = db.Column(db.String(500), nullable=False)
    stored_filename = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_type = db.Column(db.String(100), nullable=False)
    mime_type = db.Column(db.String(200))
    session_id = db.Column(db.String(255), nullable=False)
    message_id = db.Column(db.String(255))
    upload_path = db.Column(db.String(1000), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    download_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'session_id': self.session_id,
            'message_id': self.message_id,
            'is_public': self.is_public,
            'download_count': self.download_count,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }