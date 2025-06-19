# Convoy Webhook Gateway Deployment Guide

## Overview
This guide covers deploying the MCP Executive Platform with Convoy as a webhook gateway for scalable email webhook processing.

## Architecture

```
Internet → Convoy Gateway → Email Agent → Processing
              ↓
         PostgreSQL (Events)
              ↓
          Redis (Queue)
```

## Components

### 1. Convoy Gateway
- **Purpose**: Webhook ingestion, verification, retry handling, and routing
- **Port**: 8080 (API & Dashboard)
- **Features**:
  - Automatic retries with exponential backoff
  - Event persistence in PostgreSQL
  - Fan-out routing to multiple destinations
  - Rate limiting and security features

### 2. Email Agent (MCP Executive)
- **Purpose**: Process verified webhooks from Convoy
- **Port**: 5006
- **Integration**: Receives forwarded webhooks from Convoy

### 3. PostgreSQL Databases
- **convoy-db**: Stores Convoy events and metadata
- **app-db**: Application database for MCP Executive

### 4. Redis Instances
- **convoy-redis**: Convoy's queue and cache
- **app-redis**: Application cache and Celery broker

## Quick Start

### 1. Environment Setup

Create a `.env` file with required variables:
```bash
# Copy example and fill in values
cp .env.example .env

# Required variables:
MAILGUN_SIGNING_KEY=your-mailgun-signing-key
OPENROUTER_API_KEY=your-openrouter-api-key
CONVOY_ADMIN_PASSWORD=secure-admin-password
CONVOY_JWT_SECRET=secure-jwt-secret
CONVOY_API_KEY=secure-api-key
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f convoy
docker-compose logs -f mcp-executive
```

### 3. Configure Convoy Routes

Wait for services to be healthy, then run:
```bash
# Configure webhook routes
./scripts/convoy-routes.sh

# Or manually configure a route:
curl -X POST http://localhost:8080/api/v1/routes \
  -u admin:${CONVOY_ADMIN_PASSWORD} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mailgun-webhook",
    "match": {
      "type": "http_path",
      "value": "/webhooks/mailgun"
    },
    "destinations": [{
      "url": "http://mcp-executive:5006/api/email-agent/webhooks/mailgun",
      "method": "POST"
    }],
    "retries": {
      "count": 5,
      "backoff": {
        "type": "exponential",
        "initial": "1s",
        "max": "30s"
      }
    }
  }'
```

### 4. Configure Mailgun

In your Mailgun dashboard:
1. Navigate to Webhooks settings
2. Add webhook URL: `https://your-domain.com/webhooks/mailgun`
3. Select events to track (delivered, opened, clicked, etc.)

## Testing

### 1. Health Checks

```bash
# Check Convoy health
curl http://localhost:8080/health

# Check Email Agent health
curl http://localhost:5006/api/email-agent/health

# Check via Convoy route
curl http://localhost:8080/webhooks/email-agent/health
```

### 2. Test Webhook

```bash
# Generate test payload
python test_email_agent.py

# Send test webhook through Convoy
curl -X POST http://localhost:8080/webhooks/mailgun \
  -H "Content-Type: application/json" \
  -d '{
    "signature": {
      "token": "test-token",
      "timestamp": "1234567890",
      "signature": "test-signature"
    },
    "event-data": {
      "event": "delivered",
      "message": {
        "headers": {
          "from": "test@example.com",
          "subject": "Test Email"
        }
      }
    }
  }'
```

## Production Deployment

### 1. Security Hardening

```yaml
# Update docker-compose.yml for production:
environment:
  - FLASK_ENV=production
  - CONVOY_ADMIN_PASSWORD=${STRONG_PASSWORD}
  - CONVOY_JWT_SECRET=${RANDOM_SECRET}
  - CONVOY_API_KEY=${SECURE_API_KEY}
```

### 2. SSL/TLS with Nginx

The included nginx service can handle SSL termination:
```bash
# Place SSL certificates in nginx/ssl/
cp your-cert.crt nginx/ssl/
cp your-cert.key nginx/ssl/

# Update nginx/sites-enabled/default with SSL config
```

### 3. Scaling

```bash
# Scale Email Agent instances
docker-compose up -d --scale mcp-executive=3

# Convoy will load balance across instances
```

### 4. Monitoring

Access Convoy dashboard:
- URL: http://localhost:8080
- Username: admin
- Password: ${CONVOY_ADMIN_PASSWORD}

Features:
- View webhook events
- Monitor delivery status
- Retry failed webhooks
- View metrics and analytics

## Advanced Configuration

### 1. Fan-Out Routes

Route webhooks to multiple destinations:
```bash
curl -X POST http://localhost:8080/api/v1/routes \
  -u admin:${CONVOY_ADMIN_PASSWORD} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mailgun-fanout",
    "match": {"type": "http_path", "value": "/webhooks/mailgun-multi"},
    "destinations": [
      {
        "url": "http://mcp-executive:5006/api/email-agent/webhooks/mailgun",
        "method": "POST"
      },
      {
        "url": "http://audit-service:4000/events",
        "method": "POST"
      }
    ]
  }'
```

### 2. Rate Limiting

Configure per-route rate limits:
```json
{
  "rate_limit": {
    "requests_per_second": 100,
    "burst": 200
  }
}
```

### 3. Custom Headers

Add headers to forwarded requests:
```json
{
  "destinations": [{
    "url": "http://mcp-executive:5006/webhooks",
    "headers": {
      "X-Convoy-Source": "mailgun",
      "X-Environment": "production"
    }
  }]
}
```

## Troubleshooting

### Common Issues

1. **Convoy not starting**
   - Check PostgreSQL is running: `docker-compose logs convoy-db`
   - Verify credentials in docker-compose.yml

2. **Webhooks not reaching Email Agent**
   - Check Convoy routes: `curl http://localhost:8080/api/v1/routes -u admin:password`
   - Verify network connectivity: `docker exec convoy ping mcp-executive`

3. **Signature verification failures**
   - Ensure MAILGUN_SIGNING_KEY is set correctly
   - Check if webhook is coming through Convoy (look for X-Convoy headers)

### Debug Mode

Enable detailed logging:
```yaml
environment:
  - EMAIL_AGENT_LOG_LEVEL=DEBUG
  - CONVOY_LOG_LEVEL=debug
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f convoy
docker-compose logs -f mcp-executive

# Last 100 lines
docker-compose logs --tail=100 convoy
```

## Backup and Recovery

### Database Backups

```bash
# Backup Convoy database
docker exec convoy-postgres pg_dump -U convoy_user convoy_db > convoy_backup.sql

# Backup application database
docker exec mcp-postgres pg_dump -U mcp_user mcp_db > mcp_backup.sql

# Restore
docker exec -i convoy-postgres psql -U convoy_user convoy_db < convoy_backup.sql
```

### Volume Backups

```bash
# List volumes
docker volume ls

# Backup volume
docker run --rm -v convoy_pgdata:/data -v $(pwd):/backup alpine tar czf /backup/convoy_pgdata.tar.gz -C /data .
```

## Maintenance

### Update Services

```bash
# Pull latest images
docker-compose pull

# Recreate services
docker-compose up -d --force-recreate
```

### Clean Up

```bash
# Remove stopped containers
docker-compose down

# Remove all (including volumes)
docker-compose down -v

# Prune unused resources
docker system prune -a
```

## Resources

- [Convoy Documentation](https://getconvoy.io/docs)
- [Docker Compose Best Practices](https://docs.docker.com/compose/production/)
- [Mailgun Webhooks Guide](https://documentation.mailgun.com/en/latest/user_manual.html#webhooks)
- [MCP Executive Platform Docs](./email_agent_integration.md)