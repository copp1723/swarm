# Mailgun Email Receiving Setup Guide

## Overview

The Swarm MCP system is designed to receive emails and automatically convert them into agent tasks. This guide will help you set up Mailgun to receive emails and forward them to your application.

## Step 1: Create an Email Address for Your Agent

In Mailgun dashboard:

1. Go to **Receiving** → **Routes**
2. Click **Create Route**
3. Configure the route:
   - **Expression Type**: Match Recipient
   - **Recipient**: `agent@yourdomain.com` (or any email you want)
   - **Actions**: 
     - Store (to save the email)
     - Forward to: `https://yourdomain.com/api/email-agent/webhooks/mailgun`
   - **Priority**: 0
   - **Description**: "Swarm Agent Email Handler"

## Step 2: Configure Webhook Settings

### Required Environment Variables

Add these to your `.env` file:

```bash
# Mailgun Configuration
MAILGUN_API_KEY=your-sending-api-key
MAILGUN_DOMAIN=mg.yourdomain.com
MAILGUN_SIGNING_KEY=your-webhook-signing-key  # CRITICAL for security!
DEFAULT_FROM_EMAIL=agent@yourdomain.com

# Optional but recommended
MAILGUN_WEBHOOK_URL=https://yourdomain.com/api/email-agent/webhooks/mailgun
```

### Get Your Webhook Signing Key

1. In Mailgun dashboard, go to **Settings** → **Webhooks**
2. Find "HTTP webhook signing key"
3. Copy this key - it's used to verify webhook authenticity

## Step 3: Set Up Webhooks (Two Options)

### Option A: Via Mailgun Dashboard (Easier)

1. Go to **Webhooks** in Mailgun
2. Add webhook URL: `https://yourdomain.com/api/email-agent/webhooks/mailgun`
3. Select events to track:
   - ✅ delivered
   - ✅ opened
   - ✅ clicked
   - ✅ complained
   - ✅ unsubscribed
   - ✅ failed

### Option B: Via API (Programmatic)

```bash
curl -s --user 'api:YOUR_API_KEY' \
  https://api.mailgun.net/v3/domains/YOUR_DOMAIN/webhooks \
  -F id='delivered' \
  -F url='https://yourdomain.com/api/email-agent/webhooks/mailgun'
```

## Step 4: Test Email Receiving

### Local Testing with ngrok

For local development:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start your app
cd /Users/copp1723/Desktop/swarm/mcp_new_project
./deploy-production.sh

# In another terminal, expose your local app
ngrok http 8000

# Update Mailgun route with ngrok URL
# e.g., https://abc123.ngrok.io/api/email-agent/webhooks/mailgun
```

### Production Testing

Once deployed:

1. Send a test email to `agent@yourdomain.com`
2. Check logs:
   ```bash
   docker-compose logs -f app | grep email
   ```
3. Verify in database:
   ```bash
   docker-compose exec app python -c "
   from services.email_service import EmailService
   service = EmailService()
   emails = service.get_recent_emails(limit=5)
   print(emails)
   "
   ```

## Step 5: Email Processing Features

### What Happens When an Email is Received

1. **Mailgun receives** the email at `agent@yourdomain.com`
2. **Webhook sent** to your application with email data
3. **Security check** - HMAC signature verification
4. **Email parsed** into structured task:
   ```json
   {
     "type": "bug_report",
     "priority": "high",
     "title": "Critical bug in login system",
     "requirements": ["Fix login", "Test on production"],
     "deadline": "2024-01-20",
     "assigned_agent": "debugging_agent"
   }
   ```
5. **Task queued** for background processing
6. **Agent processes** the task and can send response

### Supported Email Formats

The parser understands various email formats:

```
Subject: BUG: Login system broken
Priority: Urgent

The login system is throwing 500 errors...
Deadline: Tomorrow
Tags: #critical #auth
```

Or more structured:

```
Task Type: Feature Request
Priority: Medium
Title: Add dark mode
Requirements:
- Toggle in settings
- Save preference
- Apply to all pages
Due: End of month
```

## Step 6: Advanced Configuration

### Using Convoy for Reliability

The system supports Convoy webhook gateway for:
- Automatic retries
- Dead letter queues
- Webhook analytics

To enable:
```bash
ENABLE_CONVOY=true
CONVOY_API_URL=http://convoy:5005
CONVOY_API_KEY=your-convoy-key
```

### Email Templates for Responses

Configure auto-responses in `config/email_agent_config.yaml`:

```yaml
templates:
  acknowledgment:
    subject: "Task Received: {task_title}"
    body: |
      Hi {sender_name},
      
      I've received your {task_type} and assigned it to {assigned_agent}.
      Expected completion: {deadline}
      
      Task ID: {task_id}
```

## Troubleshooting

### Webhook Not Receiving

1. **Check URL accessibility**:
   ```bash
   curl -X POST https://yourdomain.com/api/email-agent/webhooks/mailgun
   # Should return 400 (missing signature) not 404
   ```

2. **Verify signing key**:
   ```python
   # In your app logs, look for:
   "Webhook signature verification failed"
   # This means wrong signing key
   ```

3. **Check Mailgun logs**:
   - Go to Mailgun → Logs
   - Look for webhook delivery attempts

### Email Not Processing

1. **Check Celery workers**:
   ```bash
   docker-compose logs celery
   ```

2. **Verify task queue**:
   ```bash
   docker-compose exec redis redis-cli
   > LLEN celery
   ```

3. **Check email parser**:
   ```bash
   docker-compose exec app python -c "
   from services.email_parser import EmailParser
   parser = EmailParser()
   test = parser.parse('Test email')
   print(test)
   "
   ```

## Security Best Practices

1. **Always verify webhook signatures** - Never disable this!
2. **Use HTTPS** for webhook endpoints
3. **Rotate signing keys** periodically
4. **Implement rate limiting** (already configured)
5. **Monitor failed webhooks** in Mailgun dashboard

## Example Use Cases

1. **Bug Reports**: Email to `bugs@yourdomain.com` → Auto-assigned to debugging agent
2. **Feature Requests**: Email to `features@yourdomain.com` → Routed to planning agent
3. **Support Tickets**: Email to `support@yourdomain.com` → Creates support task
4. **Code Reviews**: Email with attachment → Triggers code review workflow

## Next Steps

1. Set up monitoring for email processing
2. Configure auto-response templates
3. Create email aliases for different task types
4. Set up email analytics dashboard
5. Implement custom email parsing rules