"""Example usage of the new utility modules"""
import asyncio
from utils import (
    # File I/O
    safe_read_json,
    safe_write_json,
    ensure_directory_exists,
    
    # Async error handling
    handle_async_route_errors,
    AsyncRouteHandler,
    
    # Batch operations
    BatchProcessor,
    
    # Config validation
    validate_config_schema,
    load_and_validate_config,
    
    # Error catalog
    ErrorCodes,
    format_error_response,
    ErrorBuilder
)


def example_file_io():
    """Example of using file I/O utilities"""
    print("=== File I/O Examples ===")
    
    # Ensure directory exists
    ensure_directory_exists("data/configs")
    
    # Write JSON safely
    config = {
        "app_name": "SWARM Agent System",
        "version": "2.0",
        "agents": ["coding_agent", "product_agent", "bug_agent"]
    }
    success = safe_write_json("data/configs/app_config.json", config)
    print(f"Write JSON success: {success}")
    
    # Read JSON safely with default
    loaded_config = safe_read_json("data/configs/app_config.json", default_value={})
    print(f"Loaded config: {loaded_config}")
    
    # Try reading non-existent file
    missing_config = safe_read_json("data/configs/missing.json", default_value={"default": True})
    print(f"Missing file returned default: {missing_config}")


def example_error_catalog():
    """Example of using error catalog"""
    print("\n=== Error Catalog Examples ===")
    
    # Simple error response
    error1 = format_error_response(
        ErrorCodes.NOT_FOUND,
        resource="agent",
        request_id="123-456"
    )
    print(f"Not found error: {error1}")
    
    # Using ErrorBuilder for complex errors
    error2 = (ErrorBuilder()
        .with_code(ErrorCodes.VALIDATION_ERROR)
        .with_field_errors({
            'agent_id': 'Invalid format',
            'message': 'Message too long'
        })
        .with_request_id("789-012")
        .build())
    print(f"Validation error: {error2}")
    
    # Rate limit error
    error3 = format_error_response(
        ErrorCodes.RATE_LIMITED,
        seconds=60
    )
    print(f"Rate limit error: {error3}")


async def example_async_error_handler():
    """Example of using async error handler"""
    print("\n=== Async Error Handler Examples ===")
    
    # Create handler
    handler = AsyncRouteHandler()
    
    # Simulate an async route function
    @handler.handle_async
    async def fetch_agent_data(agent_id: str):
        if agent_id == "invalid":
            raise ValueError("Invalid agent ID")
        return {"agent_id": agent_id, "status": "active"}
    
    # Test successful call
    try:
        result = await fetch_agent_data("coding_agent")
        print(f"Successful call: {result}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test error handling
    try:
        result = await fetch_agent_data("invalid")
        print(f"Should not reach here: {result}")
    except Exception as e:
        print(f"Handled error: {e}")


def example_config_validation():
    """Example of config validation"""
    print("\n=== Config Validation Examples ===")
    
    # Define a schema
    schema = {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "minLength": 1},
            "port": {"type": "integer", "minimum": 1, "maximum": 65535},
            "debug": {"type": "boolean"},
            "agents": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            }
        },
        "required": ["app_name", "port"]
    }
    
    # Valid config
    valid_config = {
        "app_name": "SWARM",
        "port": 8080,
        "debug": True,
        "agents": ["agent1", "agent2"]
    }
    
    is_valid, errors = validate_config_schema(valid_config, schema)
    print(f"Valid config validation: {is_valid}, errors: {errors}")
    
    # Invalid config
    invalid_config = {
        "app_name": "",  # Too short
        "port": 70000,   # Out of range
        "agents": []     # Too few items
    }
    
    is_valid, errors = validate_config_schema(invalid_config, schema)
    print(f"Invalid config validation: {is_valid}")
    print(f"Errors: {errors}")


async def example_batch_operations():
    """Example of batch operations (mock)"""
    print("\n=== Batch Operations Examples ===")
    
    # Create batch processor
    processor = BatchProcessor(batch_size=100)
    
    # Mock data
    items = [f"item_{i}" for i in range(250)]
    
    # Mock processing function
    async def process_item(item):
        # Simulate some async work
        await asyncio.sleep(0.001)
        if "7" in item:  # Simulate some failures
            raise ValueError(f"Lucky 7 failure for {item}")
        return f"processed_{item}"
    
    # Process items
    results = await processor.process_async(
        items,
        process_item,
        max_concurrent=5
    )
    
    print(f"Batch processing results:")
    print(f"  Total: {results['total']}")
    print(f"  Succeeded: {results['succeeded']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Error sample: {results['errors'][:3] if results['errors'] else 'None'}")


async def main():
    """Run all examples"""
    example_file_io()
    example_error_catalog()
    await example_async_error_handler()
    example_config_validation()
    await example_batch_operations()


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())