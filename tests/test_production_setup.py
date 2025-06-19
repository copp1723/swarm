"""
Comprehensive test suite for production setup
Tests database connections, caching, email integration, and scalability
"""

import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, MagicMock
import os
from datetime import datetime, timedelta

# Set test environment
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

from app_production import create_production_app
from config.production_database import ProductionDatabaseManager
from services.redis_cache_manager import get_cache_manager, get_task_cache
from services.email_agent_integration import get_email_integration
from services.db_task_storage import get_task_storage
from models.core import db
from models.task_storage import CollaborationTask


class TestProductionDatabase:
    """Test production database functionality"""
    
    @pytest.fixture
    def app(self):
        """Create test application"""
        app = create_production_app()
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def db_manager(self):
        """Create test database manager"""
        return ProductionDatabaseManager()
    
    def test_database_connection_pool(self, app, db_manager):
        """Test database connection pooling"""
        with app.app_context():
            # Test health check
            health = db_manager.health_check()
            assert health['healthy'] is True
            assert 'postgres' in health
            
            # Test connection pool under load
            pool_size = db_manager.engine.pool.size()
            assert pool_size > 0
    
    def test_database_failover(self, db_manager):
        """Test database failover mechanism"""
        # Simulate primary failure
        with patch.object(db_manager, '_create_postgres_engine', side_effect=Exception("Connection failed")):
            # Should fall back to SQLite
            health = db_manager.health_check()
            assert health['postgres']['status'] == 'error'
            assert db_manager.engine is not None
    
    def test_concurrent_database_operations(self, app):
        """Test database under concurrent load"""
        with app.app_context():
            task_storage = get_task_storage()
            
            def create_task(i):
                return task_storage.create_task(
                    task_id=f"test_task_{i}",
                    description=f"Test task {i}",
                    agents=["agent1", "agent2"]
                )
            
            # Create tasks concurrently
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(create_task, i) for i in range(50)]
                results = [f.result() for f in as_completed(futures)]
            
            assert len(results) == 50
            
            # Verify all tasks were created
            all_tasks = task_storage.get_all_tasks()
            assert len(all_tasks) >= 50


class TestRedisCache:
    """Test Redis caching functionality"""
    
    @pytest.fixture
    def cache(self):
        """Get cache manager"""
        return get_cache_manager()
    
    def test_cache_operations(self, cache):
        """Test basic cache operations"""
        # Set and get
        assert cache.set("test", "key1", "value1", ttl=60)
        assert cache.get("test", "key1") == "value1"
        
        # Delete
        assert cache.delete("test", "key1")
        assert cache.get("test", "key1") is None
        
        # Set many
        mapping = {"k1": "v1", "k2": "v2", "k3": "v3"}
        assert cache.set_many("test", mapping)
        
        # Get many
        results = cache.get_many("test", ["k1", "k2", "k3"])
        assert results == mapping
    
    def test_cache_expiration(self, cache):
        """Test cache TTL"""
        cache.set("test", "expire", "value", ttl=1)
        assert cache.get("test", "expire") == "value"
        
        time.sleep(2)
        assert cache.get("test", "expire") is None
    
    def test_cache_performance(self, cache):
        """Test cache performance under load"""
        start_time = time.time()
        
        # Write test
        for i in range(1000):
            cache.set("perf", f"key_{i}", f"value_{i}")
        
        write_time = time.time() - start_time
        assert write_time < 5.0  # Should complete within 5 seconds
        
        # Read test
        start_time = time.time()
        for i in range(1000):
            cache.get("perf", f"key_{i}")
        
        read_time = time.time() - start_time
        assert read_time < 2.0  # Reads should be faster


class TestEmailIntegration:
    """Test email-to-agent integration"""
    
    @pytest.fixture
    def app(self):
        """Create test application"""
        app = create_production_app()
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def email_integration(self):
        """Get email integration service"""
        return get_email_integration()
    
    def test_email_parsing(self, email_integration):
        """Test email parsing to task"""
        email_data = {
            "from": "test@example.com",
            "subject": "Bug Report: Login Issue",
            "body_plain": "Users cannot log in after password reset.",
            "message_id": "test123@mail.example.com"
        }
        
        result = email_integration.parse_email_to_task(email_data)
        
        assert result['task_type'] == 'bug_report'
        assert result['priority'] == 'high'
        assert 'bug_hunter' in result['agents']
        assert result['description'] == "Users cannot log in after password reset."
    
    def test_email_processing_pipeline(self, app, email_integration):
        """Test full email processing pipeline"""
        with app.app_context():
            email_data = {
                "from": "user@example.com",
                "subject": "Feature Request: Dark Mode",
                "body_plain": "Please add dark mode to the application.",
                "message_id": "feat123@mail.example.com"
            }
            
            # Mock agent responses
            with patch('tasks.enhanced_email_tasks.call_agent_for_email') as mock_agent:
                mock_agent.apply_async.return_value.get.return_value = {
                    'agent_id': 'product_manager',
                    'content': 'Dark mode is a great suggestion. I\'ll add it to our roadmap.',
                    'model_used': 'gpt-4'
                }
                
                result = email_integration.process_incoming_email(email_data)
                
                assert result['success'] is True
                assert result['task_id'] is not None
                assert result['task_type'] == 'feature_request'
                
                # Verify task was created
                task_storage = get_task_storage()
                task = task_storage.get_task(result['task_id'])
                assert task is not None
                assert task['status'] == 'pending'
    
    def test_concurrent_email_processing(self, app, email_integration):
        """Test processing multiple emails concurrently"""
        with app.app_context():
            emails = [
                {
                    "from": f"user{i}@example.com",
                    "subject": f"Issue {i}",
                    "body_plain": f"This is issue number {i}",
                    "message_id": f"msg{i}@example.com"
                }
                for i in range(10)
            ]
            
            def process_email(email):
                return email_integration.process_incoming_email(email)
            
            # Process emails concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(process_email, email) for email in emails]
                results = [f.result() for f in as_completed(futures)]
            
            assert len(results) == 10
            assert all(r['success'] for r in results)


class TestCeleryTasks:
    """Test Celery task processing"""
    
    @pytest.fixture
    def app(self):
        """Create test application with Celery"""
        app = create_production_app()
        app.config['TESTING'] = True
        app.config['CELERY_ALWAYS_EAGER'] = True  # Execute tasks synchronously
        yield app
    
    def test_email_task_processing(self, app):
        """Test email task through Celery"""
        from tasks.enhanced_email_tasks import process_email_task
        
        with app.app_context():
            email_data = {
                "from": "test@example.com",
                "subject": "Test Task",
                "body_plain": "Test content"
            }
            
            parsed_task = {
                "description": "Test task",
                "priority": "medium"
            }
            
            agents = ["agent1", "agent2"]
            
            # Mock agent calls
            with patch('tasks.enhanced_email_tasks.call_agent_for_email') as mock_agent:
                mock_agent.apply_async.return_value.get.return_value = {
                    'agent_id': 'agent1',
                    'content': 'Test response',
                    'model_used': 'gpt-4'
                }
                
                with patch('tasks.enhanced_email_tasks.send_email_response') as mock_send:
                    mock_send.apply_async.return_value.get.return_value = {
                        'success': True,
                        'email_id': 'test123'
                    }
                    
                    result = process_email_task(
                        task_id="test_task_123",
                        email_data=email_data,
                        parsed_task=parsed_task,
                        agents=agents
                    )
                    
                    assert result['success'] is True
                    assert result['task_id'] == "test_task_123"


class TestScalabilityAndPerformance:
    """Test system scalability and performance"""
    
    @pytest.fixture
    def app(self):
        """Create test application"""
        app = create_production_app()
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_high_volume_task_creation(self, app):
        """Test system under high task creation load"""
        with app.app_context():
            task_storage = get_task_storage()
            start_time = time.time()
            
            # Create many tasks rapidly
            tasks = []
            for i in range(100):
                task = task_storage.create_task(
                    task_id=f"load_test_{i}",
                    description=f"Load test task {i}",
                    agents=["agent1"],
                    metadata={"test": True, "index": i}
                )
                tasks.append(task)
            
            elapsed = time.time() - start_time
            assert elapsed < 30.0  # Should complete within 30 seconds
            
            # Verify all tasks exist
            for task in tasks:
                retrieved = task_storage.get_task(task['task_id'])
                assert retrieved is not None
    
    def test_cache_hit_ratio(self, app):
        """Test cache effectiveness"""
        with app.app_context():
            task_cache = get_task_cache()
            
            # Prime cache
            for i in range(20):
                task_id = f"cache_test_{i}"
                task_data = {"id": task_id, "data": f"Task {i}"}
                task_cache.set_task(task_id, task_data)
            
            # Test cache hits
            hits = 0
            misses = 0
            
            for _ in range(100):
                for i in range(25):  # Some will hit, some will miss
                    task_id = f"cache_test_{i}"
                    result = task_cache.get_task(task_id)
                    if result:
                        hits += 1
                    else:
                        misses += 1
            
            hit_ratio = hits / (hits + misses)
            assert hit_ratio > 0.7  # Should have > 70% cache hit ratio
    
    def test_database_query_performance(self, app):
        """Test database query performance"""
        with app.app_context():
            # Create test data
            task_storage = get_task_storage()
            for i in range(50):
                task_storage.create_task(
                    task_id=f"perf_test_{i}",
                    description=f"Performance test {i}",
                    agents=["agent1", "agent2"],
                    metadata={"category": i % 5}
                )
            
            # Test query performance
            start_time = time.time()
            
            # Various queries
            all_tasks = task_storage.get_all_tasks()
            agent_tasks = task_storage.get_tasks_by_agent("agent1")
            active_tasks = task_storage.get_active_tasks()
            
            query_time = time.time() - start_time
            assert query_time < 2.0  # Queries should complete quickly
            
            assert len(all_tasks) >= 50
            assert len(agent_tasks) >= 50
    
    def test_memory_usage(self, app):
        """Test memory usage under load"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with app.app_context():
            # Create many objects
            task_storage = get_task_storage()
            tasks = []
            
            for i in range(1000):
                task = task_storage.create_task(
                    task_id=f"memory_test_{i}",
                    description=f"Memory test {i}" * 100,  # Large description
                    agents=["agent1", "agent2", "agent3"],
                    metadata={"data": "x" * 1000}  # Large metadata
                )
                tasks.append(task)
            
            # Force garbage collection
            gc.collect()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable
            assert memory_increase < 500  # Less than 500MB increase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])