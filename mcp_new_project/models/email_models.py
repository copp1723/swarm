"""
Email Database Models
Models for email drafts and logs
"""

from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from models.core import db


class EmailDraft(db.Model):
    """Email draft model for review workflow"""
    __tablename__ = 'email_drafts'
    
    id = db.Column(db.Integer, primary_key=True)
    draft_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
    # Recipients
    recipients = db.Column(JSON, nullable=False)  # List of {email, name} objects
    subject = db.Column(db.String(500), nullable=False)
    body = db.Column(db.Text, nullable=False)
    html = db.Column(db.Text)
    
    # Attachments and metadata
    attachments = db.Column(JSON, default=list)  # List of attachment objects
    email_metadata = db.Column(JSON, default=dict)  # cc, bcc, headers, tags, etc.
    
    # Status tracking
    status = db.Column(db.String(20), default='draft', index=True)
    # Possible statuses: draft, revised, approved, rejected, sent, failed
    
    # Workflow tracking
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by = db.Column(db.String(100))
    reviewed_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    
    # Review details
    review_comments = db.Column(db.Text)
    revisions = db.Column(JSON)  # Track what was changed
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'draft_id': self.draft_id,
            'recipients': self.recipients,
            'subject': self.subject,
            'body': self.body,
            'html': self.html,
            'attachments': self.attachments,
            'metadata': self.email_metadata,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'review_comments': self.review_comments,
            'revisions': self.revisions
        }


class EmailLog(db.Model):
    """Email sending log for tracking and analytics"""
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Email details
    recipient = db.Column(db.String(255), nullable=False, index=True)
    subject = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, index=True)
    # Possible statuses: pending, sent, delivered, failed, bounced
    
    # Provider details
    provider = db.Column(db.String(50))  # mailgun, apprise, etc.
    message_id = db.Column(db.String(255), index=True)  # Provider's message ID
    
    # Timestamps
    sent_at = db.Column(db.DateTime, index=True)
    delivered_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    
    # Engagement metrics
    open_count = db.Column(db.Integer, default=0)
    click_count = db.Column(db.Integer, default=0)
    
    # Error tracking
    error = db.Column(db.Text)
    error_code = db.Column(db.String(50))
    
    # Additional data
    email_metadata = db.Column(JSON, default=dict)  # cc, tags, priority, etc.
    
    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_email_logs_sent_at_status', sent_at, status),
        db.Index('idx_email_logs_recipient_sent_at', recipient, sent_at),
    )
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'recipient': self.recipient,
            'subject': self.subject,
            'status': self.status,
            'provider': self.provider,
            'message_id': self.message_id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'clicked_at': self.clicked_at.isoformat() if self.clicked_at else None,
            'open_count': self.open_count,
            'click_count': self.click_count,
            'error': self.error,
            'error_code': self.error_code,
            'metadata': self.email_metadata
        }


class EmailTemplate(db.Model):
    """Email template model for reusable templates"""
    __tablename__ = 'email_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Template content
    subject_template = db.Column(db.String(500), nullable=False)
    body_template = db.Column(db.Text, nullable=False)
    html_template = db.Column(db.Text)
    
    # Variables schema
    variables_schema = db.Column(JSON)  # Expected variables and their types
    
    # Metadata
    category = db.Column(db.String(50), index=True)
    tags = db.Column(JSON, default=list)
    is_active = db.Column(db.Boolean, default=True)
    
    # Tracking
    created_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Usage statistics
    usage_count = db.Column(db.Integer, default=0)
    last_used_at = db.Column(db.DateTime)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'name': self.name,
            'description': self.description,
            'subject_template': self.subject_template,
            'body_template': self.body_template,
            'html_template': self.html_template,
            'variables_schema': self.variables_schema,
            'category': self.category,
            'tags': self.tags,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'usage_count': self.usage_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }