"""
Email Validation Schemas
Marshmallow schemas for email-related validation
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from datetime import datetime
from typing import List, Dict, Any, Optional


class EmailAddressSchema(Schema):
    """Schema for email address validation with optional name"""
    email = fields.Email(required=True)
    name = fields.String(required=False)
    
    @post_load
    def format_address(self, data, **kwargs):
        """Format as 'Name <email>' if name provided"""
        if data.get('name'):
            data['formatted'] = f"{data['name']} <{data['email']}>"
        else:
            data['formatted'] = data['email']
        return data


class EmailAttachmentSchema(Schema):
    """Schema for email attachment validation"""
    filename = fields.String(
        required=True,
        validate=validate.Length(min=1, max=255)
    )
    content = fields.String(required=True)  # Base64 encoded
    content_type = fields.String(
        required=False,
        default='application/octet-stream'
    )
    size = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=25*1024*1024)  # 25MB max
    )
    
    @validates('content')
    def validate_base64(self, value):
        """Validate base64 encoding"""
        import base64
        try:
            base64.b64decode(value, validate=True)
        except Exception:
            raise ValidationError("Content must be valid base64 encoded")


class EmailDraftSchema(Schema):
    """Schema for email draft creation"""
    to = fields.List(
        fields.Nested(EmailAddressSchema),
        required=True,
        validate=validate.Length(min=1)
    )
    cc = fields.List(fields.Nested(EmailAddressSchema), required=False)
    bcc = fields.List(fields.Nested(EmailAddressSchema), required=False)
    subject = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500)
    )
    body = fields.String(
        required=True,
        validate=validate.Length(min=1)
    )
    html = fields.String(required=False)
    reply_to = fields.Nested(EmailAddressSchema, required=False)
    attachments = fields.List(
        fields.Nested(EmailAttachmentSchema),
        required=False,
        validate=validate.Length(max=10)  # Max 10 attachments
    )
    tags = fields.List(
        fields.String(validate=validate.Length(max=50)),
        required=False,
        validate=validate.Length(max=3)  # Mailgun limit
    )
    headers = fields.Dict(
        keys=fields.String(validate=validate.Length(max=100)),
        values=fields.String(validate=validate.Length(max=1000)),
        required=False
    )
    template_id = fields.String(required=False)
    template_variables = fields.Dict(required=False)
    schedule_time = fields.DateTime(required=False)
    
    @validates('to')
    def validate_recipients(self, value):
        """Ensure at least one recipient"""
        if not value:
            raise ValidationError("At least one recipient required")
    
    @validates('schedule_time')
    def validate_schedule(self, value):
        """Ensure scheduled time is in the future"""
        if value and value <= datetime.utcnow():
            raise ValidationError("Scheduled time must be in the future")
    
    @post_load
    def process_draft(self, data, **kwargs):
        """Process draft data"""
        # Generate draft ID
        import uuid
        data['draft_id'] = str(uuid.uuid4())
        data['created_at'] = datetime.utcnow()
        data['status'] = 'draft'
        
        # Calculate total size
        total_size = len(data.get('body', '')) + len(data.get('html', ''))
        if data.get('attachments'):
            for attachment in data['attachments']:
                total_size += attachment.get('size', 0)
        
        if total_size > 50 * 1024 * 1024:  # 50MB total limit
            raise ValidationError("Total email size exceeds 50MB limit")
        
        return data


class EmailSendSchema(Schema):
    """Schema for sending email (simpler than draft)"""
    to = fields.String(required=True)  # Single recipient for simple send
    subject = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500)
    )
    body = fields.String(
        required=True,
        validate=validate.Length(min=1)
    )
    html = fields.String(required=False)
    from_email = fields.Email(required=False)
    reply_to = fields.Email(required=False)
    cc = fields.List(fields.Email(), required=False)
    bcc = fields.List(fields.Email(), required=False)
    tags = fields.List(fields.String(), required=False)
    headers = fields.Dict(required=False)
    priority = fields.String(
        required=False,
        default='normal',
        validate=validate.OneOf(['low', 'normal', 'high'])
    )
    
    @validates('to')
    def validate_to_email(self, value):
        """Validate single recipient email"""
        from marshmallow.fields import Email
        email_field = Email()
        email_field.deserialize(value, 'to')


class EmailReviewSchema(Schema):
    """Schema for email review/approval"""
    draft_id = fields.String(required=True)
    action = fields.String(
        required=True,
        validate=validate.OneOf(['approve', 'reject', 'revise'])
    )
    comments = fields.String(required=False)
    revisions = fields.Dict(required=False)  # Field updates for revise action
    reviewer = fields.String(required=True)
    
    @validates('revisions')
    def validate_revisions(self, value):
        """Ensure revisions provided for revise action"""
        action = self.context.get('action')
        if action == 'revise' and not value:
            raise ValidationError("Revisions required for revise action")


class BulkEmailSchema(Schema):
    """Schema for bulk email operations"""
    recipients = fields.List(
        fields.Dict(
            email=fields.Email(required=True),
            variables=fields.Dict(required=False)
        ),
        required=True,
        validate=validate.Length(min=1, max=1000)
    )
    template_subject = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500)
    )
    template_body = fields.String(
        required=True,
        validate=validate.Length(min=1)
    )
    template_html = fields.String(required=False)
    batch_size = fields.Integer(
        required=False,
        default=50,
        validate=validate.Range(min=1, max=100)
    )
    delay_between_batches = fields.Integer(
        required=False,
        default=1,
        validate=validate.Range(min=0, max=60)
    )
    from_email = fields.Email(required=False)
    reply_to = fields.Email(required=False)
    track_opens = fields.Boolean(default=True)
    track_clicks = fields.Boolean(default=True)
    
    @validates('template_subject')
    def validate_template_variables(self, value):
        """Validate template has valid variable syntax"""
        import re
        # Check for {variable} syntax
        variables = re.findall(r'\{(\w+)\}', value)
        if '{' in value and not variables:
            raise ValidationError("Invalid template variable syntax. Use {variable_name}")


class EmailWebhookSchema(Schema):
    """Schema for email webhook validation (Mailgun format)"""
    signature = fields.Dict(required=True)
    event_data = fields.Dict(required=True)
    
    @validates('signature')
    def validate_signature_fields(self, value):
        """Ensure required signature fields"""
        required = ['timestamp', 'token', 'signature']
        missing = [f for f in required if f not in value]
        if missing:
            raise ValidationError(f"Missing signature fields: {missing}")
    
    @validates('event_data')
    def validate_event_fields(self, value):
        """Ensure required event fields"""
        if 'event' not in value:
            raise ValidationError("Missing event field in event_data")


class EmailQuerySchema(Schema):
    """Schema for querying email history"""
    status = fields.String(
        validate=validate.OneOf(['sent', 'failed', 'pending', 'draft', 'all']),
        default='all'
    )
    date_from = fields.DateTime(required=False)
    date_to = fields.DateTime(required=False)
    recipient = fields.Email(required=False)
    sender = fields.Email(required=False)
    subject_contains = fields.String(required=False)
    tag = fields.String(required=False)
    limit = fields.Integer(
        validate=validate.Range(min=1, max=100),
        default=20
    )
    offset = fields.Integer(
        validate=validate.Range(min=0),
        default=0
    )
    
    @validates('date_to')
    def validate_date_range(self, value):
        """Ensure date range is valid"""
        date_from = self.context.get('date_from')
        if date_from and value and value < date_from:
            raise ValidationError("date_to must be after date_from")


# Validation helper functions
def validate_email_draft(data: dict) -> dict:
    """Validate email draft data"""
    schema = EmailDraftSchema()
    return schema.load(data)


def validate_email_send(data: dict) -> dict:
    """Validate email send data"""
    schema = EmailSendSchema()
    return schema.load(data)


def validate_email_review(data: dict) -> dict:
    """Validate email review data"""
    schema = EmailReviewSchema()
    return schema.load(data)


def validate_bulk_email(data: dict) -> dict:
    """Validate bulk email data"""
    schema = BulkEmailSchema()
    return schema.load(data)


def validate_email_webhook(data: dict) -> dict:
    """Validate email webhook data"""
    schema = EmailWebhookSchema()
    return schema.load(data)


def validate_email_query(data: dict) -> dict:
    """Validate email query parameters"""
    schema = EmailQuerySchema()
    return schema.load(data)