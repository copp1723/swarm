# Celery Background Task Processing

## Overview

The MCP Multi-Agent Platform now includes comprehensive background task processing using Celery. This enables asynchronous processing of emails, webhooks, memory operations, and maintenance tasks.

## Architecture

### Task Queues

1. **email_queue** - Processes email events (delivery, opens, bounces, etc.)
2. **webhook_queue** - Handles webhook processing from various sources
3. **memory_queue** - Manages agent memory synchronization
4. **default** - General purpose tasks

### Workers

- **Email Worker**: 2 concurrent processes
- **Webhook Worker**: 3 concurrent processes  
- **Memory Worker**: 1 process (to avoid conflicts)
- **Default Worker**: 2 processes

### Scheduled Tasks

Celery Beat runs periodic tasks:
- **Token Cleanup**: Every hour
- **Memory Sync**: Every 5 minutes
- **Cache Health Check**: Every 30 minutes

## Starting Workers

```bash
# Start all workers and beat scheduler
./scripts/start_celery_worker.sh

# Monitor workers in real-time
./scripts/monitor_celery.py

# Stop all workers
./scripts/stop_celery_workers.sh
```

## Task Examples

### Email Processing

```python
from tasks.email_tasks import process_email_event

# Queue email event for processing
result = process_email_event.delay({
    'event': 'delivered',
    'message-id': '<123@example.com>',
    'recipient': 'user@example.com'
})

# Check task status
print(result.status)
print(result.result)
```

### Webhook Processing

```python
from tasks.webhook_tasks import process_webhook

# Process webhook with replay protection
result = process_webhook.delay(
    webhook_data={'id': '123', 'data': '...'},
    webhook_type='mailgun',
    source_ip='192.168.1.1'
)
```

### Memory Operations

```python
from tasks.memory_tasks import consolidate_agent_memories

# Consolidate memories for an agent
result = consolidate_agent_memories.delay(
    agent_id='web_researcher',
    topic='API documentation',
    time_range_days=7
)
```

## Monitoring

### Command Line Monitoring

```bash
# Real-time monitoring with colored output
./scripts/monitor_celery.py

# View task history
./scripts/monitor_celery.py --mode history

# Adjust refresh interval
./scripts/monitor_celery.py --interval 5
```

### Celery Flower (Web UI)

```bash
# Install Flower
pip install flower

# Start Flower web interface
celery -A config.celery_config:celery_app flower

# Access at http://localhost:5555
```

### Celery Events

```bash
# Real-time event monitoring
celery -A config.celery_config:celery_app events

# With curses display
celery -A config.celery_config:celery_app events --curses
```

## Configuration

### Environment Variables

```bash
# Redis connection (required)
REDIS_URL=redis://localhost:6379/0

# Optional: Celery specific settings
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Task Routing

Tasks are automatically routed to appropriate queues:

```python
# config/celery_config.py
task_routes = {
    'tasks.email_tasks.*': {'queue': 'email_queue'},
    'tasks.webhook_tasks.*': {'queue': 'webhook_queue'},
    'tasks.memory_tasks.*': {'queue': 'memory_queue'},
}
```

## Error Handling

### Retry Logic

Tasks use automatic retry with exponential backoff:

```python
@retry_on_failure(max_retries=3)
async def process_task(self, data):
    # Task will retry up to 3 times
    # with delays of 60s, 120s, 180s
```

### Dead Letter Queue

Failed tasks after all retries are logged and can be:
- Manually requeued
- Analyzed for patterns
- Sent to monitoring systems

## Security

### Replay Protection

All tasks include replay attack prevention:
- Email events use message-id tokens
- Webhooks use event-id or payload hash
- Tokens are cached with TTL

### Signature Validation

Webhook tasks validate signatures:
- Mailgun HMAC validation
- GitHub webhook secrets
- Slack request verification

## Performance Tuning

### Worker Concurrency

Adjust based on workload:

```bash
# High throughput email processing
celery worker -Q email_queue --concurrency=8

# CPU-intensive tasks
celery worker -Q compute_queue --concurrency=2
```

### Prefetch Multiplier

Control task prefetching:

```python
# Reduce prefetch for long tasks
celery_app.conf.worker_prefetch_multiplier = 1
```

## Troubleshooting

### Workers Not Starting

1. Check Redis is running: `redis-cli ping`
2. Verify virtual environment is activated
3. Check for port conflicts

### Tasks Not Processing

1. Verify workers are listening to correct queues
2. Check task routing configuration
3. Monitor with `celery inspect active`

### Memory Issues

1. Limit worker concurrency
2. Set max tasks per child: `--max-tasks-per-child=100`
3. Monitor with `./scripts/monitor_celery.py`

## Best Practices

1. **Use Appropriate Queues**: Route tasks to specialized queues
2. **Set Task Time Limits**: Prevent hanging tasks
3. **Monitor Queue Sizes**: Watch for backlog buildup
4. **Log Task Results**: Track success/failure patterns
5. **Implement Idempotency**: Tasks should be safe to retry

## Integration with Agents

Agents can leverage background tasks:

```python
# In agent code
from tasks.email_tasks import send_email_async

# Queue email for async sending
result = send_email_async.delay(
    to='user@example.com',
    subject='Task Complete',
    body='Your requested task has been completed.'
)
```

This enables agents to offload time-consuming operations while remaining responsive.