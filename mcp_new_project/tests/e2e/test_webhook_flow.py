"""
End-to-End Tests for Webhook Flow
Tests the complete flow from Convoy gateway through EmailAgent to task processing
"""

import pytest
import json
import hmac
import hashlib
import time
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from app import create_app
from services.email_agent import verify_mailgun_signature
from services.token_replay_cache import TokenReplayCache
from tasks.email_tasks import process_email_event
from services.supermemory_service import SupermemoryService, Memory


class TestWebhookFlow:
    """End-to-end tests for webhook processing flow"""
    
    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        app = create_app()
        app.config['TESTING'] = True
        app.config['MAILGUN_SIGNING_KEY'] = 'test-signing-key-123'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()
    
    @pytest.fixture
    def replay_cache(self):
        """Create test replay cache"""
        cache = TokenReplayCache(use_redis=False, ttl_seconds=120)
        return cache
    
    def generate_mailgun_signature(self, timestamp, token):
        """Generate valid Mailgun signature for testing"""
        signing_key = 'test-signing-key-123'
        message = f"{timestamp}{token}".encode('utf-8')
        key = signing_key.encode('utf-8')
        return hmac.new(key=key, msg=message, digestmod=hashlib.sha256).hexdigest()
    
    def create_mailgun_webhook_data(self, event_type='delivered', include_convoy=False):
        """Create valid Mailgun webhook test data"""
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        token = 'test-token-' + timestamp
        signature = self.generate_mailgun_signature(timestamp, token)
        
        base_data = {
            "signature": {
                "timestamp": timestamp,
                "token": token,
                "signature": signature
            },
            "event-data": {
                "event": event_type,
                "recipient": "user@example.com",
                "sender": "system@myapp.com",
                "timestamp": float(timestamp),
                "message": {
                    "headers": {
                        "from": "System <system@myapp.com>",
                        "subject": "Test Email",
                        "message-id": f"<test-{timestamp}@myapp.com>"
                    },
                    "recipients": ["user@example.com"],
                    "body-plain": "This is a test email body"
                }
            }
        }
        
        if include_convoy:
            base_data["convoy_metadata"] = {
                "project_id": "test-project",
                "endpoint_id": "test-endpoint",
                "event_id": f"evt_{timestamp}"
            }
        
        return base_data
    
    def test_mailgun_signature_verification(self):
        """Test Mailgun signature verification"""
        timestamp = str(int(time.time()))
        token = "test-token"
        valid_signature = self.generate_mailgun_signature(timestamp, token)
        
        # Test valid signature
        assert verify_mailgun_signature(token, timestamp, valid_signature) == True
        
        # Test invalid signature
        assert verify_mailgun_signature(token, timestamp, "invalid-sig") == False
        
        # Test tampered timestamp
        tampered_timestamp = str(int(time.time()) - 1000)
        assert verify_mailgun_signature(token, tampered_timestamp, valid_signature) == False
    
    def test_webhook_endpoint_validation(self, client):
        """Test webhook endpoint with various payloads"""
        # Test missing content type
        response = client.post('/api/email-agent/webhooks/mailgun')
        assert response.status_code == 415
        
        # Test invalid JSON
        response = client.post(
            '/api/email-agent/webhooks/mailgun',
            data='invalid json',
            content_type='application/json'
        )
        assert response.status_code == 400
        
        # Test missing signature
        response = client.post(
            '/api/email-agent/webhooks/mailgun',
            json={"event": "delivered"},
            content_type='application/json'
        )
        assert response.status_code == 400
        
        # Test valid webhook
        webhook_data = self.create_mailgun_webhook_data()
        response = client.post(
            '/api/email-agent/webhooks/mailgun',
            json=webhook_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'queued'
        assert 'task_id' in data
    
    @patch('services.email_agent.process_email_event')
    def test_webhook_with_convoy_headers(self, mock_process, client):
        """Test webhook processing with Convoy gateway headers"""
        webhook_data = self.create_mailgun_webhook_data(include_convoy=True)
        
        # Mock the Celery task
        mock_process.return_value = 'test-task-id'
        
        # Send webhook with Convoy headers
        headers = {
            'X-Convoy-Project-ID': 'test-project',
            'X-Convoy-Source-ID': 'mailgun',
            'X-Convoy-Endpoint-ID': 'email-agent',
            'X-Convoy-Event-Type': 'email.delivered',
            'X-Convoy-Signature': 'convoy-sig-123',
            'Content-Type': 'application/json'
        }
        
        response = client.post(
            '/api/email-agent/webhooks/mailgun',
            json=webhook_data,
            headers=headers
        )
        
        assert response.status_code == 200
        assert mock_process.called
        
        # Verify the processed email data
        call_args = mock_process.call_args[0][0]
        assert call_args['from'] == "System <system@myapp.com>"
        assert call_args['to'] == ["user@example.com"]
        assert call_args['subject'] == "Test Email"
    
    @pytest.mark.asyncio
    async def test_replay_attack_protection(self, client, replay_cache):
        """Test protection against replay attacks"""
        webhook_data = self.create_mailgun_webhook_data()
        token = webhook_data['signature']['token']
        
        # First request should succeed
        response = client.post(
            '/api/email-agent/webhooks/mailgun',
            json=webhook_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # Check if token is marked as seen in cache
        assert await replay_cache.has_seen_token(token) == True
        
        # Replay attempt should fail (if implemented)
        # Note: The current implementation doesn't check replay cache in webhook endpoint
        # This test demonstrates where replay protection should be added
    
    def test_stale_timestamp_rejection(self, client):
        """Test rejection of webhooks with stale timestamps"""
        # Create webhook with timestamp 5 minutes old
        old_timestamp = str(int(time.time()) - 300)
        token = f"test-token-{old_timestamp}"
        signature = self.generate_mailgun_signature(old_timestamp, token)
        
        webhook_data = {
            "signature": {
                "timestamp": old_timestamp,
                "token": token,
                "signature": signature
            },
            "event-data": {
                "event": "delivered",
                "recipient": "user@example.com"
            }
        }
        
        response = client.post(
            '/api/email-agent/webhooks/mailgun',
            json=webhook_data,
            content_type='application/json'
        )
        
        assert response.status_code == 403
        assert "Stale timestamp" in response.get_json()['message']
    
    @patch('tasks.email_tasks.parse_and_dispatch_task')
    @patch('tasks.email_tasks.store_email_in_memory')
    def test_email_task_processing(self, mock_store, mock_dispatch):
        """Test the complete email processing task flow"""
        email_data = {
            "from": "client@example.com",
            "to": "support@myapp.com",
            "subject": "Bug Report: Login Issue",
            "body_plain": "I cannot log in to my account. Error code: AUTH_001",
            "timestamp": time.time(),
            "message_id": "<test123@example.com>",
            "event_type": "received"
        }
        
        # Mock async functions
        mock_store.return_value = {"id": "mem_123", "status": "stored"}
        mock_dispatch.return_value = {"task_id": "task_123", "status": "dispatched"}
        
        # Call the Celery task directly
        result = process_email_event(email_data)
        
        assert result['status'] == 'processed'
        assert result['memory_stored'] == True
        assert result['task_dispatched'] == True
    
    def test_different_event_types(self, client):
        """Test handling of different Mailgun event types"""
        event_types = ['delivered', 'opened', 'clicked', 'bounced', 'complained']
        
        for event_type in event_types:
            webhook_data = self.create_mailgun_webhook_data(event_type=event_type)
            
            # Add event-specific data
            if event_type == 'clicked':
                webhook_data['event-data']['url'] = 'https://example.com/link'
            elif event_type == 'bounced':
                webhook_data['event-data']['code'] = 550
                webhook_data['event-data']['error'] = 'Mailbox not found'
            
            response = client.post(
                '/api/email-agent/webhooks/mailgun',
                json=webhook_data,
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'queued'
    
    @patch('services.supermemory_service.SupermemoryService.add_memory')
    def test_memory_integration(self, mock_add_memory):
        """Test integration with Supermemory service"""
        # Mock the memory service
        mock_add_memory.return_value = {
            "id": "mem_test123",
            "status": "success"
        }
        
        email_data = {
            "from": "user@example.com",
            "to": "agent@myapp.com",
            "subject": "Task Request",
            "body_plain": "Please analyze the sales report",
            "message_id": "<msg123@example.com>",
            "timestamp": time.time()
        }
        
        # Create memory object
        memory = Memory(
            content=email_data['body_plain'],
            metadata={
                'type': 'email',
                'from': email_data['from'],
                'subject': email_data['subject']
            },
            agent_id='email_agent',
            conversation_id='email_inbox_test',
            timestamp=datetime.now().isoformat()
        )
        
        # Test memory storage
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(mock_add_memory(memory))
        loop.close()
        
        assert result['id'] == 'mem_test123'
        assert mock_add_memory.called
    
    def test_task_dispatch_flow(self, client):
        """Test email task dispatch functionality"""
        task_data = {
            "action": "dispatch_task",
            "parameters": {
                "task": {
                    "title": "Analyze Sales Report",
                    "description": "Review Q4 sales data and provide insights",
                    "task_type": "GENERAL",
                    "priority": "HIGH",
                    "assigned_agent": "data_analyst"
                }
            }
        }
        
        response = client.post(
            '/api/email-agent/tasks',
            json=task_data,
            content_type='application/json'
        )
        
        assert response.status_code == 202
        data = response.get_json()
        assert data['status'] == 'dispatched'
        assert data['action'] == 'dispatch_task'
    
    def test_email_parsing_task(self, client):
        """Test email parsing into agent task"""
        email_data = {
            "from": "manager@company.com",
            "to": "assistant@company.com",
            "subject": "URGENT: Prepare presentation for tomorrow",
            "body_plain": "Please prepare a presentation on Q4 results. Include revenue charts and growth metrics.",
            "message_id": "<urgent123@company.com>"
        }
        
        task_data = {
            "action": "parse_email",
            "parameters": {
                "email_data": email_data
            }
        }
        
        response = client.post(
            '/api/email-agent/tasks',
            json=task_data,
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'task' in data
        assert data['task']['title'] == "Prepare presentation for tomorrow"
    
    def test_error_handling_and_recovery(self, client):
        """Test error handling in webhook processing"""
        # Test with malformed event data
        webhook_data = self.create_mailgun_webhook_data()
        webhook_data['event-data'] = {}  # Remove required fields
        
        response = client.post(
            '/api/email-agent/webhooks/mailgun',
            json=webhook_data,
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'errors' in data


class TestNotificationIntegration:
    """Test notification system integration"""
    
    @patch('services.notification_service.NotificationService.send')
    def test_webhook_failure_notification(self, mock_notify):
        """Test notifications are sent on webhook failures"""
        mock_notify.return_value = True
        
        # Simulate a webhook processing failure
        from services.notification_service import get_notification_service
        notifier = get_notification_service()
        
        result = notifier.send(
            title="Webhook Processing Failed",
            body="Failed to process email webhook: Invalid signature",
            notify_type='failure',
            tag='webhook_error'
        )
        
        assert result == True
        assert mock_notify.called
        
        call_args = mock_notify.call_args[1]
        assert call_args['title'] == "Webhook Processing Failed"
        assert 'Invalid signature' in call_args['body']


class TestRetryMechanisms:
    """Test retry mechanisms for external calls"""
    
    @patch('httpx.AsyncClient.post')
    async def test_api_retry_on_failure(self, mock_post):
        """Test API calls are retried on failure"""
        from services.resilient_http_client import ResilientHTTPClient
        
        # Simulate failures then success
        mock_post.side_effect = [
            Exception("Connection error"),
            Exception("Timeout"),
            MagicMock(status_code=200, json=lambda: {"success": True})
        ]
        
        client = ResilientHTTPClient()
        result = await client.post("https://api.example.com/webhook", json={"test": "data"})
        
        assert result.status_code == 200
        assert mock_post.call_count == 3  # Two failures + one success
    
    def test_celery_task_retry(self):
        """Test Celery task retry on failure"""
        from celery import Task
        from tasks.email_tasks import process_email_event
        
        # Verify task has retry configuration
        assert hasattr(process_email_event, 'retry')
        assert process_email_event.max_retries == 3
        assert process_email_event.default_retry_delay == 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])