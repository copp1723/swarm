"""
Load testing scenarios for production deployment
Simulates real-world usage patterns
"""

import pytest
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import statistics

from app_production import create_production_app
from services.db_task_storage import get_task_storage
from services.redis_cache_manager import get_cache_manager
from services.email_agent_integration import get_email_integration


class LoadTestMetrics:
    """Collect and analyze load test metrics"""
    
    def __init__(self):
        self.response_times = []
        self.errors = []
        self.successes = 0
        self.start_time = None
        self.end_time = None
    
    def start(self):
        self.start_time = time.time()
    
    def end(self):
        self.end_time = time.time()
    
    def record_success(self, response_time):
        self.response_times.append(response_time)
        self.successes += 1
    
    def record_error(self, error):
        self.errors.append(error)
    
    def get_summary(self):
        if not self.response_times:
            return {"error": "No successful requests"}
        
        return {
            "total_requests": self.successes + len(self.errors),
            "successful_requests": self.successes,
            "failed_requests": len(self.errors),
            "success_rate": self.successes / (self.successes + len(self.errors)),
            "total_time": self.end_time - self.start_time,
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "p95_response_time": statistics.quantiles(self.response_times, n=20)[18] if len(self.response_times) > 20 else max(self.response_times),
            "p99_response_time": statistics.quantiles(self.response_times, n=100)[98] if len(self.response_times) > 100 else max(self.response_times),
            "requests_per_second": self.successes / (self.end_time - self.start_time)
        }


class TestLoadScenarios:
    """Test various load scenarios"""
    
    @pytest.fixture
    def app(self):
        """Create test application"""
        app = create_production_app()
        app.config['TESTING'] = True
        with app.app_context():
            yield app
    
    def test_email_burst_scenario(self, app):
        """Simulate burst of incoming emails"""
        metrics = LoadTestMetrics()
        
        with app.app_context():
            email_integration = get_email_integration()
            
            # Generate burst of emails
            emails = []
            for i in range(50):
                emails.append({
                    "from": f"user{i}@example.com",
                    "subject": random.choice([
                        "Bug Report: Critical Issue",
                        "Feature Request: New Dashboard",
                        "Question: How to export data?",
                        "Support: Account locked",
                        "Feedback: Great product!"
                    ]),
                    "body_plain": f"Email content {i} with details about the issue or request.",
                    "message_id": f"burst{i}@example.com"
                })
            
            def process_email(email):
                start = time.time()
                try:
                    result = email_integration.process_incoming_email(email)
                    elapsed = time.time() - start
                    if result['success']:
                        metrics.record_success(elapsed)
                    else:
                        metrics.record_error(f"Failed: {result}")
                    return result
                except Exception as e:
                    metrics.record_error(str(e))
                    raise
            
            # Process emails concurrently (simulating burst)
            metrics.start()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(process_email, email) for email in emails]
                results = []
                for future in as_completed(futures):
                    try:
                        results.append(future.result())
                    except Exception as e:
                        print(f"Error processing email: {e}")
            metrics.end()
            
            # Analyze results
            summary = metrics.get_summary()
            print("\nEmail Burst Test Results:")
            print(f"Success Rate: {summary['success_rate']:.2%}")
            print(f"Avg Response Time: {summary['avg_response_time']:.3f}s")
            print(f"P95 Response Time: {summary['p95_response_time']:.3f}s")
            print(f"Requests/Second: {summary['requests_per_second']:.2f}")
            
            # Assertions
            assert summary['success_rate'] > 0.95  # 95% success rate
            assert summary['avg_response_time'] < 2.0  # Under 2 seconds average
    
    def test_sustained_load_scenario(self, app):
        """Simulate sustained load over time"""
        metrics = LoadTestMetrics()
        duration = 30  # 30 seconds test
        
        with app.app_context():
            task_storage = get_task_storage()
            cache = get_cache_manager()
            
            def create_and_query_task():
                start = time.time()
                try:
                    # Create task
                    task_id = f"sustained_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                    task = task_storage.create_task(
                        task_id=task_id,
                        description="Sustained load test task",
                        agents=["agent1", "agent2"],
                        metadata={"test_type": "sustained_load"}
                    )
                    
                    # Cache task
                    cache.set("tasks", task_id, task, ttl=300)
                    
                    # Query task
                    retrieved = task_storage.get_task(task_id)
                    cached = cache.get("tasks", task_id)
                    
                    elapsed = time.time() - start
                    if retrieved and cached:
                        metrics.record_success(elapsed)
                    else:
                        metrics.record_error("Task not found")
                    
                except Exception as e:
                    metrics.record_error(str(e))
            
            # Run sustained load
            metrics.start()
            end_time = time.time() + duration
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                
                while time.time() < end_time:
                    # Submit new tasks at a steady rate
                    futures.append(executor.submit(create_and_query_task))
                    time.sleep(0.1)  # 10 requests per second
                
                # Wait for all tasks to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Task error: {e}")
            
            metrics.end()
            
            # Analyze results
            summary = metrics.get_summary()
            print("\nSustained Load Test Results:")
            print(f"Total Requests: {summary['total_requests']}")
            print(f"Success Rate: {summary['success_rate']:.2%}")
            print(f"Avg Response Time: {summary['avg_response_time']:.3f}s")
            print(f"P99 Response Time: {summary['p99_response_time']:.3f}s")
            
            # Assertions
            assert summary['success_rate'] > 0.99  # 99% success rate
            assert summary['avg_response_time'] < 0.5  # Under 500ms average
    
    def test_mixed_workload_scenario(self, app):
        """Simulate mixed workload (emails, tasks, queries)"""
        metrics = LoadTestMetrics()
        
        with app.app_context():
            task_storage = get_task_storage()
            email_integration = get_email_integration()
            cache = get_cache_manager()
            
            def email_workload():
                start = time.time()
                try:
                    email = {
                        "from": f"mixed{random.randint(1, 100)}@example.com",
                        "subject": "Mixed workload test",
                        "body_plain": "Testing mixed workload scenario",
                        "message_id": f"mixed{int(time.time() * 1000)}@example.com"
                    }
                    result = email_integration.process_incoming_email(email)
                    elapsed = time.time() - start
                    if result['success']:
                        metrics.record_success(elapsed)
                    else:
                        metrics.record_error("Email processing failed")
                except Exception as e:
                    metrics.record_error(f"Email error: {e}")
            
            def task_workload():
                start = time.time()
                try:
                    task_id = f"mixed_task_{int(time.time() * 1000)}"
                    task = task_storage.create_task(
                        task_id=task_id,
                        description="Mixed workload task",
                        agents=["agent1"]
                    )
                    # Update task status
                    task_storage.update_task(task_id, status="running", progress=50)
                    task_storage.update_task(task_id, status="completed", progress=100)
                    
                    elapsed = time.time() - start
                    metrics.record_success(elapsed)
                except Exception as e:
                    metrics.record_error(f"Task error: {e}")
            
            def query_workload():
                start = time.time()
                try:
                    # Various queries
                    all_tasks = task_storage.get_all_tasks(limit=10)
                    active = task_storage.get_active_tasks()
                    
                    # Cache operations
                    cache_key = f"query_{random.randint(1, 100)}"
                    cache.set("queries", cache_key, {"data": "test"}, ttl=60)
                    cache.get("queries", cache_key)
                    
                    elapsed = time.time() - start
                    metrics.record_success(elapsed)
                except Exception as e:
                    metrics.record_error(f"Query error: {e}")
            
            # Define workload distribution
            workloads = [
                (email_workload, 0.3),  # 30% emails
                (task_workload, 0.5),   # 50% tasks
                (query_workload, 0.2)   # 20% queries
            ]
            
            # Run mixed workload
            metrics.start()
            with ThreadPoolExecutor(max_workers=15) as executor:
                futures = []
                
                for _ in range(200):  # 200 total operations
                    # Choose workload based on distribution
                    rand = random.random()
                    cumulative = 0
                    for workload_func, probability in workloads:
                        cumulative += probability
                        if rand < cumulative:
                            futures.append(executor.submit(workload_func))
                            break
                    
                    time.sleep(0.05)  # Stagger requests
                
                # Wait for completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Workload error: {e}")
            
            metrics.end()
            
            # Analyze results
            summary = metrics.get_summary()
            print("\nMixed Workload Test Results:")
            print(f"Total Operations: {summary['total_requests']}")
            print(f"Success Rate: {summary['success_rate']:.2%}")
            print(f"Avg Response Time: {summary['avg_response_time']:.3f}s")
            print(f"Median Response Time: {summary['median_response_time']:.3f}s")
            print(f"Operations/Second: {summary['requests_per_second']:.2f}")
            
            # Assertions
            assert summary['success_rate'] > 0.95  # 95% success rate
            assert summary['median_response_time'] < 1.0  # Under 1 second median
    
    def test_cache_effectiveness_under_load(self, app):
        """Test cache performance under load"""
        with app.app_context():
            cache = get_cache_manager()
            task_storage = get_task_storage()
            
            # Pre-populate some tasks
            task_ids = []
            for i in range(20):
                task_id = f"cache_load_{i}"
                task_storage.create_task(
                    task_id=task_id,
                    description=f"Cache test task {i}",
                    agents=["agent1"]
                )
                task_ids.append(task_id)
            
            # Measure cache performance
            cache_hits = 0
            cache_misses = 0
            db_queries = 0
            
            def get_task_with_cache(task_id):
                nonlocal cache_hits, cache_misses, db_queries
                
                # Try cache first
                cached = cache.get("tasks", task_id)
                if cached:
                    cache_hits += 1
                    return cached
                
                cache_misses += 1
                
                # Get from database
                task = task_storage.get_task(task_id)
                db_queries += 1
                
                if task:
                    # Cache for next time
                    cache.set("tasks", task_id, task, ttl=300)
                
                return task
            
            # Simulate load with repeated access patterns
            access_pattern = []
            for _ in range(1000):
                # 80% of requests for 20% of tasks (hotspot pattern)
                if random.random() < 0.8:
                    task_id = random.choice(task_ids[:4])
                else:
                    task_id = random.choice(task_ids)
                access_pattern.append(task_id)
            
            # Execute access pattern
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(get_task_with_cache, task_id) for task_id in access_pattern]
                for future in as_completed(futures):
                    future.result()
            
            elapsed = time.time() - start_time
            
            # Calculate metrics
            total_requests = cache_hits + cache_misses
            cache_hit_rate = cache_hits / total_requests
            
            print("\nCache Effectiveness Test Results:")
            print(f"Total Requests: {total_requests}")
            print(f"Cache Hits: {cache_hits}")
            print(f"Cache Misses: {cache_misses}")
            print(f"Cache Hit Rate: {cache_hit_rate:.2%}")
            print(f"DB Queries: {db_queries}")
            print(f"Time Elapsed: {elapsed:.2f}s")
            print(f"Requests/Second: {total_requests / elapsed:.2f}")
            
            # Assertions
            assert cache_hit_rate > 0.7  # Should have > 70% cache hit rate
            assert db_queries < total_requests * 0.3  # DB queries should be < 30% of requests
            assert elapsed < 10.0  # Should complete within 10 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print statements