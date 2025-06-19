"""Test the new utility modules"""
import asyncio
import json
import os

# Test File I/O utilities
print("=== Testing File I/O Utilities ===")
from utils.file_io import safe_read_json, safe_write_json, ensure_directory_exists

# Create test directory
ensure_directory_exists("test_data")
print("✓ Created test directory")

# Write JSON
test_data = {"name": "SWARM", "version": "2.0"}
success = safe_write_json("test_data/test.json", test_data)
print(f"✓ Write JSON: {success}")

# Read JSON
loaded = safe_read_json("test_data/test.json", default_value={})
print(f"✓ Read JSON: {loaded}")

# Test missing file
missing = safe_read_json("test_data/missing.json", default_value={"default": True})
print(f"✓ Missing file returned default: {missing}")

# Test Error Catalog
print("\n=== Testing Error Catalog ===")
from utils.error_catalog import ErrorCodes, format_error_response, ErrorBuilder

# Simple error
error1 = format_error_response(ErrorCodes.NOT_FOUND, resource="agent")
print(f"✓ Not found error: {json.dumps(error1, indent=2)}")

# Complex error with builder
error2 = (ErrorBuilder()
    .with_code(ErrorCodes.VALIDATION_ERROR)
    .with_field_errors({
        'agent_id': 'Invalid format',
        'message': 'Too long'
    })
    .build())
print(f"✓ Validation error: {json.dumps(error2, indent=2)}")

# Test Config Validation
print("\n=== Testing Config Validation ===")
from utils.config_validator import validate_config_schema, check_required_env_variables

# Define schema
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "port": {"type": "integer", "minimum": 1, "maximum": 65535}
    },
    "required": ["name", "port"]
}

# Valid config
config = {"name": "SWARM", "port": 8080}
valid, errors = validate_config_schema(config, schema)
print(f"✓ Valid config: {valid}, errors: {errors}")

# Invalid config
bad_config = {"name": "SWARM", "port": 99999}
valid, errors = validate_config_schema(bad_config, schema)
print(f"✓ Invalid config detected: {valid}, errors: {errors}")

# Check env vars
os.environ["TEST_VAR"] = "present"
valid, missing = check_required_env_variables(["TEST_VAR", "MISSING_VAR"])
print(f"✓ Env check: valid={valid}, missing={missing}")

# Test Async Error Handler
print("\n=== Testing Async Error Handler ===")
from utils.async_error_handler import AsyncRouteHandler

async def test_async():
    handler = AsyncRouteHandler()
    
    @handler.handle_async
    async def test_route():
        return {"status": "success"}
    
    try:
        result = await test_route()
        print(f"✓ Async route success: {result}")
    except Exception as e:
        print(f"✗ Async route failed: {e}")

# Run async test
asyncio.run(test_async())

# Cleanup
import shutil
if os.path.exists("test_data"):
    shutil.rmtree("test_data")
    print("\n✓ Cleaned up test data")

print("\n✅ All basic tests completed!")