# Agent Email Setup Guide for Mailgun

## Overview
This guide will help you set up individual email addresses for each agent in your MCP system, allowing them to receive and respond to emails directly.

## Prerequisites
✅ Domain configured with Mailgun
✅ MX records set up in DNS
✅ Mailgun API key obtained

## Step-by-Step Setup

### 1. Update Your Environment Configuration

1. **Copy the environment template:**
   ```bash
   cp config/.env.example config/.env
   ```

2. **Update your `.env` file with Mailgun settings:**
   ```bash
   # Mailgun Configuration
   MAILGUN_API_KEY=your_actual_mailgun_api_key_here
   MAILGUN_DOMAIN=yourdomain.com
   MAILGUN_SIGNING_KEY=your_webhook_signing_key_here
   SWARM_BASE_URL=https://yourdomain.com

   # Default email settings
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com
   ```

### 2. Agent Email Addresses

Your agents are now configured with these email addresses:
- **Product Agent**: `product@yourdomain.com`
- **Coding Agent**: `coding@yourdomain.com`
- **Bug Agent**: `bug@yourdomain.com`
- **General Assistant**: `general@yourdomain.com`

### 3. Automatic Mailgun Route Setup

Use the provided script to automatically create Mailgun routes:

```bash
# Set up all agent email routes
python scripts/setup_mailgun_routes.py setup

# List existing routes
python scripts/setup_mailgun_routes.py list

# Delete all agent routes (if needed)
python scripts/setup_mailgun_routes.py delete
```

### 4. Manual Mailgun Route Setup (Alternative)

If you prefer to set up routes manually in the Mailgun dashboard:

1. **Log into Mailgun Dashboard**
   - Go to https://app.mailgun.com/
   - Navigate to **Sending** → **Domain Settings** → **Routes**

2. **Create Routes for Each Agent:**

   **Product Agent Route:**
   - Expression: `match_recipient("product@yourdomain.com")`
   - Action: `forward("https://yourdomain.com/api/email-agent/webhooks/mailgun")`
   - Priority: `10`
   - Description: `Product Agent Email Route`

   **Coding Agent Route:**
   - Expression: `match_recipient("coding@yourdomain.com")`
   - Action: `forward("https://yourdomain.com/api/email-agent/webhooks/mailgun")`
   - Priority: `10`
   - Description: `Coding Agent Email Route`

   **Bug Agent Route:**
   - Expression: `match_recipient("bug@yourdomain.com")`
   - Action: `forward("https://yourdomain.com/api/email-agent/webhooks/mailgun")`
   - Priority: `10`
   - Description: `Bug Agent Email Route`

   **General Agent Route:**
   - Expression: `match_recipient("general@yourdomain.com")`
   - Action: `forward("https://yourdomain.com/api/email-agent/webhooks/mailgun")`
   - Priority: `10`
   - Description: `General Agent Email Route`

### 5. Webhook Configuration

1. **In Mailgun Dashboard:**
   - Go to **Settings** → **Webhooks**
   - Set webhook URL: `https://yourdomain.com/api/email-agent/webhooks/mailgun`
   - Generate and save the webhook signing key

2. **Update your `.env` file:**
   ```bash
   MAILGUN_SIGNING_KEY=your_webhook_signing_key_here
   ```

### 6. Deploy Your Application

1. **Start the production server:**
   ```bash
   # Using the production app
   python app_production.py

   # Or with Gunicorn (recommended)
   gunicorn -k gevent -w 4 app_production:app
   ```

2. **Ensure your webhook URL is accessible:**
   - Test: `curl https://yourdomain.com/api/email-agent/webhooks/mailgun`
   - Should return a method not allowed error (normal for GET request)

### 7. Test Your Setup

1. **Send test emails to your agents:**
   ```bash
   # Test product agent
   echo "Please help me plan a new feature for user authentication" | mail -s "New Feature Request" product@yourdomain.com

   # Test coding agent  
   echo "I need help debugging a Python script" | mail -s "Debug Request" coding@yourdomain.com

   # Test bug agent
   echo "Found a bug in the login system" | mail -s "Bug Report" bug@yourdomain.com

   # Test general agent
   echo "Can you help me understand how to use this system?" | mail -s "General Question" general@yourdomain.com
   ```

2. **Monitor the logs:**
   ```bash
   # Check application logs
   tail -f logs/mcp_executive.log

   # Check Mailgun logs in dashboard
   ```

### 8. Email Flow Process

When someone sends an email to an agent:

1. **Email Received** → Mailgun receives the email
2. **Route Matched** → Mailgun matches the recipient to a route
3. **Webhook Triggered** → Mailgun forwards to your webhook URL
4. **Agent Processing** → Your system identifies the target agent
5. **AI Response** → Agent processes the email and generates response
6. **Email Sent** → Response is sent back via Mailgun

### 9. Monitoring and Troubleshooting

#### Check Route Status
```bash
python scripts/setup_mailgun_routes.py list
```

#### Check Email Processing
```bash
# View recent email logs
grep "email-agent" logs/mcp_executive.log | tail -20

# Check webhook deliveries in Mailgun dashboard
```

#### Common Issues

**Issue: Webhook not receiving emails**
- Verify webhook URL is accessible from internet
- Check Mailgun route configuration
- Verify webhook signing key matches

**Issue: Agent not responding**
- Check agent configuration in `config/agents.json`
- Verify OpenRouter API key is set
- Check application logs for errors

**Issue: Email sending fails**
- Verify Mailgun API key has sending permissions
- Check domain verification status
- Ensure SPF/DKIM records are configured

### 10. Advanced Configuration

#### Custom Agent Email Addresses
To add custom email addresses for agents:

1. **Update `config/agents.json`:**
   ```json
   {
     "custom_agent": {
       "name": "Custom Agent",
       "email": "custom@yourdomain.com",
       "role": "specialist",
       "system_prompt": "You are a custom specialist agent."
     }
   }
   ```

2. **Create the Mailgun route:**
   ```bash
   python scripts/setup_mailgun_routes.py setup
   ```

#### Email Templates
Customize email responses by modifying templates in:
- `services/email_agent_integration.py`
- Agent system prompts in `config/agents.json`

#### Rate Limiting
Configure email rate limits in your `.env`:
```bash
RATE_LIMIT_WEBHOOKS_PER_MINUTE=100
WEBHOOK_PROCESSING_TIMEOUT=30
```

## Security Considerations

1. **Webhook Validation**: Always verify webhook signatures
2. **Rate Limiting**: Implement rate limits to prevent abuse
3. **Input Sanitization**: Sanitize email content before processing
4. **Access Control**: Limit who can email your agents
5. **Logging**: Log all email interactions for audit purposes

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review application logs
3. Verify Mailgun configuration
4. Test webhook connectivity

## Summary

After completing this setup:
- ✅ Each agent has a dedicated email address
- ✅ Emails are automatically routed to the correct agent
- ✅ Agents respond with AI-generated content
- ✅ All interactions are logged and auditable
- ✅ System is production-ready and scalable

Your multi-agent system can now handle email communications seamlessly!

