# Retry & Notification Stack

## Overview

The MCP Multi-Agent Platform implements a comprehensive retry and notification system using Tenacity for resilient external calls and Apprise for multi-channel notifications.

## Tenacity Retry Configuration

### Pre-configured Retry Strategies

#### 1. API Call Retry
```python
from utils.tenacity_retry import retry_api_call

@retry_api_call(max_attempts=5)
async def call_external_api():
    # Your API call here
    pass
```
- **Max Attempts**: 5
- **Backoff**: Exponential with jitter
- **Max Delay**: 30 seconds between retries
- **Notifications**: Sends alert on final failure

#### 2. Database Operation Retry
```python
from utils.tenacity_retry import retry_database_operation

@retry_database_operation(max_attempts=3)
async def database_query():
    # Your database operation
    pass
```
- **Max Attempts**: 3
- **Backoff**: Quick retries (0.5s base, 5s max)
- **Notifications**: Disabled by default

#### 3. Webhook Delivery Retry
```python
from utils.tenacity_retry import retry_webhook_delivery

@retry_webhook_delivery(max_attempts=5)
async def deliver_webhook(url, payload):
    # Webhook delivery logic
    pass
```
- **Max Attempts**: 5
- **Max Total Delay**: 10 minutes
- **Backoff**: Random exponential (1-120s)
- **Notifications**: Custom webhook failure alerts

#### 4. Memory Operation Retry
```python
from utils.tenacity_retry import retry_memory_operation

@retry_memory_operation(max_attempts=3)
async def sync_memory():
    # Memory operation
    pass
```
- **Max Attempts**: 3
- **Backoff**: Standard exponential
- **Notifications**: Enabled with context

### Custom Retry Configuration

```python
from utils.tenacity_retry import create_retry_decorator

# Create custom retry decorator
custom_retry = create_retry_decorator(
    max_attempts=10,
    max_delay=600,  # 10 minutes total
    exponential_base=3,
    exponential_max=120,
    exceptions=(ConnectionError, TimeoutError),
    on_failure_notify=True,
    notification_context={'service': 'custom_service'}
)

@custom_retry
async def custom_operation():
    # Your operation
    pass
```

### Manual Retry Management

```python
from utils.tenacity_retry import RetryManager

retry_manager = RetryManager(
    max_attempts=3,
    base_delay=2.0,
    exponential_base=2.0
)

while True:
    try:
        result = await operation()
        break
    except Exception as e:
        if retry_manager.should_retry(e):
            delay = retry_manager.get_delay()
            await asyncio.sleep(delay)
        else:
            await retry_manager.notify_failure({
                'operation': 'custom_op',
                'error': str(e)
            })
            raise
```

## Apprise Notification Service

### Configuration

Set notification channels via environment variables:

```bash
# Email
NOTIFICATION_EMAIL_URL=mailto://username:password@gmail.com

# Slack
NOTIFICATION_SLACK_WEBHOOK=hooks.slack.com/services/YOUR/WEBHOOK

# Discord
NOTIFICATION_DISCORD_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK

# Telegram
NOTIFICATION_TELEGRAM_TOKEN=your-bot-token
NOTIFICATION_TELEGRAM_CHAT_ID=your-chat-id

# PagerDuty (for critical alerts)
NOTIFICATION_PAGERDUTY_KEY=your-integration-key

# Custom webhook
NOTIFICATION_WEBHOOK_URL=https://your-webhook.com/notify
```

### Notification Types

#### 1. Critical Alerts
```python
from utils.notification_service import send_critical_alert

await send_critical_alert(
    title="Database Connection Failed",
    message="Unable to connect to primary database",
    details={
        'host': 'db.example.com',
        'port': 5432,
        'attempts': 5
    }
)
```

#### 2. Task Failure Alerts
```python
await notification_service.send_task_failure_alert(
    task_name='process_user_data',
    task_id='task-123',
    error='Connection timeout',
    context={'user_id': 456}
)
```

#### 3. Webhook Failure Alerts
```python
await notification_service.send_webhook_failure_alert(
    webhook_url='https://api.example.com/webhook',
    attempts=5,
    error='503 Service Unavailable'
)
```

#### 4. Security Alerts
```python
await notification_service.send_security_alert(
    alert_type='Replay Attack Detected',
    message='Multiple token replay attempts',
    source_ip='192.168.1.100',
    user='user@example.com',
    details={'attempts': 10}
)
```

#### 5. Performance Alerts
```python
await notification_service.send_performance_alert(
    metric='Response Time',
    current_value=5.2,
    threshold=2.0,
    unit='seconds',
    details={'endpoint': '/api/process'}
)
```

#### 6. Success Notifications
```python
await notification_service.send_success_notification(
    operation='Data Migration',
    message='Successfully migrated 10,000 records',
    stats={
        'records': 10000,
        'duration': '2h 15m',
        'errors': 0
    }
)
```

### Channel Tagging

Target specific notification channels using tags:

```python
# Send only to critical channels
await send_notification(
    title="System Alert",
    body="Critical system event",
    notify_type=NotifyType.WARNING,
    tags=['critical', 'ops']
)
```

### Dynamic Channel Management

```python
# Add channel at runtime
notification_service.add_channel(
    'discord://webhook_id/webhook_token',
    tag='development'
)

# Remove channel
notification_service.remove_channel('discord://webhook_id/webhook_token')

# List all channels
channels = notification_service.get_channels()
```

## Integration with HTTP Client

### Resilient HTTP Client

```python
from services.resilient_http_client import ResilientHTTPClient

async with ResilientHTTPClient(max_retries=5) as client:
    # Automatic retry with notifications on failure
    response = await client.get('https://api.example.com/data')
    data = response.json()
```

### Webhook Delivery

```python
from services.resilient_http_client import deliver_webhook_resilient

success = await deliver_webhook_resilient(
    url='https://api.example.com/webhook',
    payload={'event': 'user.created', 'id': 123},
    signature='hmac_signature',
    max_retries=5
)
```

## Celery Task Integration

All Celery tasks automatically integrate with the retry/notification stack:

```python
@celery_app.task(bind=True)
@retry_on_failure(max_retries=3)
async def process_data(self, data):
    try:
        # Process data
        result = await external_api_call(data)
        return result
    except Exception as e:
        # Automatic retry and notification on final failure
        raise
```

## Best Practices

### 1. Choose Appropriate Retry Strategy
- API calls: Use exponential backoff with jitter
- Database: Quick retries with short delays
- Webhooks: Longer delays, more attempts

### 2. Set Reasonable Limits
- Max attempts: 3-5 for most operations
- Total delay: Consider user experience
- Timeout: Set appropriate request timeouts

### 3. Notification Guidelines
- Critical alerts: System failures, security issues
- Warnings: Degraded performance, retry exhaustion
- Info: Successful operations, statistics

### 4. Error Context
Always include relevant context in notifications:
```python
details={
    'operation': 'user_sync',
    'user_id': 123,
    'timestamp': datetime.utcnow().isoformat(),
    'environment': 'production'
}
```

### 5. Idempotency
Ensure operations are idempotent for safe retries:
```python
# Use unique request IDs
request_id = str(uuid.uuid4())
await process_with_id(request_id, data)
```

## Monitoring & Debugging

### Retry Metrics
- Track retry attempts per operation
- Monitor retry success rates
- Alert on high retry rates

### Notification Health
- Verify channel connectivity
- Test notifications regularly
- Monitor delivery success

### Logging
All retries and notifications are logged:
```
INFO: Retrying operation after 2.5s (attempt 2/5)
WARNING: Operation failed after 5 attempts, sending notification
INFO: Critical alert sent to 3 channels
```

## Testing

### Test Retry Logic
```python
@pytest.mark.asyncio
async def test_retry_on_failure():
    call_count = 0
    
    @retry_api_call(max_attempts=3)
    async def flaky_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"
    
    result = await flaky_operation()
    assert result == "success"
    assert call_count == 3
```

### Test Notifications
```python
async def test_notification_delivery():
    service = NotificationService()
    
    # Add test channel
    service.add_channel('discord://test/webhook', tag='test')
    
    # Send test notification
    success = await service.send_notification(
        title="Test Alert",
        body="This is a test",
        tags=['test']
    )
    
    assert success
```