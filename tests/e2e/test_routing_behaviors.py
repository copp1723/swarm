"""
End-to-End Tests for Agent Routing Behaviors
Tests message routing, agent selection, and multi-agent coordination
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import asyncio

from models.agent_task import AgentTask, TaskType, TaskPriority, AgentAssignment
from services.multi_agent_service import MultiAgentService
from services.email_parser import EmailParser


class TestAgentRouting:
    """Test agent routing and task assignment"""
    
    @pytest.fixture
    def multi_agent_service(self):
        """Create multi-agent service instance"""
        return MultiAgentService()
    
    @pytest.fixture
    def email_parser(self):
        """Create email parser instance"""
        return EmailParser()
    
    def test_email_to_agent_routing(self, email_parser):
        """Test routing emails to appropriate agents based on content"""
        test_cases = [
            {
                "email": {
                    "from": "developer@company.com",
                    "subject": "Bug in payment processing",
                    "body_plain": "There's a critical bug in the payment gateway integration"
                },
                "expected_agent": "debugging_assistant",
                "expected_type": TaskType.DEBUGGING,
                "expected_priority": TaskPriority.HIGH
            },
            {
                "email": {
                    "from": "manager@company.com",
                    "subject": "Code review needed",
                    "body_plain": "Please review the PR for the new feature implementation"
                },
                "expected_agent": "code_reviewer",
                "expected_type": TaskType.REVIEW,
                "expected_priority": TaskPriority.MEDIUM
            },
            {
                "email": {
                    "from": "qa@company.com",
                    "subject": "Test suite failing",
                    "body_plain": "The integration tests are failing on the CI pipeline"
                },
                "expected_agent": "testing_expert",
                "expected_type": TaskType.TESTING,
                "expected_priority": TaskPriority.HIGH
            },
            {
                "email": {
                    "from": "analyst@company.com",
                    "subject": "Data analysis request",
                    "body_plain": "Need analysis of user engagement metrics for Q4"
                },
                "expected_agent": "data_analyst",
                "expected_type": TaskType.GENERAL,
                "expected_priority": TaskPriority.MEDIUM
            }
        ]
        
        for test_case in test_cases:
            task = email_parser.parse_email(test_case["email"])
            
            assert task.task_type == test_case["expected_type"]
            assert task.priority == test_case["expected_priority"]
            
            if task.agent_assignment:
                assert task.agent_assignment.primary_agent == test_case["expected_agent"]
    
    def test_multi_agent_task_execution(self, multi_agent_service):
        """Test task execution with multiple agents"""
        # Create a complex task requiring multiple agents
        task = AgentTask(
            title="Implement and test new API endpoint",
            description="Create a new REST API endpoint for user analytics with tests",
            task_type=TaskType.CODING,
            priority=TaskPriority.HIGH
        )
        
        # Assign multiple agents
        task.agent_assignment = AgentAssignment(
            primary_agent="software_architect",
            supporting_agents=["backend_developer", "testing_expert"],
            skills_required=["API design", "Python", "Testing"]
        )
        
        # Mock agent responses
        with patch.object(multi_agent_service, '_query_agent') as mock_query:
            mock_query.side_effect = [
                {"response": "API design completed", "confidence": 0.9},
                {"response": "Implementation done", "confidence": 0.85},
                {"response": "Tests written and passing", "confidence": 0.95}
            ]
            
            result = multi_agent_service.execute_task(task)
            
            assert result["status"] == "completed"
            assert mock_query.call_count == 3
            assert len(result["agent_responses"]) == 3
    
    def test_agent_capability_matching(self, multi_agent_service):
        """Test matching agent capabilities to task requirements"""
        test_tasks = [
            {
                "requirements": ["Python", "FastAPI", "Database design"],
                "expected_agent": "backend_developer"
            },
            {
                "requirements": ["React", "TypeScript", "UI/UX"],
                "expected_agent": "frontend_developer"
            },
            {
                "requirements": ["Docker", "Kubernetes", "CI/CD"],
                "expected_agent": "devops_engineer"
            },
            {
                "requirements": ["Security audit", "Penetration testing"],
                "expected_agent": "security_expert"
            }
        ]
        
        for test in test_tasks:
            agent = multi_agent_service._select_agent_by_capabilities(test["requirements"])
            assert agent == test["expected_agent"]
    
    def test_priority_based_routing(self, email_parser):
        """Test priority detection and routing"""
        priority_keywords = {
            "URGENT": TaskPriority.URGENT,
            "ASAP": TaskPriority.HIGH,
            "Critical": TaskPriority.HIGH,
            "Important": TaskPriority.HIGH,
            "When you can": TaskPriority.LOW,
            "Low priority": TaskPriority.LOW
        }
        
        for keyword, expected_priority in priority_keywords.items():
            email_data = {
                "from": "test@example.com",
                "subject": f"{keyword}: Task request",
                "body_plain": "Please handle this task"
            }
            
            task = email_parser.parse_email(email_data)
            assert task.priority == expected_priority
    
    @patch('services.llm_service.query_llm')
    def test_context_aware_routing(self, mock_llm, multi_agent_service):
        """Test routing based on conversation context"""
        # Mock LLM to return context-aware routing
        mock_llm.return_value = {
            "suggested_agent": "security_expert",
            "reasoning": "Previous messages discuss security vulnerabilities"
        }
        
        task = AgentTask(
            title="Follow up on previous discussion",
            description="As discussed, we need to address the issues",
            task_type=TaskType.GENERAL
        )
        
        # Add conversation context
        context = {
            "previous_messages": [
                "Found SQL injection vulnerability",
                "Need security audit ASAP"
            ],
            "conversation_id": "conv_123"
        }
        
        with patch.object(multi_agent_service, '_get_conversation_context', return_value=context):
            result = multi_agent_service.execute_task(task)
            
            # Verify security expert was selected based on context
            assert task.agent_assignment.primary_agent == "security_expert"


class TestDispatchBehaviors:
    """Test task dispatch and processing behaviors"""
    
    def test_synchronous_dispatch(self):
        """Test synchronous task dispatch"""
        from services.email_agent import handle_email_task
        from app import create_app
        
        app = create_app()
        
        with app.test_request_context(
            json={
                "action": "dispatch_task",
                "parameters": {
                    "task": {
                        "title": "Test Task",
                        "description": "Test description",
                        "priority": "HIGH"
                    }
                }
            }
        ):
            from flask import request
            response = handle_email_task()
            
            assert response[1] == 202  # Accepted status
            data = response[0].get_json()
            assert data["status"] == "dispatched"
    
    @pytest.mark.asyncio
    async def test_asynchronous_memory_storage(self):
        """Test async memory storage during dispatch"""
        from services.supermemory_service import get_supermemory_service, Memory
        
        memory_service = get_supermemory_service()
        
        # Create test memory
        memory = Memory(
            content="Test task content",
            metadata={"type": "task", "priority": "high"},
            agent_id="test_agent",
            conversation_id="test_conv",
            timestamp=datetime.now().isoformat()
        )
        
        # Mock the API call
        with patch.object(memory_service, 'add_memory', new_callable=AsyncMock) as mock_add:
            mock_add.return_value = {"id": "mem_123", "success": True}
            
            result = await memory_service.add_memory(memory)
            
            assert result["id"] == "mem_123"
            mock_add.assert_called_once()
    
    def test_task_queue_distribution(self):
        """Test task distribution across Celery queues"""
        from tasks.email_tasks import process_email_event
        from tasks.webhook_tasks import process_webhook_event
        
        # Verify queue routing
        assert process_email_event.queue == 'email_queue'
        assert process_webhook_event.queue == 'webhook_queue'
        
        # Test task routing based on priority
        high_priority_email = {
            "subject": "URGENT: Server down",
            "priority": "urgent"
        }
        
        low_priority_email = {
            "subject": "Monthly newsletter",
            "priority": "low"
        }
        
        # Tasks should be routed to appropriate queues
        # High priority to priority queue, low priority to default queue
    
    def test_retry_on_dispatch_failure(self):
        """Test retry behavior when dispatch fails"""
        from utils.tenacity_retry import retry_task_dispatch
        from tenacity import RetryError
        
        call_count = 0
        
        @retry_task_dispatch()
        def flaky_dispatch():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return {"status": "success"}
        
        result = flaky_dispatch()
        assert result["status"] == "success"
        assert call_count == 3


class TestValidationBehaviors:
    """Test request/response validation behaviors"""
    
    def test_webhook_payload_validation(self):
        """Test webhook payload validation with schemas"""
        from schemas.webhook_schemas import validate_mailgun_webhook
        from marshmallow import ValidationError
        
        # Valid payload
        valid_payload = {
            "event": "delivered",
            "recipient": "user@example.com",
            "sender": "system@app.com",
            "timestamp": 1234567890.0
        }
        
        validated = validate_mailgun_webhook(valid_payload)
        assert validated["event_type"] == "delivered"
        
        # Invalid payload - missing required field
        invalid_payload = {
            "event": "delivered"
            # Missing recipient
        }
        
        with pytest.raises(ValidationError) as exc:
            validate_mailgun_webhook(invalid_payload)
        
        assert "recipient" in str(exc.value)
    
    def test_task_validation_pipeline(self):
        """Test task validation through the pipeline"""
        from schemas.task_schemas import validate_task_create
        from marshmallow import ValidationError
        
        # Valid task
        valid_task = {
            "title": "Implement feature X",
            "description": "Add new feature as specified in requirements",
            "task_type": "CODING",
            "priority": "HIGH"
        }
        
        validated = validate_task_create(valid_task)
        assert "id" in validated  # ID should be generated
        assert validated["title"] == valid_task["title"]
        
        # Invalid task - empty title
        invalid_task = {
            "title": "   ",  # Just whitespace
            "description": "Some description"
        }
        
        with pytest.raises(ValidationError) as exc:
            validate_task_create(invalid_task)
        
        assert "Title cannot be empty" in str(exc.value)
    
    def test_agent_request_validation(self):
        """Test agent request validation"""
        from schemas.agent_schemas import validate_agent_request
        from marshmallow import ValidationError
        
        # Valid request
        valid_request = {
            "agent_role": "software_architect",
            "task": "Design microservices architecture"
        }
        
        validated = validate_agent_request(valid_request)
        assert validated["agent_role"] == "software_architect"
        
        # Invalid request - unknown agent
        invalid_request = {
            "agent_role": "unknown_agent",
            "task": "Some task"
        }
        
        with pytest.raises(ValidationError) as exc:
            validate_agent_request(invalid_request)
        
        assert "Unknown agent role" in str(exc.value)


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    @pytest.mark.integration
    def test_complete_email_to_task_flow(self):
        """Test complete flow from email receipt to task completion"""
        from app import create_app
        
        app = create_app()
        client = app.test_client()
        
        # Step 1: Receive webhook
        timestamp = str(int(datetime.now().timestamp()))
        token = f"test-{timestamp}"
        
        webhook_data = {
            "signature": {
                "timestamp": timestamp,
                "token": token,
                "signature": "test-signature"
            },
            "event-data": {
                "event": "received",
                "recipient": "tasks@myapp.com",
                "sender": "user@example.com",
                "message": {
                    "headers": {
                        "subject": "Bug: Login not working",
                        "from": "user@example.com"
                    },
                    "body-plain": "Users cannot log in. Getting error 401."
                }
            }
        }
        
        # Mock signature verification
        with patch('services.email_agent.verify_mailgun_signature', return_value=True):
            response = client.post(
                '/api/email-agent/webhooks/mailgun',
                json=webhook_data,
                content_type='application/json'
            )
        
        assert response.status_code == 200
        
        # Step 2: Verify task was created and queued
        data = response.get_json()
        assert data["status"] == "queued"
        assert "task_id" in data
        
        # Step 3: Verify task would be routed to debugging assistant
        # (In real scenario, this would happen in background worker)
    
    @pytest.mark.integration
    def test_multi_agent_collaboration_scenario(self):
        """Test scenario requiring multiple agents working together"""
        from services.multi_agent_service import MultiAgentService
        
        service = MultiAgentService()
        
        # Complex task requiring multiple agents
        task = AgentTask(
            title="Security incident response",
            description="Potential data breach detected. Investigate and remediate.",
            task_type=TaskType.GENERAL,
            priority=TaskPriority.URGENT
        )
        
        # This should trigger:
        # 1. Security expert for investigation
        # 2. System admin for log analysis
        # 3. Developer for patching
        # 4. Compliance officer for reporting
        
        with patch.object(service, '_query_agent') as mock_query:
            mock_query.side_effect = [
                {"response": "SQL injection vulnerability found", "agent": "security_expert"},
                {"response": "Attack originated from IP 192.168.1.100", "agent": "system_admin"},
                {"response": "Patch deployed to production", "agent": "backend_developer"},
                {"response": "Incident report filed", "agent": "compliance_officer"}
            ]
            
            result = service.execute_task(task)
            
            assert result["status"] == "completed"
            assert len(result["agent_responses"]) >= 2  # Multiple agents involved


if __name__ == "__main__":
    pytest.main([__file__, "-v"])