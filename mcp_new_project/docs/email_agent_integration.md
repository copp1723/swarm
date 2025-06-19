# Email Agent Integration Guide

## Overview
The Email Agent has been integrated into the MCP Executive Platform with full Mailgun webhook support, HMAC-SHA256 signature verification, and replay attack protection.

## Endpoints

### 1. Health Check
- **URL**: `GET /api/email-agent/health`
- **Purpose**: Check if the Email Agent service is running
- **Response**: 
  ```json
  {
    "service": "email_agent",
    "status": "healthy",
    "version": "1.0.0",
    "timestamp": "2025-06-18T..."
  }
  ```

### 2. Mailgun Webhook
- **URL**: `POST /api/email-agent/webhooks/mailgun`
- **Purpose**: Receive and process Mailgun webhook events
- **Security**: 
  - HMAC-SHA256 signature verification
  - Timestamp validation (120-second window)
- **Expected Payload**:
  ```json
  {
    "signature": {
      "token": "...",
      "timestamp": "...",
      "signature": "..."
    },
    "event-data": {
      "event": "delivered",
      "message": {
        "headers": {
          "from": "sender@example.com",
          "subject": "Test Email"
        },
        "recipients": ["recipient@example.com"],
        "body-plain": "Email content..."
      }
    }
  }
  ```

### 3. Task Handler
- **URL**: `POST /api/email-agent/tasks`
- **Purpose**: Handle email-related tasks from the orchestrator
- **Supported Actions**: 
  - `compose_draft`
  - `search_emails`
  - `analyze_email`
  - `ingest_email`

## Configuration

### Environment Variables
```bash
# Required
MAILGUN_SIGNING_KEY=your-mailgun-signing-key-here

# Optional
EMAIL_AGENT_LOG_LEVEL=INFO
EMAIL_AGENT_MAX_TIMESTAMP_AGE=120
```

### Mailgun Webhook Configuration
1. Log into your Mailgun dashboard
2. Navigate to Webhooks settings
3. Add webhook URL: `https://your-domain.com/api/email-agent/webhooks/mailgun`
4. Select events to track (e.g., delivered, opened, clicked, etc.)

## Testing

### Test the Email Agent Health
```bash
curl http://localhost:5006/api/email-agent/health
```

### Test Webhook with Sample Data
```bash
python test_email_agent.py
```

This will:
- Test signature verification
- Test timestamp validation
- Generate sample webhook payloads
- Provide cURL commands for testing

### Manual Webhook Test
```bash
# Get sample payload from test script
python test_email_agent.py

# Use the generated cURL command to test the webhook
curl -X POST http://localhost:5006/api/email-agent/webhooks/mailgun \
  -H "Content-Type: application/json" \
  -d '{...payload...}'
```

## Integration with Agents

The Email Agent is now available in the agent profiles and can be:
1. Selected from the UI as "Email Agent"
2. Tagged in collaborative tasks using `@email`
3. Used in workflows for email-based automation

### Example Usage
```javascript
// Collaborative task with Email Agent
const task = {
  task_description: "Process incoming support emails and create tickets",
  tagged_agents: ["email_01", "product_01"],
  working_directory: "./support"
};
```

## Security Considerations

1. **Signature Verification**: All webhooks are verified using HMAC-SHA256
2. **Replay Protection**: Timestamps older than 120 seconds are rejected
3. **Content Validation**: All webhook data is validated before processing
4. **Error Handling**: Failed verifications return 403 Forbidden

## Future Enhancements

1. **Supermemory Integration**: Store emails in long-term memory
2. **Approval Workflows**: Email-based approval chains
3. **Email Composition**: AI-powered email drafting
4. **Analytics**: Email pattern analysis and insights
5. **Convoy Integration**: Webhook gateway for reliability

## Troubleshooting

### Common Issues

1. **Signature Verification Fails**
   - Check MAILGUN_SIGNING_KEY environment variable
   - Ensure you're using the correct signing key from Mailgun

2. **Timestamp Errors**
   - Verify server time is synchronized
   - Check MAX_TIMESTAMP_AGE_SECONDS setting

3. **Webhook Not Received**
   - Check Mailgun webhook configuration
   - Verify firewall/network settings
   - Check application logs for errors

### Debug Mode
Enable debug logging:
```python
EMAIL_AGENT_LOG_LEVEL=DEBUG
```

## Related Files
- `/services/email_agent.py` - Main Email Agent implementation
- `/test_email_agent.py` - Test suite
- `/register_email_agent.py` - Integration guide
- `/config/agents.json` - Agent profile configuration