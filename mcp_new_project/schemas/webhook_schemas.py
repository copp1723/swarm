"""
Webhook Validation Schemas
Marshmallow schemas for webhook payload validation
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from typing import Dict, Any
import re


class MailgunSignatureSchema(Schema):
    """Schema for Mailgun webhook signature fields"""
    signature = fields.Dict(required=True)
    timestamp = fields.String(required=True)
    token = fields.String(required=True)
    
    @validates('signature')
    def validate_signature(self, value):
        """Validate signature structure"""
        required_keys = ['timestamp', 'token', 'signature']
        missing_keys = [k for k in required_keys if k not in value]
        if missing_keys:
            raise ValidationError(f"Missing signature keys: {missing_keys}")


class EmailAddressField(fields.Field):
    """Custom field for email validation"""
    
    def _validate(self, value):
        if not value:
            return
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, value):
            raise ValidationError(f"Invalid email address: {value}")
    
    def _serialize(self, value, attr, obj, **kwargs):
        return str(value) if value else None
    
    def _deserialize(self, value, attr, data, **kwargs):
        self._validate(value)
        return value


class EmailWebhookBaseSchema(Schema):
    """Base schema for email webhook events"""
    event = fields.String(
        required=True,
        validate=validate.OneOf([
            'delivered', 'opened', 'clicked', 'bounced',
            'complained', 'unsubscribed', 'failed', 'dropped'
        ])
    )
    recipient = EmailAddressField(required=True)
    sender = EmailAddressField(required=False)
    domain = fields.String(required=False)
    timestamp = fields.Float(required=False)
    
    # Common optional fields
    user_variables = fields.Dict(required=False)
    message_headers = fields.List(fields.List(fields.String()), required=False)
    
    class Meta:
        unknown = 'include'  # Include unknown fields


class MailgunDeliveredSchema(EmailWebhookBaseSchema):
    """Schema for Mailgun delivered event"""
    # Delivered-specific fields
    message_id = fields.String(required=True, data_key='message-id')
    
    @post_load
    def make_delivered_event(self, data, **kwargs):
        """Post-process delivered event data"""
        data['event_type'] = 'delivered'
        return data


class MailgunBouncedSchema(EmailWebhookBaseSchema):
    """Schema for Mailgun bounced event"""
    error = fields.String(required=False)
    code = fields.Integer(required=False)
    notification = fields.String(required=False)
    
    @validates('code')
    def validate_bounce_code(self, value):
        """Validate bounce code is in valid range"""
        if value and (value < 100 or value > 599):
            raise ValidationError(f"Invalid bounce code: {value}")
    
    @post_load
    def make_bounced_event(self, data, **kwargs):
        """Post-process bounced event data"""
        data['event_type'] = 'bounced'
        # Determine bounce type
        if data.get('code'):
            data['bounce_type'] = 'hard' if data['code'] >= 500 else 'soft'
        return data


class MailgunClickedSchema(EmailWebhookBaseSchema):
    """Schema for Mailgun clicked event"""
    url = fields.URL(required=True)
    ip = fields.String(required=False)
    user_agent = fields.String(required=False, data_key='user-agent')
    
    @post_load
    def make_clicked_event(self, data, **kwargs):
        """Post-process clicked event data"""
        data['event_type'] = 'clicked'
        return data


class MailgunComplainedSchema(EmailWebhookBaseSchema):
    """Schema for Mailgun spam complaint event"""
    campaign_id = fields.String(required=False, data_key='campaign-id')
    campaign_name = fields.String(required=False, data_key='campaign-name')
    
    @post_load
    def make_complained_event(self, data, **kwargs):
        """Post-process complained event data"""
        data['event_type'] = 'complained'
        return data


class MailgunUnsubscribedSchema(EmailWebhookBaseSchema):
    """Schema for Mailgun unsubscribed event"""
    campaign_id = fields.String(required=False, data_key='campaign-id')
    campaign_name = fields.String(required=False, data_key='campaign-name')
    tag = fields.String(required=False)
    
    @post_load
    def make_unsubscribed_event(self, data, **kwargs):
        """Post-process unsubscribed event data"""
        data['event_type'] = 'unsubscribed'
        return data


class ConvoyWebhookSchema(Schema):
    """Schema for Convoy webhook gateway events"""
    event_type = fields.String(required=True)
    data = fields.Dict(required=True)
    metadata = fields.Dict(required=False)
    timestamp = fields.String(required=False)
    
    # Convoy-specific fields
    project_id = fields.String(required=False)
    endpoint_id = fields.String(required=False)
    event_id = fields.String(required=False)
    
    @validates('event_type')
    def validate_event_type(self, value):
        """Validate event type format"""
        if not value or not isinstance(value, str):
            raise ValidationError("Invalid event type")


class WebhookRequestSchema(Schema):
    """Schema for generic webhook request validation"""
    webhook_type = fields.String(
        required=True,
        validate=validate.OneOf(['mailgun', 'convoy', 'github', 'slack'])
    )
    payload = fields.Dict(required=True)
    headers = fields.Dict(required=False)
    source_ip = fields.String(required=False)
    
    @validates('payload')
    def validate_payload(self, value):
        """Ensure payload is not empty"""
        if not value:
            raise ValidationError("Payload cannot be empty")


# Event type to schema mapping
MAILGUN_EVENT_SCHEMAS = {
    'delivered': MailgunDeliveredSchema,
    'bounced': MailgunBouncedSchema,
    'clicked': MailgunClickedSchema,
    'complained': MailgunComplainedSchema,
    'unsubscribed': MailgunUnsubscribedSchema,
    # Use base schema for other events
    'opened': EmailWebhookBaseSchema,
    'failed': EmailWebhookBaseSchema,
    'dropped': EmailWebhookBaseSchema,
}


def get_mailgun_schema(event_type: str) -> Schema:
    """Get appropriate schema for Mailgun event type"""
    return MAILGUN_EVENT_SCHEMAS.get(event_type, EmailWebhookBaseSchema)()


def validate_mailgun_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Mailgun webhook data.
    
    Args:
        data: Raw webhook data
        
    Returns:
        Validated and processed data
        
    Raises:
        ValidationError: If validation fails
    """
    # First check if we have an event type
    event_type = data.get('event')
    if not event_type:
        raise ValidationError({'event': ['Missing required field']})
    
    # Get appropriate schema
    schema = get_mailgun_schema(event_type)
    
    # Validate and return processed data
    return schema.load(data)


def validate_convoy_webhook(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Convoy webhook data.
    
    Args:
        data: Raw webhook data
        
    Returns:
        Validated data
        
    Raises:
        ValidationError: If validation fails
    """
    schema = ConvoyWebhookSchema()
    return schema.load(data)