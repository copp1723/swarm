# Staging Deployment Guide for Email Agent

## Overview

This guide covers deploying the Email Agent system to a staging environment for testing before production release.

## Prerequisites

1. **Docker and Docker Compose installed**
2. **Redis and PostgreSQL** (or use Docker containers)
3. **Valid Mailgun account** with webhook signing key
4. **Convoy webhook gateway** (optional but recommended)
5. **Environment variables configured**

## Quick Start

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd mcp_new_project

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Required Environment Variables

```bash
# Core Configuration
FLASK_APP=app.py
FLASK_ENV=staging
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/email_agent
REDIS_URL=redis://localhost:6379/0

# Mailgun
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-domain.com
MAILGUN_WEBHOOK_SIGNING_KEY=your-webhook-signing-key

# Supermemory (if using)
SUPERMEMORY_API_KEY=your-supermemory-key
SUPERMEMORY_BASE_URL=https://api.supermemory.ai/v3

# Notifications (optional)
NOTIFICATION_SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK
NOTIFICATION_EMAIL_URL=mailto://username:password@smtp.gmail.com:587

# Email Agent Settings
EMAIL_AGENT_MAX_TIMESTAMP_AGE=300
EMAIL_AGENT_AUTO_DISPATCH=true
```

## Deployment Options

### Option 1: Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f email-agent
```

The Docker Compose setup includes:
- Email Agent Flask app
- Celery worker for background tasks
- Redis for task queue
- PostgreSQL for data storage
- Nginx reverse proxy
- Convoy webhook gateway (optional)

### Option 2: Manual Deployment

#### Step 1: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

#### Step 2: Start Services

Start each service in a separate terminal or use a process manager like systemd or supervisor.

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: PostgreSQL (if not using existing)
postgres -D /usr/local/var/postgres

# Terminal 3: Celery Worker
celery -A app.celery worker --loglevel=info --concurrency=4

# Terminal 4: Celery Beat (for scheduled tasks)
celery -A app.celery beat --loglevel=info

# Terminal 5: Flask App
gunicorn -w 4 -b 0.0.0.0:5006 app:app
```

### Option 3: Kubernetes (Advanced)

See `k8s/` directory for Kubernetes manifests (if available).

## Configuration Management

### 1. Update Configuration Files

```bash
# Edit agent configuration
nano config/agents.json

# Edit email agent settings
nano config/email_agent_config.yaml
```

### 2. Test Configuration

```bash
# Run configuration test
python -c "from config.config_loader import get_config_loader; c = get_config_loader(); print('Config loaded successfully')"
```

## Setting Up Webhooks

### 1. Mailgun Webhook

Configure Mailgun to send webhooks to your staging URL:

```bash
# Using Mailgun API
curl -s --user 'api:YOUR_API_KEY' \
  https://api.mailgun.net/v3/domains/YOUR_DOMAIN/webhooks \
  -F id='email_stored' \
  -F url='https://staging.yourdomain.com/api/email-agent/webhooks/mailgun'
```

### 2. Convoy Setup (Optional)

If using Convoy for reliable webhook delivery:

```bash
# Start Convoy
docker-compose up -d convoy

# Create webhook source
./scripts/setup_convoy_routes.sh
```

## Testing the Deployment

### 1. Health Check

```bash
# Check service health
curl https://staging.yourdomain.com/api/email-agent/health

# Expected response:
# {"status": "healthy", "celery": "connected", "redis": "connected"}
```

### 2. Run Integration Tests

```bash
# Set test URL
export TEST_BASE_URL=https://staging.yourdomain.com

# Run end-to-end tests
python test_e2e_email_flow.py

# Run edge case tests
python test_edge_cases.py
```

### 3. Send Test Email

Send a test email to your Mailgun configured address and verify:

1. Webhook is received (check logs)
2. Task is created in the system
3. Celery processes the task
4. Notifications are sent (if configured)

### 4. Monitor Logs

```bash
# Flask logs
tail -f logs/app.log

# Celery logs
tail -f logs/celery.log

# Combined Docker logs
docker-compose logs -f
```

## Performance Tuning

### 1. Celery Workers

Adjust worker concurrency based on load:

```bash
# For high load
celery -A app.celery worker --concurrency=8 --max-tasks-per-child=100

# For low memory systems
celery -A app.celery worker --concurrency=2 --max-memory-per-child=200000
```

### 2. Gunicorn Settings

```bash
# Production settings
gunicorn -w 4 \
  --worker-class gevent \
  --worker-connections 1000 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --timeout 30 \
  -b 0.0.0.0:5006 \
  app:app
```

### 3. Redis Configuration

Edit `redis.conf`:

```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## Monitoring

### 1. Application Metrics

- Use `/metrics` endpoint for Prometheus (if implemented)
- Check Celery queue lengths
- Monitor Redis memory usage

### 2. Log Aggregation

Configure log shipping to your preferred service:

```bash
# Example: Ship to ELK stack
filebeat -e -c filebeat.yml
```

### 3. Alerts

Set up alerts for:
- High error rates
- Queue backlogs
- Memory/CPU usage
- Failed webhook deliveries

## Security Checklist

- [ ] HTTPS enabled with valid certificate
- [ ] Webhook signature verification enabled
- [ ] Database connections use SSL
- [ ] Secrets stored in environment variables
- [ ] Rate limiting configured
- [ ] Access logs enabled
- [ ] Security headers configured in Nginx

## Troubleshooting

### Common Issues

1. **Webhook not received**
   - Check Mailgun webhook configuration
   - Verify firewall rules allow incoming webhooks
   - Check webhook signing key matches

2. **Tasks not processing**
   - Ensure Celery workers are running
   - Check Redis connectivity
   - Review Celery logs for errors

3. **High memory usage**
   - Adjust Celery worker concurrency
   - Enable task result expiration
   - Monitor for memory leaks

### Debug Mode

Enable debug logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Or via environment
export LOG_LEVEL=DEBUG
```

## Rollback Procedure

If issues arise:

1. **Docker Compose**:
   ```bash
   docker-compose down
   git checkout previous-version
   docker-compose up -d
   ```

2. **Manual Deployment**:
   ```bash
   # Stop services
   pkill -f celery
   pkill -f gunicorn
   
   # Restore previous version
   git checkout previous-version
   pip install -r requirements.txt
   
   # Restart services
   ```

## Next Steps

1. **Load Testing**: Use tools like locust or ab to test performance
2. **Security Audit**: Run security scanning tools
3. **Backup Strategy**: Set up database backups
4. **Monitoring**: Configure comprehensive monitoring
5. **Documentation**: Update runbooks with staging-specific procedures

## Support

For issues or questions:
1. Check application logs first
2. Review this guide and configuration documentation
3. Check GitHub issues for known problems
4. Contact the development team

Remember to never use production credentials in staging!