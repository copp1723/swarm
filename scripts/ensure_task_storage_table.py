"""
Script to ensure task_storage table exists in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.core import db
from models.task_storage import TaskStorage
from app import app


def ensure_task_storage_table():
    """Create task_storage table if it doesn't exist"""
    with app.app_context():
        # Create tables for TaskStorage model
        db.create_all()
        print("Task storage table created/verified successfully")
        
        # Test the table by creating and deleting a test task
        try:
            test_task = TaskStorage.create_task(
                task_id="test_init_task",
                task_description="Test task for initialization"
            )
            print(f"Test task created: {test_task.id}")
            
            # Clean up test task
            db.session.delete(test_task)
            db.session.commit()
            print("Test task deleted successfully")
            
            print("\nTask storage database is ready for use!")
            
        except Exception as e:
            print(f"Error during test: {e}")
            db.session.rollback()


if __name__ == "__main__":
    ensure_task_storage_table()