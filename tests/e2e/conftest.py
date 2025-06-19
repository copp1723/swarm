"""
Pytest configuration and fixtures for end-to-end tests
"""

import pytest
import os
from unittest.mock import patch, MagicMock
import asyncio
import redis
from celery import Celery

from app import create_app
from services.service_container import ServiceContainer
from services.token_replay_cache import TokenReplayCache
from services.notification_service import NotificationService
from services.supermemory_service import SupermemoryService


@pytest.fixture(scope='session')
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope='function')
def app():
    """Create Flask app for testing"""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'MAILGUN_SIGNING_KEY': 'test-mailgun-key',
        'CONVOY_ENDPOINT_SECRET': 'test-convoy-secret',
        'REDIS_URL': 'redis://localhost:6379/15',  # Use test DB
        'CELERY_BROKER_URL': 'redis://localhost:6379/15',
        'CELERY_RESULT_BACKEND': 'redis://localhost:6379/15'
    })
    
    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def client(app):
    """Create Flask test client"""
    return app.test_client()


@pytest.fixture(scope='function')
def service_container(app):
    """Create service container with mocked services"""
    container = ServiceContainer()
    
    # Mock services for testing
    container.register('notification_service', MagicMock(spec=NotificationService))
    container.register('supermemory_service', MagicMock(spec=SupermemoryService))
    container.register('replay_cache', TokenReplayCache(use_redis=False))
    
    return container


@pytest.fixture(scope='function')
def mock_redis():
    """Mock Redis client"""
    with patch('redis.Redis') as mock:
        client = MagicMock()
        mock.from_url.return_value = client
        yield client


@pytest.fixture(scope='function')
def mock_celery(app):
    """Mock Celery for testing"""
    celery = Celery('test')
    celery.conf.update(
        broker_url='memory://',
        result_backend='cache+memory://',
        task_always_eager=True,  # Execute tasks synchronously
        task_eager_propagates=True
    )
    
    with patch('tasks.email_tasks.celery', celery):
        with patch('tasks.webhook_tasks.celery', celery):
            yield celery


@pytest.fixture(scope='function')
def mock_mailgun_api():
    """Mock Mailgun API responses"""
    with patch('requests.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'id': '<20240115100000.1234567@myapp.com>',
            'message': 'Queued. Thank you.'
        }
        yield mock_post


@pytest.fixture(scope='function')
def mock_supermemory_api():
    """Mock Supermemory API responses"""
    with patch('httpx.AsyncClient') as mock_client:
        client_instance = MagicMock()
        mock_client.return_value.__aenter__.return_value = client_instance
        
        # Mock successful memory storage
        client_instance.post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'id': 'mem_test123',
                'success': True
            }
        )
        
        # Mock successful memory search
        client_instance.get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'results': [
                    {
                        'id': 'mem_1',
                        'content': 'Test memory',
                        'metadata': {'type': 'email'}
                    }
                ]
            }
        )
        
        yield client_instance


@pytest.fixture(scope='function')
def sample_email_data():
    """Sample email data for testing"""
    return {
        "from": "sender@example.com",
        "to": ["recipient@myapp.com"],
        "subject": "Test Email Subject",
        "body_plain": "This is a test email body.",
        "body_html": "<p>This is a test email body.</p>",
        "message_id": "<test123@example.com>",
        "timestamp": 1705318800.0,
        "headers": {
            "From": "Sender Name <sender@example.com>",
            "To": "recipient@myapp.com",
            "Subject": "Test Email Subject",
            "Message-Id": "<test123@example.com>"
        }
    }


@pytest.fixture(scope='function')
def sample_agent_task():
    """Sample agent task for testing"""
    from models.agent_task import AgentTask, TaskType, TaskPriority
    
    return AgentTask(
        title="Test Task",
        description="This is a test task description",
        task_type=TaskType.GENERAL,
        priority=TaskPriority.MEDIUM,
        metadata={
            "source": "test",
            "created_by": "pytest"
        }
    )


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables"""
    test_env = {
        'MAILGUN_SIGNING_KEY': 'test-mailgun-key',
        'MAILGUN_API_KEY': 'test-api-key',
        'MAILGUN_DOMAIN': 'test.myapp.com',
        'CONVOY_API_KEY': 'test-convoy-key',
        'SUPERMEMORY_API_KEY': 'test-supermemory-key',
        'REDIS_URL': 'redis://localhost:6379/15',
        'OPENAI_API_KEY': 'test-openai-key'
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_redis(mock_redis):
    """Clean up Redis after each test"""
    yield
    if mock_redis:
        mock_redis.flushdb()


# Test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_redis: mark test as requiring Redis"
    )
    config.addinivalue_line(
        "markers", "requires_celery: mark test as requiring Celery"
    )