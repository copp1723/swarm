"""
Test script to verify database persistence is working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.core import db
from models.task_storage import TaskStorage
from app import app
from services.multi_agent_service import get_multi_agent_service
import time


def test_persistence():
    """Test that tasks persist in the database"""
    with app.app_context():
        # Get the multi-agent service
        service = get_multi_agent_service()
        
        # Check what storage type is being used
        storage_type = type(service.storage).__name__
        print(f"\nUsing storage type: {storage_type}")
        
        # Create a test task
        test_task_id = f"test_task_{int(time.time())}"
        
        # Test direct database operations
        print("\n1. Testing direct database operations...")
        task = TaskStorage.create_task(
            task_id=test_task_id,
            task_description="Test persistence task",
            agents=["agent1", "agent2"]
        )
        print(f"Created task: {task.id}")
        
        # Retrieve the task
        retrieved = TaskStorage.get_task(test_task_id)
        if retrieved:
            print(f"Successfully retrieved task: {retrieved.id}")
            print(f"Task description: {retrieved.task_description}")
            print(f"Agents: {retrieved.agents}")
        else:
            print("ERROR: Could not retrieve task!")
        
        # Test service storage interface
        print("\n2. Testing service storage interface...")
        from services.multi_agent_executor import TaskStatus
        
        status = TaskStatus(
            task_id=f"service_test_{int(time.time())}",
            status="running",
            progress=50,
            current_phase="Testing",
            agents_working=["test_agent"],
            results={"test": "data"}
        )
        
        # Store using service storage
        service.storage.store_task(status.task_id, status)
        print(f"Stored task via service: {status.task_id}")
        
        # Retrieve using service storage
        retrieved_status = service.storage.get_task(status.task_id)
        if retrieved_status:
            # Handle both TaskStatus object and dict
            if hasattr(retrieved_status, 'task_id'):
                print(f"Successfully retrieved via service: {retrieved_status.task_id}")
                print(f"Status: {retrieved_status.status}")
                print(f"Progress: {retrieved_status.progress}")
            else:
                print(f"Successfully retrieved via service (as dict): {status.task_id}")
                print("Retrieved status type:", type(retrieved_status))
        else:
            print("ERROR: Could not retrieve task via service!")
        
        # Check database directly for service-created task
        db_task = TaskStorage.get_task(status.task_id)
        if db_task:
            print(f"\nDatabase verification - Task exists: {db_task.id}")
            print(f"Database status: {db_task.status}")
            print(f"Database progress: {db_task.progress}")
        else:
            print("\nERROR: Task not found in database!")
        
        # Clean up test tasks
        print("\n3. Cleaning up test tasks...")
        for task_id in [test_task_id, status.task_id]:
            task_to_delete = TaskStorage.get_task(task_id)
            if task_to_delete:
                db.session.delete(task_to_delete)
        db.session.commit()
        print("Test tasks cleaned up")
        
        print("\n✅ Database persistence test completed!")


if __name__ == "__main__":
    test_persistence()