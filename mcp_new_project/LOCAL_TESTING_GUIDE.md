# Local Testing Guide for Production Setup

This guide helps you test the production-ready features locally before deploying to a production server.

## Prerequisites

- Python 3.9+
- Redis (optional, will use mock if not available)
- PostgreSQL (optional, will use SQLite if not available)

## Quick Start

```bash
# Run all production tests
python scripts/run_production_tests.py
```

## Testing Components

### 1. Database Testing

Test PostgreSQL connection pooling and failover:

```bash
# Test with PostgreSQL
export DATABASE_URL="postgresql://user:password@localhost/test_db"
python -m pytest tests/test_production_setup.py::TestProductionDatabase -v

# Test with SQLite (default)
python -m pytest tests/test_production_setup.py::TestProductionDatabase -v
```

### 2. Redis Cache Testing

Test caching functionality:

```bash
# With Redis running
redis-server &
python -m pytest tests/test_production_setup.py::TestRedisCache -v

# Without Redis (uses mock)
export USE_MOCK_REDIS=true
python -m pytest tests/test_production_setup.py::TestRedisCache -v
```

### 3. Email Integration Testing

Test email processing pipeline:

```bash
# Run email integration tests
python -m pytest tests/test_production_setup.py::TestEmailIntegration -v

# Test with mock email service
export MOCK_EMAIL_SERVICE=true
python -m pytest tests/test_production_setup.py::TestEmailIntegration -v
```

### 4. Load Testing

Simulate production load scenarios:

```bash
# Run all load tests
python -m pytest tests/test_load_scenarios.py -v -s

# Run specific scenarios
python -m pytest tests/test_load_scenarios.py::TestLoadScenarios::test_email_burst_scenario -v -s
python -m pytest tests/test_load_scenarios.py::TestLoadScenarios::test_sustained_load_scenario -v -s
```

## Manual Testing

### Start Production Server Locally

```bash
# Set up environment
cp .env.example .env
# Edit .env with your test values

# Start server
python app_production.py
```

### Test Endpoints

```bash
# Health check
curl http://localhost:5006/health

# Metrics
curl http://localhost:5006/metrics

# Test email webhook
curl -X POST http://localhost:5006/api/email-agent/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{
    "from": "test@example.com",
    "subject": "Test Email",
    "body_plain": "This is a test email"
  }'
```

### Test with Celery

```bash
# Start Redis (if available)
redis-server &

# Start Celery worker
celery -A app_production.celery worker --loglevel=info &

# Start Celery beat (for scheduled tasks)
celery -A app_production.celery beat --loglevel=info &

# Monitor with Flower
celery -A app_production.celery flower
```

## Testing Email Integration with ngrok

To test Mailgun webhooks locally:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start your local server
python app_production.py

# In another terminal, expose your local server
ngrok http 5006

# Use the ngrok URL for Mailgun webhook
# Example: https://abc123.ngrok.io/api/email-agent/webhooks/mailgun
```

## Performance Testing

### Database Performance

```python
# Test connection pool
from config.production_database import get_production_db

db_manager = get_production_db()
for i in range(100):
    health = db_manager.health_check()
    print(f"Connection {i}: {health['healthy']}")
```

### Cache Performance

```python
from services.redis_cache_manager import get_cache_manager

cache = get_cache_manager()

# Write test
import time
start = time.time()
for i in range(1000):
    cache.set("test", f"key_{i}", f"value_{i}")
print(f"1000 writes: {time.time() - start:.2f}s")

# Read test
start = time.time()
for i in range(1000):
    cache.get("test", f"key_{i}")
print(f"1000 reads: {time.time() - start:.2f}s")
```

## Debugging Tips

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=1
python app_production.py
```

### Check Database Connections

```sql
-- PostgreSQL
SELECT count(*) FROM pg_stat_activity;
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- Check slow queries
SELECT query, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

### Monitor Redis

```bash
# Redis CLI
redis-cli
> INFO stats
> MONITOR  # Watch commands in real-time
```

### Test Celery Tasks

```python
from tasks.enhanced_email_tasks import process_email_task

# Test task directly
result = process_email_task.delay(
    task_id="test_123",
    email_data={"from": "test@example.com", "subject": "Test"},
    parsed_task={"description": "Test task"},
    agents=["agent1"]
)

print(f"Task ID: {result.id}")
print(f"Status: {result.status}")
print(f"Result: {result.get(timeout=30)}")
```

## Common Issues and Solutions

### Issue: Redis Connection Failed
```bash
# Solution 1: Start Redis
redis-server

# Solution 2: Use mock Redis
export USE_MOCK_REDIS=true
```

### Issue: Database Connection Pool Exhausted
```python
# Increase pool size in production_database.py
'pool_size': 30,
'max_overflow': 60
```

### Issue: Celery Tasks Not Processing
```bash
# Check worker status
celery -A app_production.celery inspect active

# Purge queue
celery -A app_production.celery purge
```

### Issue: Email Webhooks Not Working
```bash
# Test webhook endpoint directly
curl -X POST http://localhost:5006/api/email-agent/webhooks/test \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Check logs for signature validation errors
tail -f logs/app.log | grep webhook
```

## Test Checklist

Before deploying to production, ensure:

- [ ] All unit tests pass
- [ ] Load tests show acceptable performance
- [ ] Database migrations run successfully
- [ ] Health endpoint returns healthy status
- [ ] Email processing works end-to-end
- [ ] Celery tasks process correctly
- [ ] Cache hit ratio is > 70%
- [ ] No memory leaks under load
- [ ] Error handling works properly
- [ ] Logs are generated correctly

## Next Steps

Once all tests pass locally:

1. Review the `PRODUCTION_DEPLOYMENT_GUIDE.md`
2. Set up your production environment
3. Configure environment variables
4. Deploy using your preferred method (Docker, traditional, etc.)
5. Run smoke tests on production
6. Monitor system performance