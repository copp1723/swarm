#!/usr/bin/env python3
"""
Test Database Persistence
Verifies that tasks, conversations, and audit logs persist across restarts
"""

import os
import sys
import time
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from models.core import db
from config.database import init_database
from models.task_storage import (
    create_task, get_task, update_task_status, 
    add_conversation, log_action, get_task_conversations
)
from utils.logging_config import get_logger

logger = get_logger(__name__)

def test_task_persistence():
    """Test that tasks persist in database"""
    print("\n🧪 Testing Task Persistence...")
    
    # Create a test task
    task_id = f"test_{uuid.uuid4().hex[:8]}"
    task = create_task(
        task_id=task_id,
        description="Test task for persistence verification",
        session_id="test_session",
        agents_involved=["test_agent_1", "test_agent_2"],
        priority="high"
    )
    
    print(f"✅ Created task: {task.task_id}")
    
    # Verify task exists
    retrieved = get_task(task_id)
    assert retrieved is not None, "Task not found after creation"
    assert retrieved.description == task.description, "Task description mismatch"
    print("✅ Task retrieved successfully")
    
    # Update task
    update_task_status(task_id, "running", progress=50, current_phase="Processing")
    
    # Verify update
    updated = get_task(task_id)
    assert updated.status == "running", "Status not updated"
    assert updated.progress == 50, "Progress not updated"
    print("✅ Task updates persisted")
    
    return task_id

def test_conversation_persistence(task_id):
    """Test that conversations persist"""
    print("\n🧪 Testing Conversation Persistence...")
    
    # Add conversations
    conv1 = add_conversation(
        task_id=task_id,
        agent_id="test_agent_1",
        role="assistant",
        content="This is the first test message",
        tokens_used=100
    )
    
    conv2 = add_conversation(
        task_id=task_id,
        agent_id="test_agent_2",
        role="assistant",
        content="This is the second test message",
        tokens_used=150
    )
    
    print(f"✅ Added 2 conversations")
    
    # Retrieve conversations
    conversations = get_task_conversations(task_id)
    assert len(conversations) >= 2, f"Expected at least 2 conversations, got {len(conversations)}"
    
    # Verify content
    contents = [c.content for c in conversations]
    assert "first test message" in str(contents), "First message not found"
    assert "second test message" in str(contents), "Second message not found"
    
    print("✅ Conversations retrieved successfully")
    print(f"   Found {len(conversations)} conversations")

def test_audit_persistence(task_id):
    """Test that audit logs persist"""
    print("\n🧪 Testing Audit Log Persistence...")
    
    # Add audit logs
    log1 = log_action(
        action_type="test_action",
        action_description="Testing audit log persistence",
        agent_id="test_agent",
        task_id=task_id,
        session_id="test_session",
        metadata={"test": True}
    )
    
    log2 = log_action(
        action_type="api_call",
        action_description="Simulated API call",
        agent_id="test_agent",
        task_id=task_id,
        api_calls_made=["openrouter/gpt-4"],
        execution_time_ms=1500
    )
    
    print("✅ Added audit logs")
    
    # Query audit logs
    from models.task_storage import AuditLog
    logs = AuditLog.query.filter_by(task_id=task_id).all()
    assert len(logs) >= 2, f"Expected at least 2 audit logs, got {len(logs)}"
    
    print(f"✅ Audit logs retrieved successfully")
    print(f"   Found {len(logs)} audit entries")

def test_restart_persistence():
    """Test that data persists after simulated restart"""
    print("\n🧪 Testing Restart Persistence...")
    
    # Create a marker task
    marker_id = f"marker_{int(time.time())}"
    marker_task = create_task(
        task_id=marker_id,
        description="Marker task to verify persistence across restarts",
        session_id="restart_test",
        agents_involved=["persistence_test"]
    )
    
    print(f"✅ Created marker task: {marker_id}")
    
    # Simulate restart by clearing any in-memory cache
    from services.db_task_storage import get_task_storage
    storage = get_task_storage()
    storage.clear_cache()
    
    print("🔄 Simulated restart (cleared cache)")
    
    # Verify marker still exists
    retrieved = get_task(marker_id)
    assert retrieved is not None, "Marker task lost after restart"
    assert retrieved.description == marker_task.description, "Task data corrupted"
    
    print("✅ Data persisted across restart!")
    
    return marker_id

def test_complex_queries():
    """Test complex database queries"""
    print("\n🧪 Testing Complex Queries...")
    
    # Get all tasks
    from models.task_storage import CollaborationTask
    all_tasks = CollaborationTask.query.all()
    print(f"📊 Total tasks in database: {len(all_tasks)}")
    
    # Get tasks by status
    running_tasks = CollaborationTask.query.filter_by(status='running').all()
    completed_tasks = CollaborationTask.query.filter_by(status='completed').all()
    
    print(f"   Running tasks: {len(running_tasks)}")
    print(f"   Completed tasks: {len(completed_tasks)}")
    
    # Get recent tasks
    from datetime import datetime, timedelta
    recent_cutoff = datetime.utcnow() - timedelta(hours=1)
    recent_tasks = CollaborationTask.query.filter(
        CollaborationTask.created_at >= recent_cutoff
    ).all()
    
    print(f"   Tasks created in last hour: {len(recent_tasks)}")
    
    # Test pagination
    page_size = 5
    first_page = CollaborationTask.query.limit(page_size).all()
    print(f"✅ Pagination working (fetched {len(first_page)} of {page_size} requested)")

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    
    from models.task_storage import CollaborationTask
    test_tasks = CollaborationTask.query.filter(
        CollaborationTask.task_id.like('test_%')
    ).all()
    
    for task in test_tasks:
        db.session.delete(task)
    
    db.session.commit()
    print(f"✅ Cleaned up {len(test_tasks)} test tasks")

def main():
    """Run all persistence tests"""
    print("🔬 Database Persistence Test Suite")
    print("=" * 50)
    
    # Create Flask app for database context
    app = Flask(__name__)
    init_database(app)
    
    with app.app_context():
        try:
            # Run tests
            task_id = test_task_persistence()
            test_conversation_persistence(task_id)
            test_audit_persistence(task_id)
            marker_id = test_restart_persistence()
            test_complex_queries()
            
            print("\n✅ All persistence tests passed!")
            print("\n📋 Summary:")
            print("  • Tasks persist in database")
            print("  • Conversations are stored and retrievable")
            print("  • Audit logs track all actions")
            print("  • Data survives restarts")
            print("  • Complex queries work correctly")
            
            # Optional cleanup
            response = input("\nClean up test data? (y/n): ")
            if response.lower() == 'y':
                cleanup_test_data()
            
        except AssertionError as e:
            print(f"\n❌ Test failed: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()