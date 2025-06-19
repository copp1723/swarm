#!/usr/bin/env python3
"""
Test script for Email Service and Supermemory Integration
Tests the new API endpoints for both services
"""

import requests
import json
import time
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='../config/.env')

# Configuration
BASE_URL = "http://localhost:5006"
API_KEY = os.environ.get('SWARM_DEV_API_KEY', 'your-api-key-here')

# Headers
headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
}


def test_email_service():
    """Test Email Service endpoints"""
    print("\n=== Testing Email Service ===\n")
    
    # 1. Test simple email send
    print("1. Testing simple email send...")
    email_data = {
        "to": "test@example.com",
        "subject": "Test Email from SWARM",
        "body": "This is a test email sent from the SWARM system.",
        "tags": ["test", "api"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/email/send",
        json=email_data,
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Result: {json.dumps(response.json(), indent=2)}")
    
    # 2. Test email draft creation
    print("\n2. Testing email draft creation...")
    draft_data = {
        "to": [{"email": "recipient@example.com", "name": "John Doe"}],
        "subject": "Important Update - Please Review",
        "body": "This is a draft email that requires approval before sending.",
        "html": "<p>This is a <strong>draft email</strong> that requires approval.</p>",
        "tags": ["important", "review"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/email/draft",
        json=draft_data,
        headers=headers
    )
    print(f"Response: {response.status_code}")
    result = response.json()
    print(f"Result: {json.dumps(result, indent=2)}")
    
    draft_id = result.get('draft_id')
    
    # 3. Test getting draft
    if draft_id:
        print(f"\n3. Testing get draft {draft_id}...")
        response = requests.get(
            f"{BASE_URL}/api/email/draft/{draft_id}",
            headers=headers
        )
        print(f"Response: {response.status_code}")
        print(f"Draft: {json.dumps(response.json(), indent=2)}")
        
        # 4. Test draft review (approve)
        print(f"\n4. Testing draft review (approve)...")
        review_data = {
            "action": "approve",
            "reviewer": "admin",
            "comments": "Looks good, approved for sending"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/email/draft/{draft_id}/review",
            json=review_data,
            headers=headers
        )
        print(f"Response: {response.status_code}")
        print(f"Review result: {json.dumps(response.json(), indent=2)}")
    
    # 5. Test email history
    print("\n5. Testing email history...")
    response = requests.get(
        f"{BASE_URL}/api/email/history?limit=5",
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"History: {json.dumps(response.json(), indent=2)}")
    
    # 6. Test email stats
    print("\n6. Testing email stats...")
    response = requests.get(
        f"{BASE_URL}/api/email/stats",
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Stats: {json.dumps(response.json(), indent=2)}")


def test_supermemory_integration():
    """Test Supermemory Integration endpoints"""
    print("\n\n=== Testing Supermemory Integration ===\n")
    
    # Check if Supermemory API key is configured
    if not os.environ.get('SUPERMEMORY_API_KEY'):
        print("WARNING: SUPERMEMORY_API_KEY not configured. Skipping Supermemory tests.")
        return
    
    # 1. Test adding memory
    print("1. Testing add memory...")
    memory_data = {
        "content": "The SWARM system uses a multi-agent architecture with specialized agents for different tasks.",
        "agent_id": "DEVELOPER",
        "conversation_id": "test_conv_123",
        "metadata": {
            "category": "system_architecture",
            "importance": "high"
        },
        "tags": ["architecture", "multi-agent", "swarm"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/memory/add",
        json=memory_data,
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Result: {json.dumps(response.json(), indent=2)}")
    
    # 2. Test searching memories
    print("\n2. Testing memory search...")
    search_data = {
        "query": "multi-agent architecture",
        "agent_id": "DEVELOPER",
        "limit": 5
    }
    
    response = requests.post(
        f"{BASE_URL}/api/memory/search",
        json=search_data,
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Search results: {json.dumps(response.json(), indent=2)}")
    
    # 3. Test getting agent memories
    print("\n3. Testing get agent memories...")
    response = requests.get(
        f"{BASE_URL}/api/memory/agent/DEVELOPER?limit=5",
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Agent memories: {json.dumps(response.json(), indent=2)}")
    
    # 4. Test sharing memory
    print("\n4. Testing memory sharing...")
    share_data = {
        "content": "Best practice: Always use type hints in Python functions for better code clarity.",
        "source_agent": "DEVELOPER",
        "target_agents": ["PRODUCT", "BUG"],
        "metadata": {
            "importance": "high",
            "category": "best_practice"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/memory/share",
        json=share_data,
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Share result: {json.dumps(response.json(), indent=2)}")
    
    # 5. Test agent profile
    print("\n5. Testing agent profile...")
    profile_data = {
        "capabilities": ["code_review", "optimization", "debugging"],
        "preferences": {
            "language": "python",
            "style": "pep8",
            "framework": "flask"
        },
        "knowledge_areas": ["web_development", "api_design", "database_optimization"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/memory/agent/DEVELOPER/profile",
        json=profile_data,
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Profile result: {json.dumps(response.json(), indent=2)}")
    
    # 6. Test memory stats
    print("\n6. Testing memory stats...")
    response = requests.get(
        f"{BASE_URL}/api/memory/stats?agent_id=DEVELOPER",
        headers=headers
    )
    print(f"Response: {response.status_code}")
    print(f"Stats: {json.dumps(response.json(), indent=2)}")


def test_integration():
    """Test integration between services"""
    print("\n\n=== Testing Service Integration ===\n")
    
    # Test email draft with memory context
    print("1. Creating email draft with memory lookup...")
    
    # First search for relevant memories
    search_response = requests.post(
        f"{BASE_URL}/api/memory/search",
        json={"query": "best practices", "limit": 3},
        headers=headers
    )
    
    memories = []
    if search_response.status_code == 200:
        memories = search_response.json().get('memories', [])
    
    # Create email draft incorporating memories
    email_draft = {
        "to": [{"email": "team@example.com", "name": "Development Team"}],
        "subject": "Weekly Best Practices Summary",
        "body": f"Here are this week's best practices from our knowledge base:\n\n" + 
                "\n".join([f"- {m.get('content', '')}" for m in memories[:3]]),
        "tags": ["weekly", "best-practices", "knowledge-sharing"]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/email/draft",
        json=email_draft,
        headers=headers
    )
    print(f"Draft creation response: {response.status_code}")
    print(f"Result: {json.dumps(response.json(), indent=2)}")


def main():
    """Run all tests"""
    print("Starting Email Service and Supermemory Integration Tests")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {API_KEY[:10]}..." if API_KEY else "No API key configured")
    
    # Run tests
    test_email_service()
    test_supermemory_integration()
    test_integration()
    
    print("\n\n=== Tests Complete ===")


if __name__ == "__main__":
    main()