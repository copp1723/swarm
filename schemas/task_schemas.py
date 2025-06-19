"""
Task Validation Schemas
Marshmallow schemas for task-related validation
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from datetime import datetime, timedelta
from typing import Optional


class TaskRequirementsSchema(Schema):
    """Schema for task requirements validation"""
    tools = fields.List(fields.String(), required=False)
    capabilities = fields.List(fields.String(), required=False)
    dependencies = fields.List(fields.String(), required=False)
    estimated_duration = fields.String(required=False)
    
    @validates('estimated_duration')
    def validate_duration(self, value):
        """Validate duration format (e.g., '2h', '30m', '1d')"""
        if value:
            import re
            pattern = r'^\d+[hdmw]$'  # hours, days, minutes, weeks
            if not re.match(pattern, value):
                raise ValidationError("Invalid duration format. Use format like '2h', '30m', '1d'")


class EmailMetadataSchema(Schema):
    """Schema for email metadata validation"""
    message_id = fields.String(required=True)
    sender = fields.Email(required=True)
    recipient = fields.Email(required=False)
    subject = fields.String(required=False)
    timestamp = fields.DateTime(required=False)
    
    @post_load
    def add_timestamp(self, data, **kwargs):
        """Add timestamp if not provided"""
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        return data


class TaskCreateSchema(Schema):
    """Schema for task creation validation"""
    title = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200)
    )
    description = fields.String(
        required=True,
        validate=validate.Length(min=1)
    )
    task_type = fields.String(
        required=False,
        default='GENERAL',
        validate=validate.OneOf([
            'CODING', 'DEBUGGING', 'TESTING', 'DOCUMENTATION',
            'REVIEW', 'DEPLOYMENT', 'MONITORING', 'GENERAL'
        ])
    )
    priority = fields.String(
        required=False,
        default='MEDIUM',
        validate=validate.OneOf(['LOW', 'MEDIUM', 'HIGH', 'URGENT'])
    )
    status = fields.String(
        required=False,
        default='pending',
        validate=validate.OneOf([
            'pending', 'in_progress', 'completed', 
            'failed', 'cancelled', 'blocked'
        ])
    )
    assigned_agent = fields.String(required=False)
    deadline = fields.DateTime(required=False)
    requirements = fields.Nested(TaskRequirementsSchema, required=False)
    tags = fields.List(fields.String(), required=False)
    source = fields.String(
        required=False,
        default='manual',
        validate=validate.OneOf(['email', 'webhook', 'api', 'manual', 'scheduled'])
    )
    email_metadata = fields.Nested(EmailMetadataSchema, required=False)
    
    @validates('deadline')
    def validate_deadline(self, value):
        """Ensure deadline is in the future"""
        if value and value < datetime.utcnow():
            raise ValidationError("Deadline must be in the future")
    
    @validates('title')
    def validate_title(self, value):
        """Ensure title is not just whitespace"""
        if not value.strip():
            raise ValidationError("Title cannot be empty or just whitespace")
    
    @post_load
    def process_task(self, data, **kwargs):
        """Post-process task data"""
        # Generate task ID
        import uuid
        data['id'] = str(uuid.uuid4())
        
        # Add creation timestamp
        data['created_at'] = datetime.utcnow()
        
        # Set default deadline if not provided
        if 'deadline' not in data:
            # Default to 7 days from now for non-urgent tasks
            if data.get('priority') == 'URGENT':
                data['deadline'] = datetime.utcnow() + timedelta(days=1)
            else:
                data['deadline'] = datetime.utcnow() + timedelta(days=7)
        
        return data


class TaskUpdateSchema(Schema):
    """Schema for task update validation"""
    title = fields.String(validate=validate.Length(min=1, max=200))
    description = fields.String(validate=validate.Length(min=1))
    status = fields.String(
        validate=validate.OneOf([
            'pending', 'in_progress', 'completed', 
            'failed', 'cancelled', 'blocked'
        ])
    )
    priority = fields.String(
        validate=validate.OneOf(['LOW', 'MEDIUM', 'HIGH', 'URGENT'])
    )
    assigned_agent = fields.String()
    deadline = fields.DateTime()
    progress = fields.Integer(validate=validate.Range(min=0, max=100))
    notes = fields.String()
    tags = fields.List(fields.String())
    
    @validates('deadline')
    def validate_deadline(self, value):
        """Allow past deadlines for updates (task might be overdue)"""
        if value and value < datetime.utcnow() - timedelta(days=365):
            raise ValidationError("Deadline seems unreasonably far in the past")
    
    @post_load
    def add_update_timestamp(self, data, **kwargs):
        """Add update timestamp"""
        data['updated_at'] = datetime.utcnow()
        return data


class TaskQuerySchema(Schema):
    """Schema for task query validation"""
    status = fields.String(
        validate=validate.OneOf([
            'pending', 'in_progress', 'completed', 
            'failed', 'cancelled', 'blocked', 'all'
        ])
    )
    assigned_agent = fields.String()
    priority = fields.String(
        validate=validate.OneOf(['LOW', 'MEDIUM', 'HIGH', 'URGENT', 'all'])
    )
    task_type = fields.String()
    tags = fields.List(fields.String())
    created_after = fields.DateTime()
    created_before = fields.DateTime()
    deadline_before = fields.DateTime()
    limit = fields.Integer(validate=validate.Range(min=1, max=100), default=20)
    offset = fields.Integer(validate=validate.Range(min=0), default=0)
    sort_by = fields.String(
        validate=validate.OneOf(['created_at', 'deadline', 'priority', 'status']),
        default='created_at'
    )
    sort_order = fields.String(
        validate=validate.OneOf(['asc', 'desc']),
        default='desc'
    )
    
    @validates('created_before')
    def validate_date_range(self, value):
        """Ensure date range is valid"""
        created_after = self.context.get('created_after')
        if created_after and value and value < created_after:
            raise ValidationError("created_before must be after created_after")


class TaskBulkOperationSchema(Schema):
    """Schema for bulk task operations"""
    task_ids = fields.List(
        fields.String(),
        required=True,
        validate=validate.Length(min=1, max=100)
    )
    operation = fields.String(
        required=True,
        validate=validate.OneOf([
            'delete', 'archive', 'assign', 'update_status', 
            'update_priority', 'add_tags', 'remove_tags'
        ])
    )
    parameters = fields.Dict(required=False)
    
    @validates('parameters')
    def validate_parameters(self, value):
        """Validate parameters based on operation"""
        operation = self.context.get('operation')
        
        if operation == 'assign' and not value.get('agent_id'):
            raise ValidationError("agent_id required for assign operation")
        
        if operation == 'update_status' and not value.get('status'):
            raise ValidationError("status required for update_status operation")
        
        if operation == 'update_priority' and not value.get('priority'):
            raise ValidationError("priority required for update_priority operation")
        
        if operation in ['add_tags', 'remove_tags'] and not value.get('tags'):
            raise ValidationError("tags required for tag operations")


# Validation helper functions
def validate_task_create(data: dict) -> dict:
    """Validate task creation data"""
    schema = TaskCreateSchema()
    return schema.load(data)


def validate_task_update(data: dict) -> dict:
    """Validate task update data"""
    schema = TaskUpdateSchema()
    return schema.load(data)


def validate_task_query(data: dict) -> dict:
    """Validate task query parameters"""
    schema = TaskQuerySchema()
    return schema.load(data)


def validate_bulk_operation(data: dict) -> dict:
    """Validate bulk operation data"""
    schema = TaskBulkOperationSchema()
    return schema.load(data)