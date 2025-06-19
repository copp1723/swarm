#!/usr/bin/env python3
"""
Test script for Supermemory integration
"""

import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(dotenv_path='../config/.env')

from services.supermemory_service import get_supermemory_service, Memory
from datetime import datetime

async def test_supermemory():
    """Test Supermemory API integration"""
    print("Testing Supermemory Integration")
    print("=" * 50)
    
    try:
        # Initialize service
        print("\n1. Initializing Supermemory service...")
        memory_service = get_supermemory_service()
        print("✓ Service initialized")
        
        # Test 1: Add a memory
        print("\n2. Adding a test memory...")
        test_memory = Memory(
            content="This is a test memory from the MCP Multi-Agent System. The system is working correctly.",
            metadata={
                "type": "test",
                "test_run": datetime.now().isoformat(),
                "agent": "test_agent"
            },
            agent_id="test_agent",
            conversation_id="test_conversation_001",  # Add conversation ID
            timestamp=datetime.now().isoformat(),
            tags=["test", "integration"]
        )
        
        result = await memory_service.add_memory(test_memory)
        if 'error' not in result:
            print(f"✓ Memory added successfully: {result.get('id', 'Unknown ID')}")
        else:
            print(f"✗ Failed to add memory: {result['error']}")
            return
        
        # Test 2: Search for memories
        print("\n3. Searching for memories...")
        search_results = await memory_service.search_memories(
            query="test memory MCP Multi-Agent",
            agent_id="test_agent",
            limit=5
        )
        
        if search_results:
            print(f"✓ Found {len(search_results)} memories")
            for i, memory in enumerate(search_results, 1):
                print(f"  {i}. Score: {memory.get('score', 0):.2f} - {memory.get('content', '')[:50]}...")
        else:
            print("✗ No memories found")
        
        # Test 3: Get agent memories
        print("\n4. Getting all memories for test_agent...")
        agent_memories = await memory_service.get_agent_memories("test_agent", limit=10)
        
        if agent_memories:
            print(f"✓ Found {len(agent_memories)} memories for test_agent")
        else:
            print("✗ No memories found for test_agent")
        
        # Test 4: Share memory
        print("\n5. Testing memory sharing...")
        share_result = await memory_service.share_memory_across_agents(
            content="Shared knowledge: The system integration test was successful",
            source_agent="test_agent",
            target_agents=["coder_01", "product_01"],
            metadata={"shared_at": datetime.now().isoformat()}
        )
        
        if 'error' not in share_result:
            print("✓ Memory shared successfully")
        else:
            print(f"✗ Failed to share memory: {share_result['error']}")
        
        # Test 5: Get shared knowledge
        print("\n6. Getting shared knowledge...")
        shared = await memory_service.get_shared_knowledge(limit=5)
        
        if shared:
            print(f"✓ Found {len(shared)} shared knowledge items")
        else:
            print("✗ No shared knowledge found")
        
        print("\n✅ All tests completed successfully!")
        print("\nSupermemory is ready to use with your agents!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the service
        await memory_service.close()

if __name__ == "__main__":
    asyncio.run(test_supermemory())