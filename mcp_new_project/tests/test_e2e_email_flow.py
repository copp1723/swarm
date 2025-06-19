#!/usr/bin/env python3
"""
End-to-End Test Script for Email Agent
Tests the complete flow from email receipt to task dispatch
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = os.getenv('TEST_BASE_URL', 'http://localhost:5006')
WEBHOOK_ENDPOINT = f"{BASE_URL}/api/email-agent/webhooks/mailgun"
TASKS_ENDPOINT = f"{BASE_URL}/api/email-agent/tasks"

# Test scenarios
TEST_SCENARIOS = [
    {
        "name": "Urgent Bug Report",
        "description": "Tests urgent priority bug report processing",
        "email": {
            "sender": "user@example.com",
            "recipient": "dev@company.com",
            "subject": "URGENT: Production server is down!",
            "body": "The production server is throwing 500 errors. Users can't login. This is critical and needs to be fixed ASAP! The error started happening after the last deployment at 2 PM.",
            "timestamp": str(int(datetime.utcnow().timestamp()))
        },
        "expected": {
            "priority": "urgent",
            "task_type": "bug_report",
            "primary_agent": "bug_01",
            "has_deadline": False
        }
    },
    {
        "name": "Feature Request with Deadline",
        "description": "Tests feature request with deadline extraction",
        "email": {
            "sender": "product@example.com",
            "recipient": "dev@company.com",
            "subject": "New feature: User Dashboard",
            "body": "We need to implement a new user dashboard feature. Requirements:\n- Show user statistics\n- Display recent activity\n- Add export functionality\n\nThis needs to be completed by end of month for the Q4 release.",
            "timestamp": str(int(datetime.utcnow().timestamp()))
        },
        "expected": {
            "priority": "medium",
            "task_type": "feature_request",
            "primary_agent": "product_01",
            "has_deadline": True
        }
    },
    {
        "name": "Code Review Request",
        "description": "Tests code review task assignment",
        "email": {
            "sender": "developer@example.com",
            "recipient": "team@company.com",
            "subject": "Please review PR #123",
            "body": "Hi team,\n\nI've submitted PR #123 for the authentication refactor. Could someone please review it? The changes include:\n- Updated JWT handling\n- New middleware for auth\n- Unit tests\n\nThanks!",
            "timestamp": str(int(datetime.utcnow().timestamp()))
        },
        "expected": {
            "priority": "medium",
            "task_type": "code_review",
            "primary_agent": "coder_01",
            "has_deadline": False
        }
    },
    {
        "name": "Low Priority Documentation",
        "description": "Tests low priority documentation task",
        "email": {
            "sender": "team@example.com",
            "recipient": "docs@company.com",
            "subject": "Documentation update needed",
            "body": "When you have time, could you update the API documentation for the new endpoints? No rush on this, just whenever you get a chance.",
            "timestamp": str(int(datetime.utcnow().timestamp()))
        },
        "expected": {
            "priority": "low",
            "task_type": "documentation",
            "primary_agent": "product_01",
            "has_deadline": False
        }
    },
    {
        "name": "High Priority Deployment",
        "description": "Tests high priority deployment task",
        "email": {
            "sender": "manager@example.com",
            "recipient": "devops@company.com",
            "subject": "Important: Deploy hotfix to production today",
            "body": "We need to deploy the security hotfix to production by end of day today. The fix is already in the staging branch and has been tested.",
            "timestamp": str(int(datetime.utcnow().timestamp()))
        },
        "expected": {
            "priority": "high",
            "task_type": "deployment",
            "primary_agent": "devops_01",
            "has_deadline": True
        }
    }
]


def create_mailgun_webhook(email_data):
    """Create a Mailgun webhook payload"""
    return {
        "signature": {
            "timestamp": email_data["timestamp"],
            "token": "test-token",
            "signature": "test-signature"
        },
        "event-data": {
            "event": "stored",
            "timestamp": float(email_data["timestamp"]),
            "id": f"test-{email_data['timestamp']}"
        },
        "message": {
            "headers": {
                "to": email_data["recipient"],
                "message-id": f"<{email_data['timestamp']}@example.com>",
                "from": email_data["sender"],
                "subject": email_data["subject"]
            },
            "recipients": [email_data["recipient"]],
            "sender": email_data["sender"],
            "stripped-text": email_data["body"]
        }
    }


def test_webhook_endpoint(scenario):
    """Test the webhook endpoint with a scenario"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing: {scenario['name']}")
    logger.info(f"Description: {scenario['description']}")
    logger.info(f"{'='*60}")
    
    # Create webhook payload
    webhook_data = create_mailgun_webhook(scenario['email'])
    
    # Send webhook request
    try:
        response = requests.post(
            WEBHOOK_ENDPOINT,
            json=webhook_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            logger.info("✅ Webhook accepted")
            result = response.json()
            task_id = result.get('task_id')
            
            if task_id:
                logger.info(f"   Task ID: {task_id}")
                # Give system time to process
                time.sleep(2)
                
                # Verify task was created correctly
                return verify_task(task_id, scenario['expected'])
            else:
                logger.error("❌ No task ID returned")
                return False
        else:
            logger.error(f"❌ Webhook failed: {response.status_code}")
            logger.error(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Request failed: {str(e)}")
        return False


def verify_task(task_id, expected):
    """Verify task was created with expected properties"""
    try:
        # Query tasks endpoint
        response = requests.get(f"{TASKS_ENDPOINT}/{task_id}")
        
        if response.status_code == 200:
            task = response.json()
            
            # Verify priority
            if task.get('priority') == expected['priority']:
                logger.info(f"✅ Priority correct: {expected['priority']}")
            else:
                logger.error(f"❌ Priority mismatch: expected {expected['priority']}, got {task.get('priority')}")
                return False
            
            # Verify task type
            if task.get('task_type') == expected['task_type']:
                logger.info(f"✅ Task type correct: {expected['task_type']}")
            else:
                logger.error(f"❌ Task type mismatch: expected {expected['task_type']}, got {task.get('task_type')}")
                return False
            
            # Verify agent assignment
            agent_assignment = task.get('agent_assignment', {})
            if agent_assignment.get('primary_agent') == expected['primary_agent']:
                logger.info(f"✅ Agent assignment correct: {expected['primary_agent']}")
            else:
                logger.error(f"❌ Agent mismatch: expected {expected['primary_agent']}, got {agent_assignment.get('primary_agent')}")
                return False
            
            # Verify deadline extraction
            has_deadline = bool(task.get('requirements', {}).get('deadline'))
            if has_deadline == expected['has_deadline']:
                logger.info(f"✅ Deadline extraction correct: {'found' if has_deadline else 'none'}")
            else:
                logger.error(f"❌ Deadline mismatch: expected {expected['has_deadline']}, got {has_deadline}")
                return False
            
            return True
            
        else:
            logger.error(f"❌ Failed to fetch task: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Task verification failed: {str(e)}")
        return False


def test_edge_cases():
    """Test edge cases and error scenarios"""
    logger.info(f"\n{'='*60}")
    logger.info("Testing Edge Cases")
    logger.info(f"{'='*60}")
    
    edge_cases = [
        {
            "name": "Empty body",
            "webhook": {
                "message": {
                    "headers": {
                        "from": "test@example.com",
                        "subject": "Test"
                    },
                    "stripped-text": ""
                }
            }
        },
        {
            "name": "Missing sender",
            "webhook": {
                "message": {
                    "headers": {
                        "subject": "Test"
                    },
                    "stripped-text": "Test body"
                }
            }
        },
        {
            "name": "Invalid timestamp",
            "webhook": {
                "signature": {
                    "timestamp": "invalid"
                },
                "message": {
                    "headers": {
                        "from": "test@example.com",
                        "subject": "Test"
                    },
                    "stripped-text": "Test body"
                }
            }
        }
    ]
    
    passed = 0
    for case in edge_cases:
        logger.info(f"\nTesting: {case['name']}")
        
        try:
            response = requests.post(
                WEBHOOK_ENDPOINT,
                json=case['webhook'],
                headers={'Content-Type': 'application/json'}
            )
            
            # We expect these to be handled gracefully
            if response.status_code in [200, 400, 422]:
                logger.info("✅ Handled gracefully")
                passed += 1
            else:
                logger.error(f"❌ Unexpected response: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Request failed: {str(e)}")
    
    return passed == len(edge_cases)


def test_performance():
    """Test system performance with multiple concurrent requests"""
    logger.info(f"\n{'='*60}")
    logger.info("Testing Performance")
    logger.info(f"{'='*60}")
    
    # Create 10 test emails
    emails = []
    for i in range(10):
        email = {
            "sender": f"user{i}@example.com",
            "recipient": "test@company.com",
            "subject": f"Test email {i}",
            "body": f"This is test email number {i}. Please process this task.",
            "timestamp": str(int(datetime.utcnow().timestamp()) + i)
        }
        emails.append(create_mailgun_webhook(email))
    
    # Send all requests
    start_time = time.time()
    results = []
    
    for i, webhook in enumerate(emails):
        try:
            response = requests.post(
                WEBHOOK_ENDPOINT,
                json=webhook,
                headers={'Content-Type': 'application/json'}
            )
            results.append(response.status_code == 200)
        except:
            results.append(False)
    
    end_time = time.time()
    duration = end_time - start_time
    
    success_count = sum(1 for r in results if r)
    logger.info(f"Processed {len(emails)} emails in {duration:.2f} seconds")
    logger.info(f"Success rate: {success_count}/{len(emails)} ({success_count/len(emails)*100:.1f}%)")
    logger.info(f"Average time per email: {duration/len(emails):.3f} seconds")
    
    return success_count == len(emails)


def main():
    """Run all end-to-end tests"""
    logger.info("🚀 EMAIL AGENT END-TO-END TEST SUITE")
    logger.info(f"Target: {BASE_URL}")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/email-agent/health")
        if response.status_code != 200:
            logger.error("❌ Email Agent service is not running!")
            logger.error("Please start the service first:")
            logger.error("1. Start Redis: redis-server")
            logger.error("2. Start Celery: celery -A app.celery worker --loglevel=info")
            logger.error("3. Start Flask: python app.py")
            return
    except:
        logger.error("❌ Cannot connect to Email Agent service!")
        return
    
    # Run test scenarios
    scenario_results = []
    for scenario in TEST_SCENARIOS:
        result = test_webhook_endpoint(scenario)
        scenario_results.append((scenario['name'], result))
        time.sleep(1)  # Avoid overwhelming the system
    
    # Run edge case tests
    edge_case_result = test_edge_cases()
    
    # Run performance test
    performance_result = test_performance()
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for _, result in scenario_results if result)
    total = len(scenario_results)
    
    logger.info(f"\nScenario Tests: {passed}/{total} passed")
    for name, result in scenario_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {name}: {status}")
    
    logger.info(f"\nEdge Cases: {'✅ PASSED' if edge_case_result else '❌ FAILED'}")
    logger.info(f"Performance: {'✅ PASSED' if performance_result else '❌ FAILED'}")
    
    overall_success = (passed == total) and edge_case_result and performance_result
    
    if overall_success:
        logger.info("\n🎉 All tests passed!")
    else:
        logger.info(f"\n⚠️ Some tests failed")


if __name__ == "__main__":
    main()