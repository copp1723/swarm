"""
Agent Validation Schemas
Marshmallow schemas for agent-related request/response validation
"""

from marshmallow import Schema, fields, validate, validates, ValidationError, post_load
from typing import List, Optional
from config.agents import AGENT_PROFILES, AGENT_ROLES


class ChatMessageSchema(Schema):
    """Schema for chat message validation"""
    role = fields.String(
        required=True,
        validate=validate.OneOf(['user', 'assistant', 'system'])
    )
    content = fields.String(required=True, validate=validate.Length(min=1))
    name = fields.String(required=False)
    metadata = fields.Dict(required=False)
    
    @validates('content')
    def validate_content(self, value):
        """Ensure content is not just whitespace"""
        if not value.strip():
            raise ValidationError("Content cannot be empty or just whitespace")


class ChatRequestSchema(Schema):
    """Schema for chat request validation"""
    messages = fields.List(
        fields.Nested(ChatMessageSchema),
        required=True,
        validate=validate.Length(min=1)
    )
    model = fields.String(required=False)
    temperature = fields.Float(
        required=False,
        validate=validate.Range(min=0.0, max=2.0)
    )
    max_tokens = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=32000)
    )
    stream = fields.Boolean(required=False, default=False)
    
    # Agent-specific fields
    agent_id = fields.String(required=False)
    agent_role = fields.String(
        required=False,
        validate=validate.OneOf(AGENT_ROLES)
    )
    
    @validates('messages')
    def validate_messages(self, value):
        """Ensure at least one user message exists"""
        user_messages = [m for m in value if m.get('role') == 'user']
        if not user_messages:
            raise ValidationError("At least one user message is required")


class AgentRequestSchema(Schema):
    """Schema for agent-specific requests"""
    agent_id = fields.String(required=False)
    agent_role = fields.String(
        required=True,
        validate=validate.OneOf(AGENT_ROLES)
    )
    task = fields.String(required=True, validate=validate.Length(min=1))
    context = fields.Dict(required=False)
    parameters = fields.Dict(required=False)
    
    @validates('agent_role')
    def validate_agent_exists(self, value):
        """Ensure agent role exists in configuration"""
        if value not in AGENT_PROFILES:
            raise ValidationError(f"Unknown agent role: {value}")


class MultiAgentConversationSchema(Schema):
    """Schema for multi-agent conversation requests"""
    conversation_id = fields.String(required=False)
    agents = fields.List(
        fields.String(validate=validate.OneOf(AGENT_ROLES)),
        required=True,
        validate=validate.Length(min=2)
    )
    initial_message = fields.String(required=True, validate=validate.Length(min=1))
    context = fields.Dict(required=False)
    max_turns = fields.Integer(
        required=False,
        default=10,
        validate=validate.Range(min=1, max=50)
    )
    
    @validates('agents')
    def validate_unique_agents(self, value):
        """Ensure agent list has unique roles"""
        if len(value) != len(set(value)):
            raise ValidationError("Duplicate agents in conversation")


class TaskAssignmentSchema(Schema):
    """Schema for task assignment validation"""
    task_id = fields.String(required=False)
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(required=True, validate=validate.Length(min=1))
    assigned_agent = fields.String(
        required=True,
        validate=validate.OneOf(AGENT_ROLES)
    )
    priority = fields.String(
        required=False,
        default='medium',
        validate=validate.OneOf(['low', 'medium', 'high', 'urgent'])
    )
    due_date = fields.DateTime(required=False)
    tags = fields.List(fields.String(), required=False)
    dependencies = fields.List(fields.String(), required=False)
    
    @post_load
    def process_task(self, data, **kwargs):
        """Post-process task data"""
        # Generate task ID if not provided
        if 'task_id' not in data:
            import uuid
            data['task_id'] = str(uuid.uuid4())
        return data


class AgentCapabilitySchema(Schema):
    """Schema for agent capability queries"""
    agent_role = fields.String(
        required=True,
        validate=validate.OneOf(AGENT_ROLES)
    )
    capability = fields.String(required=True)
    
    @validates('capability')
    def validate_capability(self, value):
        """Validate capability format"""
        if not value or not isinstance(value, str):
            raise ValidationError("Invalid capability")


class AgentSelectionSchema(Schema):
    """Schema for automatic agent selection"""
    task_description = fields.String(required=True, validate=validate.Length(min=10))
    required_capabilities = fields.List(fields.String(), required=False)
    preferred_models = fields.List(fields.String(), required=False)
    exclude_agents = fields.List(
        fields.String(validate=validate.OneOf(AGENT_ROLES)),
        required=False
    )
    
    @validates('task_description')
    def validate_task_description(self, value):
        """Ensure task description is meaningful"""
        word_count = len(value.split())
        if word_count < 3:
            raise ValidationError("Task description must contain at least 3 words")


class AgentResponseSchema(Schema):
    """Schema for agent response validation"""
    agent_id = fields.String(required=True)
    agent_role = fields.String(required=True)
    response = fields.String(required=True)
    confidence = fields.Float(
        required=False,
        validate=validate.Range(min=0.0, max=1.0)
    )
    metadata = fields.Dict(required=False)
    tools_used = fields.List(fields.String(), required=False)
    processing_time = fields.Float(required=False)
    
    @post_load
    def add_timestamp(self, data, **kwargs):
        """Add timestamp to response"""
        from datetime import datetime
        data['timestamp'] = datetime.utcnow().isoformat()
        return data


class ConversationContextSchema(Schema):
    """Schema for conversation context management"""
    conversation_id = fields.String(required=True)
    agent_id = fields.String(required=False)
    include_memories = fields.Boolean(required=False, default=True)
    memory_limit = fields.Integer(
        required=False,
        default=10,
        validate=validate.Range(min=1, max=100)
    )
    time_range_hours = fields.Integer(
        required=False,
        validate=validate.Range(min=1, max=168)  # Max 1 week
    )


# Validation helper functions
def validate_agent_request(data: dict) -> dict:
    """Validate agent request data"""
    schema = AgentRequestSchema()
    return schema.load(data)


def validate_chat_request(data: dict) -> dict:
    """Validate chat request data"""
    schema = ChatRequestSchema()
    return schema.load(data)


def validate_multi_agent_conversation(data: dict) -> dict:
    """Validate multi-agent conversation request"""
    schema = MultiAgentConversationSchema()
    return schema.load(data)


def validate_task_assignment(data: dict) -> dict:
    """Validate task assignment data"""
    schema = TaskAssignmentSchema()
    return schema.load(data)