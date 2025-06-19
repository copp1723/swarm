# Production Deployment Guide for Swarm MCP with Email Integration

## Overview
This guide covers deploying the Swarm MCP platform with production PostgreSQL, Redis, and email-to-agent integration.

## Prerequisites

- PostgreSQL 13+ database
- Redis 6+ server
- Domain with Mailgun configured
- SSL certificate (Let's Encrypt recommended)
- Python 3.9+
- Docker (optional but recommended)

## Environment Configuration

### 1. Create Production Environment File

```bash
cp .env.production .env
```

Edit `.env` with your production values:

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@host:5432/swarm_db
POSTGRES_POOL_SIZE=20
POSTGRES_MAX_OVERFLOW=40

# Redis Configuration
REDIS_URL=redis://:password@host:6379/0
REDIS_MAX_CONNECTIONS=100

# Celery Configuration
CELERY_BROKER_URL=redis://:password@host:6379/1
CELERY_RESULT_BACKEND=redis://:password@host:6379/2

# Email Configuration
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=mail.yourdomain.com
MAILGUN_SIGNING_KEY=your-webhook-signing-key
DEFAULT_FROM_EMAIL=agent@yourdomain.com

# API Keys
OPENROUTER_API_KEY=your-openrouter-key
SECRET_KEY=your-secret-key-generate-with-secrets.token_hex(32)
JWT_SECRET_KEY=your-jwt-secret

# Application Settings
FLASK_ENV=production
SERVER_NAME=yourdomain.com
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Features
ENABLE_WEBSOCKETS=true
ENABLE_CELERY=true
ENABLE_CONVOY=true

# Monitoring
SENTRY_DSN=your-sentry-dsn
```

## Database Setup

### 1. PostgreSQL Setup

```sql
-- Create database and user
CREATE DATABASE swarm_db;
CREATE USER swarm_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE swarm_db TO swarm_user;

-- Enable extensions
\c swarm_db
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### 2. Run Migrations

```bash
cd /path/to/swarm/mcp_new_project
python migrations/run_migrations.py
```

### 3. Redis Setup

```bash
# Redis configuration (redis.conf)
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
requirepass your-redis-password
```

## Application Deployment

### Option 1: Docker Deployment (Recommended)

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.yml up -d

# Scale workers
docker-compose scale celery_worker=4
```

### Option 2: Traditional Deployment

#### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install production dependencies
pip install -r config/requirements/requirements.txt
pip install -r config/requirements/requirements_email_agent.txt
pip install gunicorn gevent psycopg2-binary redis
```

#### 2. Start Services

```bash
# Start Gunicorn (main app)
gunicorn -w 4 \
  --worker-class gevent \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  app_production:app

# Start Celery workers
celery -A app_production.celery worker \
  --loglevel=info \
  --concurrency=4 \
  --max-tasks-per-child=100

# Start Celery beat (for scheduled tasks)
celery -A app_production.celery beat \
  --loglevel=info

# Start Flower (Celery monitoring)
celery -A app_production.celery flower \
  --port=5555
```

#### 3. Nginx Configuration

```nginx
upstream swarm_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Timeouts
    client_max_body_size 50M;
    client_body_timeout 60;
    send_timeout 300;
    
    # WebSocket support
    location /socket.io {
        proxy_pass http://swarm_app/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Main application
    location / {
        proxy_pass http://swarm_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
    
    # Static files
    location /static {
        alias /path/to/swarm/mcp_new_project/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Email Integration Setup

### 1. Configure Mailgun Route

1. Log into Mailgun Dashboard
2. Go to **Receiving** → **Routes**
3. Create new route:
   - Expression: `match_recipient("agent@yourdomain.com")`
   - Action: Forward to `https://yourdomain.com/api/email-agent/webhooks/mailgun`
   - Priority: 0

### 2. Test Email Processing

```bash
# Send test email
curl -X POST https://yourdomain.com/api/email-agent/test \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@example.com",
    "subject": "Test Task",
    "body": "Please help me with this bug..."
  }'
```

## Production Monitoring

### 1. Health Checks

```bash
# Application health
curl https://yourdomain.com/health

# Detailed metrics
curl https://yourdomain.com/metrics
```

### 2. Log Aggregation

```bash
# Configure rsyslog or similar
*.* @@log-server.yourdomain.com:514
```

### 3. Database Monitoring

```sql
-- Monitor connections
SELECT count(*) FROM pg_stat_activity;

-- Monitor slow queries
SELECT query, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

### 4. Redis Monitoring

```bash
# Redis CLI monitoring
redis-cli -h your-redis-host
> INFO
> MONITOR  # Real-time command monitoring
```

## Performance Tuning

### 1. PostgreSQL Optimization

```sql
-- Adjust shared_buffers (25% of RAM)
ALTER SYSTEM SET shared_buffers = '4GB';

-- Increase work_mem for complex queries
ALTER SYSTEM SET work_mem = '256MB';

-- Enable query parallelization
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
```

### 2. Redis Optimization

```bash
# Enable persistence with AOF
appendonly yes
appendfsync everysec

# Optimize for LRU eviction
maxmemory-policy allkeys-lru
```

### 3. Application Optimization

```python
# In production settings
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 40
SQLALCHEMY_POOL_RECYCLE = 3600

# Celery optimization
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_TASK_ACKS_LATE = True
```

## Backup Strategy

### 1. PostgreSQL Backups

```bash
#!/bin/bash
# backup-postgres.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"

# Full backup
pg_dump -h localhost -U swarm_user -d swarm_db -F custom -f "$BACKUP_DIR/swarm_db_$DATE.dump"

# Keep only last 7 days
find $BACKUP_DIR -name "*.dump" -mtime +7 -delete
```

### 2. Redis Backups

```bash
#!/bin/bash
# backup-redis.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/redis"

# Save snapshot
redis-cli -a your-password BGSAVE
sleep 10
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/dump_$DATE.rdb"
```

### 3. Automated Backups

```cron
# Crontab entries
0 2 * * * /path/to/backup-postgres.sh
0 3 * * * /path/to/backup-redis.sh
```

## Scaling Considerations

### 1. Horizontal Scaling

- **Web Servers**: Add more Gunicorn instances behind load balancer
- **Workers**: Scale Celery workers based on queue depth
- **Database**: Consider read replicas for heavy read loads

### 2. Vertical Scaling

- **PostgreSQL**: Increase shared_buffers, work_mem
- **Redis**: Increase maxmemory based on cache hit ratio
- **Application**: Increase worker processes and threads

### 3. Caching Strategy

```python
# Use Redis cache for frequently accessed data
from services.redis_cache_manager import cache_result

@cache_result(namespace="agents", ttl=3600)
def get_agent_profile(agent_id):
    # Expensive database query
    return Agent.query.get(agent_id)
```

## Troubleshooting

### Common Issues

1. **Database Connection Pool Exhausted**
   ```python
   # Increase pool size in production_database.py
   'pool_size': 30,
   'max_overflow': 60
   ```

2. **Celery Tasks Not Processing**
   ```bash
   # Check worker status
   celery -A app_production.celery inspect active
   
   # Purge stuck tasks
   celery -A app_production.celery purge
   ```

3. **Email Webhooks Failing**
   ```bash
   # Check webhook signature
   curl -X POST https://yourdomain.com/api/email-agent/webhooks/test
   
   # Verify Mailgun logs
   # Check application logs for signature mismatches
   ```

## Security Checklist

- [ ] SSL/TLS configured with strong ciphers
- [ ] Database connections use SSL
- [ ] Redis password protected
- [ ] API keys rotated regularly
- [ ] Webhook signatures verified
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection protection (via SQLAlchemy)
- [ ] XSS protection headers configured
- [ ] CORS properly configured

## Maintenance Tasks

### Daily
- Monitor error rates in logs
- Check queue depths
- Verify backup completion

### Weekly
- Review slow query logs
- Check disk usage
- Update security patches

### Monthly
- Rotate API keys
- Review and optimize indexes
- Clean up old task data

## Support Resources

- **Logs**: `/var/log/swarm/`
- **Metrics**: `https://yourdomain.com/metrics`
- **Health**: `https://yourdomain.com/health`
- **Celery Flower**: `http://yourdomain.com:5555`

---

This production setup provides:
- ✅ High availability with PostgreSQL and Redis
- ✅ Scalable task processing with Celery
- ✅ Email-to-agent workflow automation
- ✅ Comprehensive monitoring and backups
- ✅ Security best practices