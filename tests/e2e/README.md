# End-to-End Tests

This directory contains comprehensive end-to-end tests for the webhook flow through Convoy gateway into EmailAgent tasks.

## Test Structure

### 1. `test_webhook_flow.py`
Tests the complete webhook processing pipeline:
- Mailgun signature verification
- Webhook endpoint validation
- Convoy header processing
- Replay attack protection
- Email task processing
- Integration with Supermemory
- Error handling and recovery

### 2. `test_routing_behaviors.py`
Tests agent routing and task assignment:
- Email-to-agent routing based on content
- Multi-agent task execution
- Agent capability matching
- Priority-based routing
- Context-aware routing
- Task dispatch behaviors
- Validation behaviors

### 3. `test_convoy_integration.py`
Tests Convoy webhook gateway integration:
- Convoy-specific headers
- Retry mechanisms with exponential backoff
- Idempotency handling
- Delivery guarantees
- Circuit breaker pattern
- Rate limiting
- Monitoring and metrics

### 4. `conftest.py`
Shared pytest fixtures and configuration:
- Flask app and client setup
- Service container mocking
- API mocking (Mailgun, Supermemory)
- Sample data fixtures
- Environment setup

## Running Tests

### Run all E2E tests:
```bash
pytest tests/e2e -v
```

### Run specific test file:
```bash
pytest tests/e2e/test_webhook_flow.py -v
```

### Run with coverage:
```bash
pytest tests/e2e --cov=services --cov=tasks --cov-report=html
```

### Run integration tests only:
```bash
pytest tests/e2e -m integration
```

### Run tests requiring Redis:
```bash
pytest tests/e2e -m requires_redis
```

## Test Scenarios Covered

### Security
- ✅ Mailgun signature verification
- ✅ Timestamp validation (replay protection)
- ✅ Token replay cache functionality
- ✅ Invalid payload rejection

### Routing
- ✅ Email content analysis for agent selection
- ✅ Priority detection from keywords
- ✅ Multi-agent collaboration
- ✅ Capability-based agent matching

### Resilience
- ✅ Retry on failures (Tenacity integration)
- ✅ Circuit breaker simulation
- ✅ Dead letter queue handling
- ✅ Notification on fatal failures

### Validation
- ✅ Webhook payload validation (Marshmallow)
- ✅ Task creation validation
- ✅ Agent request validation
- ✅ Email field validation

### Integration
- ✅ Supermemory storage
- ✅ Celery task queuing
- ✅ Convoy gateway headers
- ✅ Complete email-to-task flow

## Mocking Strategy

The tests use extensive mocking to isolate components:
- External APIs (Mailgun, Supermemory, Convoy)
- Redis connections
- Celery tasks (run synchronously in tests)
- HTTP clients

## Adding New Tests

When adding new E2E tests:
1. Use appropriate fixtures from `conftest.py`
2. Mock external dependencies
3. Test both success and failure paths
4. Add integration markers where appropriate
5. Document complex test scenarios

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:
```yaml
# Example GitHub Actions
test-e2e:
  runs-on: ubuntu-latest
  services:
    redis:
      image: redis:7-alpine
      ports:
        - 6379:6379
  steps:
    - uses: actions/checkout@v2
    - name: Run E2E Tests
      run: |
        pip install -r requirements.txt
        pytest tests/e2e -v --tb=short
```