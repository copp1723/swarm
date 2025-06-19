# Complete Mailgun Webhook Setup for mailagent@onerylie.com

## ✅ Prerequisites Confirmed
- Domain: `mail.onerylie.com` (MX, SPF, DKIM, CNAME verified)
- Mailgun Pro Plan (supports inbound routing)
- Swarm MCP application ready

## 🚀 Step 1: Get Your Webhook Signing Key

1. Log into Mailgun Dashboard
2. Navigate to **Settings** → **Webhooks** 
3. Find **"HTTP webhook signing key"**
4. Copy this key - you'll need it for the `.env` file

## 🔧 Step 2: Configure Environment Variables

Add these to your `.env` file:

```bash
# Mailgun Configuration
MAILGUN_API_KEY=your-api-key-here
MAILGUN_DOMAIN=mail.onerylie.com
MAILGUN_SIGNING_KEY=your-webhook-signing-key-here  # CRITICAL!
DEFAULT_FROM_EMAIL=mailagent@onerylie.com

# Optional - for tracking
MAILGUN_WEBHOOK_URL=https://your-domain.com/api/email-agent/webhooks/mailgun
```

## 🌐 Step 3: Set Up Public Webhook Access

### Option A: Local Development with ngrok

```bash
# Start your application
cd /Users/copp1723/Desktop/swarm/mcp_new_project
./deploy-production.sh

# In another terminal, expose port 8000
ngrok http 8000

# You'll see something like:
# Forwarding https://abc123.ngrok.io -> http://localhost:8000
```

Your webhook URL will be:
```
https://abc123.ngrok.io/api/email-agent/webhooks/mailgun
```

### Option B: Production Deployment

Your webhook URL will be:
```
https://mail.onerylie.com/api/email-agent/webhooks/mailgun
```

## 📮 Step 4: Configure Mailgun Route

1. Go to Mailgun Dashboard → **Receiving** → **Routes**
2. Click **"Create Route"**
3. Configure:
   - **Expression Type**: `Match Recipient`
   - **Recipient**: `mailagent@onerylie.com`
   - **Actions**: 
     - ✅ Store (optional - keeps copy in Mailgun)
     - ✅ Forward (toggle ON)
   - **Forward URL**: 
     ```
     https://your-ngrok-or-production-url/api/email-agent/webhooks/mailgun
     ```
   - **Stop**: ✅ ON (prevents other routes from processing)
   - **Priority**: `0`
   - **Description**: `Mail Agent Task Parser`

## 🧪 Step 5: Test the Webhook Handler

### Quick Test Script

```bash
# Test if webhook endpoint is accessible
curl -X POST https://your-webhook-url/api/email-agent/webhooks/mailgun \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "timestamp=1234567890&token=test&signature=test"

# Should return: {"status":"error","message":"Invalid signature"}
# This confirms the endpoint is reachable and validating signatures
```

### Verify Handler is Working

```python
# Check logs while sending test email
docker-compose logs -f app | grep -E "(email|webhook|mailgun)"
```

## 📧 Step 6: Test Email Processing

### Send Test Email with Calendar Invite

1. Create a test `.ics` file or calendar invite
2. Send email to `mailagent@onerylie.com` with:
   ```
   Subject: Meeting: Project Review
   Body: Please add this meeting to my calendar
   Attachment: meeting.ics
   ```

### What Happens Next:

1. Mailgun receives the email
2. Webhook is triggered with email data
3. Your app validates the webhook signature
4. Email is parsed into a task:
   ```json
   {
     "type": "calendar_event",
     "title": "Meeting: Project Review",
     "priority": "medium",
     "attachments": ["meeting.ics"],
     "assigned_agent": "calendar_agent"
   }
   ```
5. Task is queued for processing
6. Response sent back (if configured)

## 🔍 Step 7: Monitor & Debug

### Check Mailgun Logs
1. Go to Mailgun → **Logs**
2. Filter by your domain
3. Look for:
   - Accepted emails to `mailagent@onerylie.com`
   - Webhook delivery attempts
   - Any errors or retries

### Check Application Logs
```bash
# All email-related logs
docker-compose logs app | grep -i email

# Webhook specific
docker-compose logs app | grep -i webhook

# Check Celery worker for task processing
docker-compose logs celery | grep -i task
```

### Common Issues & Solutions

**Webhook returns 400 "Invalid signature"**
- Wrong or missing `MAILGUN_SIGNING_KEY` in `.env`
- Signature key mismatch between Mailgun and your app

**Webhook returns 404**
- Wrong webhook URL in Mailgun route
- Application not running or route not registered

**Email received but no task created**
- Check email parser configuration
- Verify Celery workers are running
- Check database for stored emails

## 📊 Step 8: Verify End-to-End

### Database Check
```bash
# Check if emails are being stored
docker-compose exec app python -c "
from models.email_models import EmailLog
from models.core import db
emails = EmailLog.query.order_by(EmailLog.created_at.desc()).limit(5).all()
for email in emails:
    print(f'{email.created_at}: {email.sender} -> {email.subject}')
"
```

### Task Creation Check
```bash
# Check if tasks are being created from emails
docker-compose exec app python -c "
from models.tasks import AgentTask
from models.core import db
tasks = AgentTask.query.filter_by(source='email').order_by(AgentTask.created_at.desc()).limit(5).all()
for task in tasks:
    print(f'{task.created_at}: {task.type} - {task.title}')
"
```

## 🎯 Quick Checklist

- [ ] Webhook signing key added to `.env`
- [ ] Application running (locally or production)
- [ ] Webhook URL publicly accessible (ngrok or HTTPS)
- [ ] Mailgun route created with correct forward URL
- [ ] Test email sent to `mailagent@onerylie.com`
- [ ] Webhook logs show successful delivery
- [ ] Task created from email in database

## 🚨 Important Security Notes

1. **Never disable signature validation** - it's your defense against fake webhooks
2. **Use HTTPS in production** - HTTP webhooks can be intercepted
3. **Rotate signing keys periodically** - update both in Mailgun and `.env`
4. **Monitor failed webhooks** - could indicate attacks or misconfigurations

## 📝 Sample Task Formats for Testing

### Bug Report Email
```
To: mailagent@onerylie.com
Subject: BUG: Login page shows 500 error
Body:
Priority: High
When users try to login with special characters, the page crashes.
Steps to reproduce:
1. Go to login page
2. Enter email with emoji
3. Submit form
Expected: Error message
Actual: 500 error page
```

### Feature Request Email
```
To: mailagent@onerylie.com
Subject: Feature Request: Dark mode toggle
Body:
Priority: Medium
Please add a dark mode toggle to the settings page.
Requirements:
- Toggle switch in user settings
- Persist preference
- Apply to all pages
Deadline: End of month
```

### Calendar Event Email
```
To: mailagent@onerylie.com
Subject: Meeting: Team Standup
Body:
Add this recurring meeting to the calendar
Attachment: team-standup.ics
```

Ready to test? Start with ngrok locally, then move to production once confirmed working!