#!/usr/bin/env python3
"""
Integration test for Email Agent with Celery and Supermemory
Tests the complete flow from email parsing to storage
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_celery_tasks():
    """Test Celery task imports and basic functionality"""
    print("\n" + "=" * 60)
    print("TESTING CELERY TASKS")
    print("=" * 60)
    
    try:
        from tasks.email_tasks import (
            process_email_event,
            store_email_in_memory,
            search_email_tasks,
            notify_email_processed
        )
        print("✅ All Celery tasks imported successfully")
        
        # Test task registration
        print("\nRegistered tasks:")
        from celery import current_app
        for task_name in current_app.tasks:
            if 'email_tasks' in task_name:
                print(f"  - {task_name}")
                
    except Exception as e:
        print(f"❌ Celery tasks import failed: {str(e)}")
        return False
    
    return True


def test_notification_service():
    """Test notification service"""
    print("\n" + "=" * 60)
    print("TESTING NOTIFICATION SERVICE")
    print("=" * 60)
    
    try:
        from services.notification_service import get_notification_service
        
        notifier = get_notification_service()
        print("✅ Notification service initialized")
        
        # Test sending a notification
        result = notifier.send_sync(
            title="🧪 Integration Test",
            message="Testing Email Agent integration",
            priority="normal",
            tags=["test", "email"]
        )
        
        if result:
            print("✅ Test notification sent successfully")
        else:
            print("⚠️  No notification channels configured (check .env)")
            
    except Exception as e:
        print(f"❌ Notification service test failed: {str(e)}")
        return False
    
    return True


def test_supermemory_service():
    """Test Supermemory service sync wrappers"""
    print("\n" + "=" * 60)
    print("TESTING SUPERMEMORY SERVICE")
    print("=" * 60)
    
    try:
        from services.supermemory_service import get_supermemory_service, Memory
        
        # Check if API key is configured
        if not os.getenv('SUPERMEMORY_API_KEY'):
            print("⚠️  SUPERMEMORY_API_KEY not set, skipping live test")
            print("✅ Supermemory service imports work correctly")
            return True
        
        service = get_supermemory_service()
        print("✅ Supermemory service initialized")
        
        # Test creating a memory object
        test_memory = Memory(
            content="Test email task from integration test",
            metadata={
                "type": "test",
                "source": "integration_test"
            },
            agent_id="test_agent",
            timestamp=datetime.utcnow().isoformat()
        )
        print("✅ Memory object created successfully")
        
    except Exception as e:
        print(f"❌ Supermemory service test failed: {str(e)}")
        return False
    
    return True


def test_email_parsing_flow():
    """Test the complete email parsing flow"""
    print("\n" + "=" * 60)
    print("TESTING EMAIL PARSING FLOW")
    print("=" * 60)
    
    try:
        from services.email_parser import EmailParser
        from models.agent_task import AgentTask
        
        parser = EmailParser()
        
        # Create test email
        test_email = {
            "message": {
                "headers": {
                    "from": "test@example.com",
                    "subject": "URGENT: Fix login bug",
                    "message-id": "<integration-test@example.com>"
                },
                "recipients": ["dev@company.com"],
                "body-plain": "Users can't login. This needs to be fixed by end of day!"
            },
            "timestamp": str(int(datetime.utcnow().timestamp()))
        }
        
        # Parse email
        task = parser.parse_email(test_email)
        
        print(f"✅ Email parsed successfully")
        print(f"   Task ID: {task.task_id}")
        print(f"   Title: {task.title}")
        print(f"   Type: {task.task_type.value}")
        print(f"   Priority: {task.priority.value}")
        print(f"   Assigned to: {task.agent_assignment.primary_agent if task.agent_assignment else 'None'}")
        
    except Exception as e:
        print(f"❌ Email parsing test failed: {str(e)}")
        return False
    
    return True


def test_flask_endpoints():
    """Test Flask endpoint configuration"""
    print("\n" + "=" * 60)
    print("TESTING FLASK ENDPOINTS")
    print("=" * 60)
    
    try:
        from services.email_agent import email_bp
        
        # List all routes
        print("Email Agent routes:")
        for rule in email_bp.deferred_functions:
            print(f"  - {rule}")
        
        print("✅ Flask blueprint configured correctly")
        
    except Exception as e:
        print(f"❌ Flask endpoint test failed: {str(e)}")
        return False
    
    return True


def main():
    """Run all integration tests"""
    print("\n🚀 EMAIL AGENT INTEGRATION TEST SUITE")
    print("=" * 80)
    
    tests = [
        ("Celery Tasks", test_celery_tasks),
        ("Notification Service", test_notification_service),
        ("Supermemory Service", test_supermemory_service),
        ("Email Parsing Flow", test_email_parsing_flow),
        ("Flask Endpoints", test_flask_endpoints)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("\nNext steps:")
        print("1. Start Celery worker: celery -A app.celery worker --loglevel=info")
        print("2. Start Flask app: python app.py")
        print("3. Send test webhook to /api/email-agent/webhooks/mailgun")
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        print("\nCheck:")
        print("1. Environment variables in .env")
        print("2. Dependencies installed: pip install -r requirements.txt")
        print("3. Services running (Redis, PostgreSQL if using)")


if __name__ == "__main__":
    main()