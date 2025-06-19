# Email Service and Supermemory Integration

## Overview

This document describes the two new features added to the SWARM system:

1. **Email Service Integration** - Complete email functionality with draft/review workflow
2. **Supermemory Integration** - Agent-specific memory contexts for persistent knowledge

## Email Service

### Features

- **Direct Email Sending** - Send emails immediately via Mailgun or Apprise fallback
- **Draft/Review Workflow** - Create drafts that require approval before sending
- **Bulk Email Support** - Send personalized emails to multiple recipients
- **Email Templates** - Store and reuse email templates
- **Webhook Integration** - Handle Mailgun webhooks for delivery tracking
- **Complete Audit Trail** - Track all emails sent, delivered, opened, and clicked

### API Endpoints

#### Send Email
```bash
POST /api/email/send
{
    "to": "recipient@example.com",
    "subject": "Test Email",
    "body": "Email content",
    "html": "<p>Optional HTML content</p>",
    "cc": ["cc@example.com"],
    "tags": ["notification"]
}
```

#### Create Draft
```bash
POST /api/email/draft
{
    "to": [{"email": "recipient@example.com", "name": "John Doe"}],
    "subject": "Draft Email",
    "body": "Email content",
    "attachments": [{
        "filename": "report.pdf",
        "content": "base64_encoded_content",
        "content_type": "application/pdf"
    }]
}
```

#### Review Draft
```bash
POST /api/email/draft/{draft_id}/review
{
    "action": "approve|reject|revise",
    "comments": "Review comments",
    "reviewer": "reviewer_username"
}
```

#### Email History
```bash
GET /api/email/history?status=sent&limit=20
```

### Configuration

Set the following environment variables:

```bash
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=mg.yourdomain.com
MAILGUN_SIGNING_KEY=your-webhook-signing-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
```

## Supermemory Integration

### Features

- **Agent-Specific Memories** - Each agent maintains its own knowledge base
- **Memory Sharing** - Share important knowledge between agents
- **Conversation Context** - Track memories by conversation
- **Memory Consolidation** - Summarize related memories
- **Agent Profiles** - Store agent capabilities and preferences
- **Semantic Search** - Find relevant memories using natural language

### API Endpoints

#### Add Memory
```bash
POST /api/memory/add
{
    "content": "Memory content",
    "agent_id": "DEVELOPER",
    "conversation_id": "conv_123",
    "metadata": {
        "category": "code_review",
        "importance": "high"
    },
    "tags": ["python", "optimization"]
}
```

#### Search Memories
```bash
POST /api/memory/search
{
    "query": "python best practices",
    "agent_id": "DEVELOPER",
    "limit": 10
}
```

#### Share Memory
```bash
POST /api/memory/share
{
    "content": "Shared knowledge",
    "source_agent": "DEVELOPER",
    "target_agents": ["PRODUCT", "BUG"],
    "metadata": {
        "importance": "high"
    }
}
```

#### Agent Profile
```bash
POST /api/memory/agent/{agent_id}/profile
{
    "capabilities": ["code_review", "optimization"],
    "preferences": {
        "language": "python",
        "style": "pep8"
    },
    "knowledge_areas": ["web_development", "api_design"]
}
```

### Configuration

Set the following environment variable:

```bash
SUPERMEMORY_API_KEY=your-supermemory-api-key
```

## Database Schema

### Email Tables

1. **email_drafts** - Stores email drafts pending review
2. **email_logs** - Tracks all sent emails and their status
3. **email_templates** - Reusable email templates

Run the migration script to create tables:

```bash
python migrations/create_email_tables.py
```

## Testing

Run the integration test script:

```bash
python tests/test_email_memory_integration.py
```

## Integration with Agents

Agents can now:

1. **Send Emails** - Use the email service to notify users
2. **Remember Context** - Store and retrieve relevant information
3. **Share Knowledge** - Pass important information to other agents
4. **Learn from History** - Access past conversations and decisions

## Security Considerations

- All endpoints require authentication via API key
- Email webhooks verify signatures
- Rate limiting applied to prevent abuse
- Sensitive data encrypted in transit

## Next Steps

1. Implement email template management UI
2. Add memory visualization dashboard
3. Create agent collaboration workflows
4. Set up automated memory consolidation