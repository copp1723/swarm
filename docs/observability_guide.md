# Observability Guide

## Overview

The Email Agent system includes comprehensive observability features using Loguru for structured logging, Sentry for error tracking, and custom performance monitoring.

## Components

### 1. Structured Logging with Loguru

Loguru provides:
- Automatic log rotation and compression
- Structured logging with context
- Color-coded console output
- JSON logging for production
- Performance tracking decorators

#### Configuration

Set these environment variables:

```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=logs
LOG_FILE_ROTATION=100 MB
LOG_FILE_RETENTION=30 days
LOG_FILE_COMPRESSION=zip
ENABLE_FILE_LOGGING=true
ENABLE_JSON_LOGS=false  # Set to true for production
```

#### Usage Examples

```python
from utils.logging_config import get_logger, LogContext, log_email_task

logger = get_logger(__name__)

# Basic logging
logger.info("Processing email", email_id="123")

# Context logging
with LogContext(user_id="456", request_id="abc"):
    logger.info("Processing user request")
    # All logs within this context will include user_id and request_id

# Specialized logging
log_email_task("task_123", "created", title="Fix bug", priority="high")
```

### 2. Error Tracking with Sentry

Sentry provides:
- Automatic error capture
- Performance monitoring
- Release tracking
- User context
- Integration with Flask and Celery

#### Configuration

```bash
SENTRY_DSN=https://your-key@sentry.io/your-project-id
SENTRY_ENVIRONMENT=development  # or staging, production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
ENABLE_SENTRY=true
```

#### Features

- Automatic error capture with stack traces
- Breadcrumbs for debugging context
- Performance monitoring for slow endpoints
- Filtered sensitive data (passwords, API keys)

### 3. Performance Monitoring

Custom performance monitoring tracks:
- Operation durations
- System resource usage
- Request counts and error rates
- Email processing metrics

#### Usage Examples

```python
from utils.performance_monitor import (
    timed_operation, track_operation, 
    track_email_processing, record_metric
)

# Decorator for timing functions
@timed_operation("email.parse")
def parse_email(data):
    # Function is automatically timed
    pass

# Context manager for operations
with track_operation("webhook.process", email_id="123"):
    # Operation is tracked with context
    process_webhook()

# Track specific metrics
track_email_processing("email_123", "parsed", duration=0.5)
record_metric("queue.length", 42)
```

## Monitoring Endpoints

### Health Check
```bash
GET /api/monitoring/health

# Response:
{
  "status": "healthy",
  "checks": {
    "database": true,
    "redis": true,
    "celery": true
  },
  "system": {
    "cpu_percent": 23.5,
    "memory_percent": 45.2,
    "disk_percent": 67.8
  }
}
```

### Metrics
```bash
GET /api/monitoring/metrics

# Response:
{
  "metrics": {
    "uptime_seconds": 3600,
    "counters": {
      "email.parsed.success": 150,
      "email.parsed.failure": 3,
      "webhook.mailgun.status_200": 147,
      "webhook.mailgun.status_403": 6
    },
    "active_operations": 2
  }
}
```

### Readiness Probe
```bash
GET /api/monitoring/ready

# Returns 200 if ready, 503 if not
```

### Liveness Probe
```bash
GET /api/monitoring/live

# Always returns 200 if service is running
```

## Log Files

Logs are stored in the `logs/` directory:

- `mcp_executive.log` - Main application log
- `mcp_executive.error.log` - Errors only
- `mcp_executive.debug.log` - Debug logs (development only)

Each log file:
- Rotates at 100MB (configurable)
- Keeps 30 days of history
- Compresses old files to save space

## Debugging Tips

### 1. Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python app.py
```

### 2. View Structured Logs

```bash
# Pretty print JSON logs
tail -f logs/mcp_executive.log | jq '.'

# Filter by level
grep '"level": "ERROR"' logs/mcp_executive.log | jq '.'

# Search by context
grep '"task_id": "task_123"' logs/mcp_executive.log
```

### 3. Performance Analysis

```python
# Get performance summary
from utils.performance_monitor import get_performance_summary
summary = get_performance_summary()
print(json.dumps(summary, indent=2))
```

### 4. Sentry Debugging

- Use breadcrumbs to track user actions
- Check Sentry dashboard for error patterns
- Use Sentry's performance monitoring for slow queries

## Best Practices

### 1. Use Structured Logging

```python
# Good - structured with context
logger.info("Email processed", 
    email_id=email_id,
    duration=duration,
    status="success"
)

# Bad - unstructured string
logger.info(f"Processed email {email_id} in {duration}s")
```

### 2. Track Important Operations

```python
with track_operation("critical.operation", user_id=user_id):
    # Critical operation code
    result = perform_operation()
    if not result:
        logger.error("Operation failed", reason=result.error)
```

### 3. Use Appropriate Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General informational messages
- **WARNING**: Something unexpected but handled
- **ERROR**: Error occurred but system continues
- **CRITICAL**: Serious error, system may not continue

### 4. Monitor Key Metrics

Track these metrics for email processing:
- Webhook processing time
- Email parsing success rate
- Task dispatch latency
- Queue lengths
- Memory usage trends

## Alerting

Configure alerts for:

1. **High Error Rate**: More than 5% errors in 5 minutes
2. **Slow Response**: Average response time > 1 second
3. **Queue Backup**: More than 100 tasks queued
4. **Resource Usage**: CPU > 80% or Memory > 85%
5. **Service Down**: Health check failing

## Production Checklist

- [ ] Set `ENABLE_JSON_LOGS=true` for structured logs
- [ ] Configure Sentry DSN for error tracking
- [ ] Set appropriate log retention (30-90 days)
- [ ] Enable log compression to save space
- [ ] Set up log aggregation (ELK, Splunk, etc.)
- [ ] Configure alerting thresholds
- [ ] Test monitoring endpoints
- [ ] Document runbooks for common issues
- [ ] Set up dashboards for key metrics
- [ ] Configure PagerDuty for critical alerts

## Troubleshooting

### High Memory Usage

1. Check for memory leaks in logs:
```bash
grep "memory_percent" logs/mcp_executive.log | tail -20
```

2. Review active operations:
```bash
curl http://localhost:5006/api/monitoring/metrics | jq '.metrics.active_operations'
```

### Slow Performance

1. Check operation durations:
```bash
grep "duration_seconds" logs/mcp_executive.log | jq '. | select(.duration_seconds > 1)'
```

2. Review Sentry performance data

### Missing Logs

1. Verify logging is enabled:
```bash
echo $ENABLE_FILE_LOGGING  # Should be "true"
```

2. Check disk space:
```bash
df -h logs/
```

3. Verify permissions:
```bash
ls -la logs/
```