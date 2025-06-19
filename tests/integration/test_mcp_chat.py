#!/usr/bin/env python3
"""Test script to verify MCP tool integration with chat agents"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../../config/.env')

API_KEY = os.getenv('SWARM_API_KEY', 'sk-dev-test')
BASE_URL = os.getenv('SWARM_BASE_URL', 'http://localhost:5006')

def test_bug_agent_with_directory():
    """Test if Bug Agent can access filesystem through MCP tools"""
    
    print("Testing Bug Agent with filesystem access...")
    
    # Test message that should trigger filesystem context
    message = "Can you list the files in the swarm folder on the desktop?"
    
    response = requests.post(
        f"{BASE_URL}/api/agents/chat/bug_01",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "message": message,
            "enhance_prompt": True
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nSuccess: {data.get('success')}")
        print(f"\nAgent Response:\n{data.get('response')}")
        print(f"\nEnhanced: {data.get('enhanced')}")
        if data.get('original_message'):
            print(f"\nOriginal Message: {data.get('original_message')}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def check_mcp_server_status():
    """Check if MCP servers are running"""
    
    print("Checking MCP server status...")
    
    response = requests.get(
        f"{BASE_URL}/api/mcp/servers",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        data = response.json()
        servers = data.get('data', {}).get('servers', {})
        print(f"\nTotal servers: {servers.get('total', 0)}")
        print(f"Running servers: {servers.get('running', 0)}")
        
        for server_id, server_info in servers.get('servers', {}).items():
            print(f"\n{server_id}:")
            print(f"  Status: {server_info.get('status')}")
            print(f"  Tools: {server_info.get('tools')}")
            print(f"  Tool names: {', '.join(server_info.get('tool_names', []))}")
    else:
        print(f"Error checking MCP servers: {response.status_code}")

if __name__ == "__main__":
    # First check MCP server status
    check_mcp_server_status()
    
    print("\n" + "="*50 + "\n")
    
    # Then test Bug Agent
    test_bug_agent_with_directory()