#!/usr/bin/env python3
"""
Test script to validate service discovery and dependency injection robustness improvements
"""

import sys
import os
import time
from contextlib import contextmanager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_config import get_logger

logger = get_logger(__name__)

@contextmanager
def test_context(test_name):
    """Context manager for test execution"""
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {test_name}")
    print(f"{'='*60}")
    start_time = time.time()
    
    try:
        yield
        duration = time.time() - start_time
        print(f"✅ PASSED: {test_name} ({duration:.2f}s)")
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ FAILED: {test_name} ({duration:.2f}s)")
        print(f"   Error: {e}")
        raise

def test_service_container_initialization():
    """Test that the service container initializes properly"""
    with test_context("Service Container Initialization"):
        from core.service_registry import initialize_services
        container = initialize_services()
        
        assert container is not None, "Service container should not be None"
        assert hasattr(container, '_services'), "Container should have _services attribute"
        assert hasattr(container, '_singletons'), "Container should have _singletons attribute"
        
        print(f"   ✓ Container initialized with {len(container._services)} services")

def test_critical_service_validation():
    """Test critical service validation"""
    with test_context("Critical Service Validation"):
        from core.service_registry import validate_critical_services
        
        critical_status = validate_critical_services()
        
        assert isinstance(critical_status, dict), "Should return a dictionary"
        assert len(critical_status) > 0, "Should validate at least one service"
        
        # Log status of each service
        for service_name, status in critical_status.items():
            status_icon = "✓" if status else "✗"
            print(f"   {status_icon} {service_name}: {'Available' if status else 'Missing'}")
        
        # At least some services should be available
        available_count = sum(1 for status in critical_status.values() if status)
        print(f"   📊 {available_count}/{len(critical_status)} critical services available")

def test_service_availability_checking():
    """Test service availability with fallbacks"""
    with test_context("Service Availability Checking"):
        from core.service_registry import ensure_service_available, get_service
        
        # Test getting existing service
        existing_service = get_service('config_manager')
        if existing_service:
            print("   ✓ Found existing service: config_manager")
        else:
            print("   ⚠ config_manager not available")
        
        # Test fallback creation
        def dummy_fallback():
            return {"type": "fallback_service", "status": "created"}
        
        fallback_service = ensure_service_available('test_fallback_service', dummy_fallback)
        assert fallback_service is not None, "Fallback service should be created"
        assert fallback_service.get('type') == 'fallback_service', "Should be the fallback service"
        print("   ✓ Fallback service creation working")

def test_service_status_reporting():
    """Test service status reporting"""
    with test_context("Service Status Reporting"):
        from core.service_registry import get_service_status
        
        status = get_service_status()
        
        assert isinstance(status, dict), "Should return a dictionary"
        assert 'total_registered' in status, "Should include total registered count"
        assert 'services' in status, "Should include services detail"
        
        print(f"   📊 Total registered services: {status['total_registered']}")
        print(f"   📊 Active singletons: {status['singletons_active']}")
        
        # Check if any services failed
        failed_services = []
        for service_name, info in status.get('services', {}).items():
            if not info.get('available', False):
                failed_services.append(service_name)
        
        if failed_services:
            print(f"   ⚠ Failed services: {', '.join(failed_services)}")
        else:
            print("   ✓ All registered services are available")

def test_dependency_injection_container():
    """Test dependency injection container robustness"""
    with test_context("Dependency Injection Container"):
        from core.dependency_injection import get_container, Scope
        
        container = get_container()
        
        # Test service registration
        container.register('test_service', lambda: {'test': True}, scope=Scope.SINGLETON)
        
        # Test service retrieval
        service1 = container.get_service('test_service')
        service2 = container.get_service('test_service')
        
        assert service1 is not None, "Should return service instance"
        assert service1 is service2, "Should return same singleton instance"
        assert service1.get('test') is True, "Should have correct data"
        
        print("   ✓ Service registration and retrieval working")
        print("   ✓ Singleton behavior verified")
        
        # Test missing service handling
        missing_service = container.get_service('non_existent_service')
        assert missing_service is None, "Should return None for missing service"
        print("   ✓ Missing service handling working")

def test_error_handling_robustness():
    """Test error handling in service operations"""
    with test_context("Error Handling Robustness"):
        from core.service_registry import get_service, get_required_service
        
        # Test graceful handling of missing services
        missing_service = get_service('definitely_does_not_exist')
        assert missing_service is None, "Should return None gracefully"
        print("   ✓ Graceful handling of missing services")
        
        # Test required service error handling
        try:
            get_required_service('definitely_does_not_exist')
            assert False, "Should raise exception for missing required service"
        except RuntimeError as e:
            assert 'unavailable' in str(e).lower(), "Should have meaningful error message"
            print("   ✓ Required service error handling working")

def run_all_tests():
    """Run all service robustness tests"""
    print("🚀 Starting Service Robustness Test Suite")
    print("=" * 80)
    
    tests = [
        test_service_container_initialization,
        test_critical_service_validation,
        test_service_availability_checking,
        test_service_status_reporting,
        test_dependency_injection_container,
        test_error_handling_robustness
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            logger.error(f"Test {test_func.__name__} failed: {e}")
    
    print(f"\n{'='*80}")
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Service robustness improvements are working.")
        return True
    else:
        print(f"⚠️  {failed} test(s) failed. Check the logs for details.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

