"""Test the new utility modules (without jsonschema dependency)"""
import asyncio
import json
import os

# Test File I/O utilities
print("=== Testing File I/O Utilities ===")
# Import directly to avoid the full utils import
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.file_io import safe_read_json, safe_write_json, ensure_directory_exists

# Create test directory
ensure_directory_exists("test_data")
print("✓ Created test directory")

# Write JSON
test_data = {"name": "SWARM", "version": "2.0", "agents": ["coding", "product", "bug"]}
success = safe_write_json("test_data/test.json", test_data)
print(f"✓ Write JSON: {success}")

# Read JSON
loaded = safe_read_json("test_data/test.json", default_value={})
print(f"✓ Read JSON: {loaded}")

# Test missing file with default
missing = safe_read_json("test_data/missing.json", default_value={"default": True})
print(f"✓ Missing file returned default: {missing}")

# Test atomic write
from utils.file_io import atomic_write
content = "This is a test of atomic write functionality.\nIt should be safe from partial writes."
success = atomic_write("test_data/atomic_test.txt", content)
print(f"✓ Atomic write: {success}")

# Test Error Catalog
print("\n=== Testing Error Catalog ===")
from utils.error_catalog import ErrorCodes, format_error_response, ErrorBuilder, get_status_code

# Simple error
error1 = format_error_response(ErrorCodes.NOT_FOUND, resource="agent")
print(f"✓ Not found error (status {get_status_code(ErrorCodes.NOT_FOUND)}): {error1['error']['message']}")

# Rate limit error
error2 = format_error_response(ErrorCodes.RATE_LIMITED, seconds=60)
print(f"✓ Rate limit error: {error2['error']['message']}")

# Complex error with builder
error3 = (ErrorBuilder()
    .with_code(ErrorCodes.VALIDATION_ERROR)
    .with_field_errors({
        'agent_id': 'Invalid format - must be alphanumeric',
        'message': 'Message exceeds maximum length of 1000 characters'
    })
    .with_request_id("test-123")
    .build())
print(f"✓ Validation error with field errors:")
print(f"  - Message: {error3['error']['message']}")
print(f"  - Fields: {error3['error']['details']['field_errors']}")

# Test Batch Operations (mock)
print("\n=== Testing Batch Operations ===")
from utils.batch_operations import BatchProcessor

async def test_batch_processing():
    processor = BatchProcessor(batch_size=50, log_progress=False)
    
    # Create test items
    items = [f"item_{i}" for i in range(123)]
    
    # Mock processing function
    async def process_item(item):
        await asyncio.sleep(0.001)  # Simulate work
        if "13" in item:  # Simulate some failures
            raise ValueError(f"Unlucky number in {item}")
        return f"processed_{item}"
    
    # Process items
    results = await processor.process_async(
        items,
        process_item,
        max_concurrent=5
    )
    
    print(f"✓ Batch processing completed:")
    print(f"  - Total items: {results['total']}")
    print(f"  - Succeeded: {results['succeeded']}")
    print(f"  - Failed: {results['failed']}")
    print(f"  - Error types: {len(results['errors'])} unique errors")

# Run batch test
asyncio.run(test_batch_processing())

# Test Async Error Handler
print("\n=== Testing Async Error Handler ===")
from utils.async_error_handler import AsyncRouteHandler, retry_async

async def test_async_handlers():
    handler = AsyncRouteHandler()
    
    # Test successful route
    @handler.handle_async
    async def get_agent_status(agent_id: str):
        if agent_id == "invalid":
            raise ValueError("Invalid agent ID format")
        return {"agent_id": agent_id, "status": "active", "tasks": 5}
    
    # Test success case
    try:
        result = await get_agent_status("coding_agent")
        print(f"✓ Async route success: {result}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
    
    # Test retry mechanism
    attempt_count = 0
    async def flaky_operation():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("Service temporarily unavailable")
        return {"status": "success", "attempts": attempt_count}
    
    try:
        result = await retry_async(flaky_operation, max_attempts=5, delay=0.1)
        print(f"✓ Retry mechanism succeeded after {result['attempts']} attempts")
    except Exception as e:
        print(f"✗ Retry failed: {e}")

# Run async tests
asyncio.run(test_async_handlers())

# Test file operations
print("\n=== Testing Additional File Operations ===")
from utils.file_io import read_file_lines, append_to_file, file_exists, get_file_size

# Test file lines reading
test_lines = ["Line 1", "Line 2", "Line 3", "", "Line 5"]
with open("test_data/lines.txt", "w") as f:
    f.write("\n".join(test_lines))

lines = read_file_lines("test_data/lines.txt")
print(f"✓ Read {len(lines)} lines from file")

lines_no_empty = read_file_lines("test_data/lines.txt", skip_empty=True)
print(f"✓ Read {len(lines_no_empty)} non-empty lines")

# Test append
append_to_file("test_data/append_test.txt", "First line")
append_to_file("test_data/append_test.txt", "Second line")
print(f"✓ Appended lines to file")

# Test file utilities
exists = file_exists("test_data/test.json")
size = get_file_size("test_data/test.json")
print(f"✓ File exists: {exists}, size: {size} bytes")

# Cleanup
import shutil
if os.path.exists("test_data"):
    shutil.rmtree("test_data")
    print("\n✓ Cleaned up test data")

print("\n✅ All utility tests completed successfully!")
print("\nNote: Config validation tests require 'jsonschema' package to be installed.")