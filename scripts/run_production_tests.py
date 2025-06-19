#!/usr/bin/env python3
"""
Run production tests locally before deployment
Tests database, cache, email integration, and performance
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add project to path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))


def setup_test_environment():
    """Set up test environment variables"""
    print("Setting up test environment...")
    
    # Use test database
    os.environ['DATABASE_URL'] = 'sqlite:///test_production.db'
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['TESTING'] = 'true'
    
    # Use test Redis (if available)
    os.environ['REDIS_URL'] = os.environ.get('REDIS_URL', 'redis://localhost:6379/15')
    
    # Mock email settings
    os.environ['MAILGUN_API_KEY'] = 'test-key'
    os.environ['MAILGUN_DOMAIN'] = 'test.example.com'
    
    print("Test environment configured")


def check_dependencies():
    """Check if required services are available"""
    print("\nChecking dependencies...")
    
    # Check Redis
    try:
        import redis
        r = redis.Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/15'))
        r.ping()
        print("✓ Redis is available")
    except Exception as e:
        print(f"✗ Redis not available: {e}")
        print("  Using mock Redis for tests")
        os.environ['USE_MOCK_REDIS'] = 'true'
    
    # Check PostgreSQL (optional for local tests)
    try:
        import psycopg2
        print("✓ PostgreSQL driver available")
    except ImportError:
        print("✗ PostgreSQL driver not installed")
        print("  Using SQLite for tests")
    
    print("Dependency check complete")


def run_unit_tests():
    """Run unit tests"""
    print("\n" + "="*60)
    print("Running Unit Tests")
    print("="*60)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_production_setup.py",
        "-v", "--tb=short"
    ]
    
    result = subprocess.run(cmd, cwd=project_dir)
    return result.returncode == 0


def run_load_tests():
    """Run load tests"""
    print("\n" + "="*60)
    print("Running Load Tests")
    print("="*60)
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_load_scenarios.py",
        "-v", "-s", "--tb=short"
    ]
    
    result = subprocess.run(cmd, cwd=project_dir)
    return result.returncode == 0


def run_integration_tests():
    """Run integration tests with real services"""
    print("\n" + "="*60)
    print("Running Integration Tests")
    print("="*60)
    
    # Start test server
    print("Starting test server...")
    server_process = subprocess.Popen(
        [sys.executable, "app_production.py"],
        cwd=project_dir,
        env=os.environ.copy()
    )
    
    # Wait for server to start
    time.sleep(3)
    
    try:
        # Test health endpoint
        import requests
        response = requests.get("http://localhost:5006/health")
        print(f"Health check response: {response.status_code}")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"Database healthy: {health_data.get('database', {}).get('postgres', {}).get('healthy', False)}")
            print(f"Cache healthy: {health_data.get('cache', False)}")
        
        # Test metrics endpoint
        response = requests.get("http://localhost:5006/metrics")
        print(f"Metrics response: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        return False
    
    finally:
        # Stop test server
        server_process.terminate()
        server_process.wait()
        print("Test server stopped")


def run_database_migrations_test():
    """Test database migrations"""
    print("\n" + "="*60)
    print("Testing Database Migrations")
    print("="*60)
    
    try:
        # Run migrations
        from migrations.run_migrations import run_all_migrations
        from models.core import db
        from app_production import create_production_app
        
        app = create_production_app()
        with app.app_context():
            # Create tables
            db.create_all()
            print("✓ Database tables created")
            
            # Run any custom migrations
            run_all_migrations()
            print("✓ Migrations completed")
            
            # Verify tables
            from models.task_storage import CollaborationTask, ConversationHistory, AuditLog
            
            # Test queries
            task_count = CollaborationTask.query.count()
            print(f"✓ CollaborationTask table accessible (count: {task_count})")
            
            history_count = ConversationHistory.query.count()
            print(f"✓ ConversationHistory table accessible (count: {history_count})")
            
            audit_count = AuditLog.query.count()
            print(f"✓ AuditLog table accessible (count: {audit_count})")
            
        return True
        
    except Exception as e:
        print(f"✗ Migration test failed: {e}")
        return False


def generate_test_report(results):
    """Generate test report"""
    print("\n" + "="*60)
    print("Test Report Summary")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for r in results.values() if r)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n✅ All tests passed! System is ready for production deployment.")
    else:
        print("\n❌ Some tests failed. Please fix issues before deploying to production.")
    
    return passed_tests == total_tests


def cleanup_test_environment():
    """Clean up test artifacts"""
    print("\nCleaning up test environment...")
    
    # Remove test database
    test_db = project_dir / "test_production.db"
    if test_db.exists():
        test_db.unlink()
        print("✓ Test database removed")
    
    # Clear test cache if using Redis
    if not os.environ.get('USE_MOCK_REDIS'):
        try:
            import redis
            r = redis.Redis.from_url(os.environ.get('REDIS_URL'))
            r.flushdb()
            print("✓ Test Redis database cleared")
        except:
            pass


def main():
    """Main test runner"""
    print("Production Test Suite")
    print("====================")
    
    # Setup
    setup_test_environment()
    check_dependencies()
    
    # Run tests
    results = {}
    
    print("\nRunning test suite...")
    
    # Database migrations
    results['Database Migrations'] = run_database_migrations_test()
    
    # Unit tests
    results['Unit Tests'] = run_unit_tests()
    
    # Load tests
    results['Load Tests'] = run_load_tests()
    
    # Integration tests
    results['Integration Tests'] = run_integration_tests()
    
    # Generate report
    all_passed = generate_test_report(results)
    
    # Cleanup
    cleanup_test_environment()
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()