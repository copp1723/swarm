#!/usr/bin/env python3
"""Comprehensive test suite for SWARM utilities and UI integration"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("SWARM INTEGRATION TEST SUITE")
print("=" * 60)

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "errors": []
}

def test_section(name):
    print(f"\n{name}")
    print("-" * len(name))

def test_case(description, condition, error_msg=""):
    global test_results
    if condition:
        print(f"✓ {description}")
        test_results["passed"] += 1
    else:
        print(f"✗ {description}")
        if error_msg:
            print(f"  Error: {error_msg}")
        test_results["failed"] += 1
        test_results["errors"].append(f"{description}: {error_msg}")

def warning(description):
    global test_results
    print(f"⚠ {description}")
    test_results["warnings"] += 1

# 1. Test Python Module Imports
test_section("1. PYTHON MODULE IMPORTS")

modules_to_test = [
    ("utils.file_io", ["safe_read_json", "safe_write_json", "atomic_write"]),
    ("utils.error_catalog", ["ErrorCodes", "format_error_response"]),
    ("utils.batch_operations", ["BatchProcessor"]),
    ("utils.async_error_handler", ["AsyncRouteHandler"]),
]

for module_name, expected_attrs in modules_to_test:
    try:
        module = __import__(module_name, fromlist=expected_attrs)
        missing_attrs = [attr for attr in expected_attrs if not hasattr(module, attr)]
        test_case(
            f"Import {module_name}",
            len(missing_attrs) == 0,
            f"Missing attributes: {missing_attrs}" if missing_attrs else ""
        )
    except ImportError as e:
        test_case(f"Import {module_name}", False, str(e))

# 2. Test File I/O Operations
test_section("2. FILE I/O OPERATIONS")

from utils.file_io import safe_read_json, safe_write_json, ensure_directory_exists, atomic_write

# Create temp directory for tests
test_dir = tempfile.mkdtemp()
test_file = os.path.join(test_dir, "test.json")
test_data = {"test": "data", "nested": {"key": "value"}}

try:
    # Test directory creation
    sub_dir = os.path.join(test_dir, "sub", "directory")
    test_case(
        "Create nested directories",
        ensure_directory_exists(sub_dir) and os.path.exists(sub_dir)
    )
    
    # Test JSON write
    test_case(
        "Safe JSON write",
        safe_write_json(test_file, test_data)
    )
    
    # Test JSON read
    read_data = safe_read_json(test_file)
    test_case(
        "Safe JSON read",
        read_data == test_data,
        f"Data mismatch: {read_data} != {test_data}" if read_data != test_data else ""
    )
    
    # Test atomic write
    atomic_file = os.path.join(test_dir, "atomic.txt")
    test_case(
        "Atomic write operation",
        atomic_write(atomic_file, "test content") and os.path.exists(atomic_file)
    )
    
    # Test missing file with default
    missing_data = safe_read_json("nonexistent.json", default_value={"default": True})
    test_case(
        "Handle missing file with default",
        missing_data == {"default": True}
    )
    
finally:
    shutil.rmtree(test_dir)

# 3. Test Error Catalog
test_section("3. ERROR CATALOG")

from utils.error_catalog import ErrorCodes, format_error_response, get_status_code, ErrorBuilder

# Test error response formatting
error_response = format_error_response(ErrorCodes.NOT_FOUND, resource="test_agent")
test_case(
    "Format error response",
    error_response["error"]["code"] == ErrorCodes.NOT_FOUND and
    "test_agent" in error_response["error"]["message"]
)

# Test status code mapping
test_case(
    "Error status code mapping",
    get_status_code(ErrorCodes.NOT_FOUND) == 404 and
    get_status_code(ErrorCodes.INTERNAL_ERROR) == 500
)

# Test ErrorBuilder
complex_error = (ErrorBuilder()
    .with_code(ErrorCodes.VALIDATION_ERROR)
    .with_field_error("name", "Required field")
    .build())
test_case(
    "ErrorBuilder with field errors",
    "field_errors" in complex_error["error"]["details"] and
    complex_error["error"]["details"]["field_errors"]["name"] == "Required field"
)

# 4. Test Configuration Files
test_section("4. CONFIGURATION FILES")

config_files = [
    "config/agents.json",
    "config/constants.py",
    "config/workflows.json"
]

for config_file in config_files:
    file_path = os.path.join(os.path.dirname(__file__), config_file)
    test_case(
        f"Config file exists: {config_file}",
        os.path.exists(file_path)
    )
    
    # If JSON, test if it's valid
    if config_file.endswith('.json') and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                json.load(f)
            test_case(f"Valid JSON: {config_file}", True)
        except json.JSONDecodeError as e:
            test_case(f"Valid JSON: {config_file}", False, str(e))

# 5. Test UI Files
test_section("5. UI INTEGRATION FILES")

ui_files = [
    "static/index.html",
    "static/css/ui-enhancements.css",
    "static/js/ui-enhancements/agent-enhancements.js"
]

for ui_file in ui_files:
    file_path = os.path.join(os.path.dirname(__file__), ui_file)
    test_case(
        f"UI file exists: {ui_file}",
        os.path.exists(file_path)
    )

# Check if UI enhancements are included in index.html
index_path = os.path.join(os.path.dirname(__file__), "static/index.html")
if os.path.exists(index_path):
    with open(index_path, 'r') as f:
        index_content = f.read()
    
    test_case(
        "UI CSS included in index.html",
        "ui-enhancements.css" in index_content
    )
    
    test_case(
        "UI JS included in index.html",
        "agent-enhancements.js" in index_content
    )

# 6. Test for Common Issues
test_section("6. COMMON INTEGRATION ISSUES")

# Check for duplicate imports
if os.path.exists(index_path):
    css_count = index_content.count("ui-enhancements.css")
    js_count = index_content.count("agent-enhancements.js")
    
    test_case(
        "No duplicate CSS includes",
        css_count == 1,
        f"Found {css_count} instances" if css_count != 1 else ""
    )
    
    test_case(
        "No duplicate JS includes", 
        js_count == 1,
        f"Found {js_count} instances" if js_count != 1 else ""
    )

# Check for conflicting class names
css_path = os.path.join(os.path.dirname(__file__), "static/css")
if os.path.exists(css_path):
    conflict_classes = ["agent-role-badge", "capability-badge", "system-status-bar"]
    conflicts_found = []
    
    for css_file in Path(css_path).glob("*.css"):
        if css_file.name != "ui-enhancements.css":
            content = css_file.read_text()
            for class_name in conflict_classes:
                if class_name in content:
                    conflicts_found.append(f"{class_name} in {css_file.name}")
    
    test_case(
        "No CSS class conflicts",
        len(conflicts_found) == 0,
        f"Conflicts: {', '.join(conflicts_found)}" if conflicts_found else ""
    )

# 7. Test Dependencies
test_section("7. DEPENDENCIES")

# Check if jsonschema is available
try:
    import jsonschema
    test_case("jsonschema available", True)
except ImportError:
    warning("jsonschema not installed - config validation will be limited")

# Check if yaml is available
try:
    import yaml
    test_case("PyYAML available", True)
except ImportError:
    warning("PyYAML not installed - YAML support will be limited")

# 8. Test Database Models
test_section("8. DATABASE MODELS")

try:
    from models import Agent, ChatHistory, Workflow
    test_case("Import database models", True)
    
    # Check if required attributes exist
    test_case(
        "Agent model has required fields",
        hasattr(Agent, 'id') and hasattr(Agent, 'name') and hasattr(Agent, 'role')
    )
except ImportError as e:
    test_case("Import database models", False, str(e))

# 9. Test API Routes
test_section("9. API ROUTES")

routes_files = [
    "routes/agents.py",
    "routes/chat.py", 
    "routes/workflows.py"
]

for route_file in routes_files:
    file_path = os.path.join(os.path.dirname(__file__), route_file)
    test_case(
        f"Route file exists: {route_file}",
        os.path.exists(file_path)
    )

# 10. Test Services
test_section("10. SERVICES")

services = [
    "services/multi_agent_executor.py",
    "services/prompt_enhancer.py",
    "services/error_handler.py"
]

for service_file in services:
    file_path = os.path.join(os.path.dirname(__file__), service_file)
    test_case(
        f"Service file exists: {service_file}",
        os.path.exists(file_path)
    )

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
print(f"✓ Passed: {test_results['passed']}")
print(f"✗ Failed: {test_results['failed']}")
print(f"⚠ Warnings: {test_results['warnings']}")

if test_results['failed'] > 0:
    print("\nFailed Tests:")
    for error in test_results['errors']:
        print(f"  - {error}")

if test_results['warnings'] > 0:
    print("\nWarnings indicate optional features that may enhance functionality.")

# Overall result
print("\n" + "=" * 60)
if test_results['failed'] == 0:
    print("✅ ALL CRITICAL TESTS PASSED!")
    print("The integration appears to be successful.")
else:
    print("❌ SOME TESTS FAILED")
    print("Please review the errors above and fix any issues.")

# Check for potential runtime issues
print("\n" + "=" * 60)
print("POTENTIAL RUNTIME ISSUES TO CHECK:")
print("=" * 60)
print("1. Ensure Flask app is configured correctly in app.py")
print("2. Verify database is initialized (run migrations if needed)")
print("3. Check that all API endpoints are registered")
print("4. Ensure WebSocket support is enabled for real-time features")
print("5. Verify Redis is running if using Celery for background tasks")
print("6. Check that all required environment variables are set")

print("\nTo run the application:")
print("  ./start_server.sh  (or python app.py)")
print("\nTo test UI enhancements:")
print("  Open browser to: http://localhost:5000/static/test-ui-enhancements.html")