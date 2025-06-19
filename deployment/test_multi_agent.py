#!/usr/bin/env python3
"""
Test script for SWARM multi-agent collaboration functionality
Run this after deploying to production to verify everything works
"""

import requests
import json
import time
import sys
import os
import argparse
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

# ANSI color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Configuration - Set via command line args or environment variables
parser = argparse.ArgumentParser(description="Test SWARM multi-agent functionality")
parser.add_argument("--url", help="Base URL for SWARM API")
parser.add_argument("--key", help="API Key for authentication")
parser.add_argument("--timeout", type=int, default=300, help="Max wait time for task completion (seconds)")
parser.add_argument("--export-dir", default="./exports", help="Directory to save exports")
parser.add_argument("--verbose", action="store_true", help="Show detailed output")
args = parser.parse_args()

BASE_URL = args.url or os.environ.get("SWARM_API_URL") or "http://localhost:5006"
API_KEY = args.key or os.environ.get("SWARM_API_KEY") or ""
MAX_WAIT_TIME = args.timeout
EXPORT_DIR = args.export_dir
VERBOSE = args.verbose

# Create export directory if it doesn't exist
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR)

# Test scenarios for multi-agent collaboration
TEST_SCENARIOS = [
    {
        "name": "Code Review Workflow",
        "task": "Review the authentication system for security vulnerabilities",
        "agents": ["coding_01", "bug_01", "general_01"],
        "expected_duration": 60
    },
    {
        "name": "Feature Development",
        "task": "Plan and implement a user dashboard with analytics",
        "agents": ["product_01", "coding_01"],
        "expected_duration": 90
    },
    {
        "name": "Bug Investigation",
        "task": "Investigate and fix memory leak in the chat service",
        "agents": ["bug_01", "coding_01"],
        "expected_duration": 45
    }
]

def log(message: str, color: str = "", bold: bool = False) -> None:
    """Print formatted log messages"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"{BOLD}" if bold else ""
    print(f"[{timestamp}] {prefix}{color}{message}{RESET}")

def make_request(method: str, endpoint: str, data: Optional[Dict] = None, 
                 params: Optional[Dict] = None, timeout: int = 30) -> Tuple[Dict, bool]:
    """Make API request with error handling"""
    url = f"{BASE_URL}{endpoint}"
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        elif method.lower() == "post":
            response = requests.post(url, headers=headers, json=data, timeout=timeout)
        else:
            return {"error": f"Unsupported method: {method}"}, False
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse response
        if response.content:
            return response.json(), True
        return {}, True
        
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                return {"error": error_data.get("error", str(e)), "status_code": e.response.status_code}, False
            except:
                return {"error": str(e), "status_code": e.response.status_code if hasattr(e, 'response') else None}, False
        return {"error": str(e)}, False

def test_agent_listing() -> bool:
    """Test that agents are available"""
    log("Testing agent listing...", BLUE, True)
    
    # Request agent list
    response, success = make_request("GET", "/api/agents/list")
    
    if not success:
        log(f"Failed to get agent list: {response.get('error')}", RED)
        return False
    
    # Validate response structure
    if not response.get("success"):
        log(f"Agent list API returned failure: {response}", RED)
        return False
    
    profiles = response.get("profiles", [])
    if not profiles:
        log("No agents found in response", RED)
        return False
    
    # Check for expected agents
    expected_agents = {"product_01", "coding_01", "bug_01", "general_01"}
    found_agents = set()
    
    for profile in profiles:
        agent_id = profile.get("id", profile.get("agent_id"))
        role = profile.get("role")
        if agent_id in expected_agents:
            found_agents.add(agent_id)
            log(f"✓ Found agent: {agent_id} ({role})", GREEN)
        elif VERBOSE:
            log(f"Additional agent found: {agent_id} ({role})", BLUE)
    
    missing_agents = expected_agents - found_agents
    if missing_agents:
        log(f"Missing expected agents: {', '.join(missing_agents)}", RED)
        return False
    
    log(f"All expected agents found ({len(found_agents)})", GREEN, True)
    return True

def test_single_agent_chat() -> bool:
    """Test individual agent communication"""
    log("Testing single agent chat...", BLUE, True)
    
    # Test with coding agent
    agent_id = "coding_01"
    message = "What's the best way to implement error handling in a REST API?"
    
    log(f"Sending message to {agent_id}...", BLUE)
    
    # Send chat message
    data = {
        "message": message,
        "enhance_prompt": True
    }
    
    response, success = make_request("POST", f"/api/agents/chat/{agent_id}", data)
    
    if not success:
        log(f"Failed to chat with agent {agent_id}: {response.get('error')}", RED)
        return False
    
    # Validate response
    if not response.get("success"):
        log(f"Chat API returned failure: {response}", RED)
        return False
    
    agent_response = response.get("response", "")
    if not agent_response:
        log("Agent returned empty response", RED)
        return False
    
    # Check response length and content
    if len(agent_response) < 50:
        log(f"Agent response suspiciously short: {agent_response}", YELLOW)
    
    if VERBOSE:
        log(f"Agent response: {agent_response[:100]}...", BLUE)
    
    log(f"Successfully received response from {agent_id} ({len(agent_response)} chars)", GREEN)
    
    # Test chat history
    log(f"Testing chat history for {agent_id}...", BLUE)
    
    history_response, history_success = make_request("GET", f"/api/agents/chat_history/{agent_id}")
    
    if not history_success:
        log(f"Failed to get chat history: {history_response.get('error')}", RED)
        return False
    
    if not history_response.get("success"):
        log(f"Chat history API returned failure: {history_response}", RED)
        return False
    
    history = history_response.get("history", [])
    if not history:
        log("Chat history is empty after sending message", RED)
        return False
    
    log(f"Successfully retrieved chat history ({len(history)} messages)", GREEN)
    
    # Clean up - clear history
    clear_response, clear_success = make_request("DELETE", f"/api/agents/chat_history/{agent_id}")
    
    if not clear_success:
        log(f"Warning: Failed to clear chat history: {clear_response.get('error')}", YELLOW)
    
    log("Single agent chat test completed successfully", GREEN, True)
    return True

def test_multi_agent_collaboration() -> bool:
    """Test multi-agent task execution"""
    log("Testing multi-agent collaboration...", BLUE, True)
    
    # Use first test scenario
    scenario = TEST_SCENARIOS[0]
    log(f"Running scenario: {scenario['name']}", BLUE)
    
    # Start collaboration
    data = {
        "task_description": scenario["task"],
        "tagged_agents": scenario["agents"],
        "working_directory": "./",
        "sequential": False,
        "enhance_prompt": True
    }
    
    response, success = make_request("POST", "/api/agents/collaborate", data)
    
    if not success:
        log(f"Failed to start collaboration: {response.get('error')}", RED)
        return False
    
    if not response.get("success"):
        log(f"Collaboration API returned failure: {response}", RED)
        return False
    
    task_id = response.get("task_id")
    if not task_id:
        log("No task_id returned from collaboration API", RED)
        return False
    
    log(f"Collaboration started with task_id: {task_id}", GREEN)
    
    # Poll for task completion
    start_time = time.time()
    completed = False
    status = "unknown"
    progress = 0
    
    log("Waiting for task completion...", BLUE)
    
    while time.time() - start_time < MAX_WAIT_TIME:
        status_response, status_success = make_request(
            "GET", f"/api/agents/conversation/{task_id}"
        )
        
        if not status_success:
            log(f"Failed to get task status: {status_response.get('error')}", RED)
            time.sleep(5)
            continue
        
        status = status_response.get("status", "unknown")
        progress = status_response.get("progress", 0)
        
        if VERBOSE:
            log(f"Task status: {status}, progress: {progress}%", BLUE)
        else:
            # Print progress without newline
            sys.stdout.write(f"\rProgress: {progress}% | Status: {status}" + " " * 20)
            sys.stdout.flush()
        
        if status == "completed":
            completed = True
            break
        
        if status == "failed":
            log(f"Task failed: {status_response.get('error', 'Unknown error')}", RED)
            return False
        
        time.sleep(5)
    
    # Print newline after progress updates
    if not VERBOSE:
        print()
    
    if not completed:
        log(f"Task did not complete within {MAX_WAIT_TIME} seconds", RED)
        return False
    
    elapsed_time = time.time() - start_time
    log(f"Task completed in {elapsed_time:.1f} seconds", GREEN)
    
    # Verify conversations exist
    conversations = status_response.get("conversations", [])
    if not conversations:
        log("No conversations found in completed task", RED)
        return False
    
    agent_count = len(set(msg["agent_id"] for msg in conversations if "agent_id" in msg))
    log(f"Found conversations from {agent_count} agents ({len(conversations)} messages)", GREEN)
    
    if agent_count < len(scenario["agents"]):
        log(f"Warning: Not all agents contributed to the conversation", YELLOW)
    
    log("Multi-agent collaboration test completed successfully", GREEN, True)
    return True

def test_audit_system() -> bool:
    """Test audit trail and export functionality"""
    log("Testing audit system...", BLUE, True)
    
    # First, start a collaboration to generate audit data
    scenario = TEST_SCENARIOS[1]  # Use second scenario
    
    data = {
        "task_description": scenario["task"],
        "tagged_agents": scenario["agents"],
        "working_directory": "./",
        "sequential": False
    }
    
    response, success = make_request("POST", "/api/agents/collaborate", data)
    
    if not success:
        log(f"Failed to start collaboration for audit test: {response.get('error')}", RED)
        return False
    
    task_id = response.get("task_id")
    if not task_id:
        log("No task_id returned from collaboration API", RED)
        return False
    
    log(f"Started task for audit testing: {task_id}", GREEN)
    
    # Wait a bit for audit records to be generated
    log("Waiting for audit records to be generated...", BLUE)
    time.sleep(10)
    
    # Get audit trail
    audit_response, audit_success = make_request(
        "GET", f"/api/audit/task/{task_id}"
    )
    
    if not audit_success:
        log(f"Failed to get audit trail: {audit_response.get('error')}", RED)
        return False
    
    audit_records = audit_response.get("audit_records", [])
    if not audit_records:
        log("No audit records found", YELLOW)
        # Continue anyway as some records might be generated later
    else:
        log(f"Found {len(audit_records)} audit records", GREEN)
    
    # Test CSV export
    log("Testing audit export to CSV...", BLUE)
    
    # Make request with stream=True to get file content
    url = f"{BASE_URL}/api/audit/task/{task_id}/export?format=csv"
    headers = {"X-API-Key": API_KEY}
    
    try:
        export_response = requests.get(url, headers=headers, stream=True)
        export_response.raise_for_status()
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = os.path.join(EXPORT_DIR, f"audit_{task_id}_{timestamp}.csv")
        
        with open(export_path, "wb") as f:
            for chunk in export_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log(f"Exported audit trail to {export_path}", GREEN)
        
        # Check file size
        file_size = os.path.getsize(export_path)
        if file_size == 0:
            log("Warning: Exported file is empty", YELLOW)
        else:
            log(f"Export file size: {file_size} bytes", GREEN)
        
    except requests.exceptions.RequestException as e:
        log(f"Failed to export audit trail: {str(e)}", RED)
        return False
    
    # Test explainability report
    log("Testing explainability report...", BLUE)
    
    explain_response, explain_success = make_request(
        "GET", f"/api/audit/task/{task_id}/explain"
    )
    
    if not explain_success:
        log(f"Failed to get explainability report: {explain_response.get('error')}", YELLOW)
        # Not failing the test as this might be an optional feature
    else:
        log("Successfully retrieved explainability report", GREEN)
        
        # Save to file
        explain_path = os.path.join(EXPORT_DIR, f"explain_{task_id}_{timestamp}.json")
        with open(explain_path, "w") as f:
            json.dump(explain_response, f, indent=2)
        
        log(f"Saved explainability report to {explain_path}", GREEN)
    
    log("Audit system test completed successfully", GREEN, True)
    return True

def run_all_tests() -> None:
    """Run comprehensive test suite"""
    if not API_KEY:
        log("API_KEY not provided. Set via --key argument or SWARM_API_KEY environment variable.", RED, True)
        sys.exit(1)
    
    log(f"Starting SWARM multi-agent test suite", BOLD, True)
    log(f"API URL: {BASE_URL}")
    log(f"Export directory: {EXPORT_DIR}")
    log(f"Timeout: {MAX_WAIT_TIME} seconds")
    print("-" * 60)
    
    # Track test results
    results = {}
    all_passed = True
    
    # Test agent listing
    results["agent_listing"] = test_agent_listing()
    all_passed = all_passed and results["agent_listing"]
    print("-" * 60)
    
    # Test single agent chat
    results["single_agent_chat"] = test_single_agent_chat()
    all_passed = all_passed and results["single_agent_chat"]
    print("-" * 60)
    
    # Test multi-agent collaboration
    results["multi_agent_collaboration"] = test_multi_agent_collaboration()
    all_passed = all_passed and results["multi_agent_collaboration"]
    print("-" * 60)
    
    # Test audit system
    results["audit_system"] = test_audit_system()
    all_passed = all_passed and results["audit_system"]
    print("-" * 60)
    
    # Print summary
    log("Test Suite Summary", BOLD, True)
    for test_name, passed in results.items():
        status = f"{GREEN}PASSED{RESET}" if passed else f"{RED}FAILED{RESET}"
        log(f"{test_name}: {status}")
    
    if all_passed:
        log("✅ All tests passed! SWARM multi-agent system is fully functional.", GREEN, True)
        sys.exit(0)
    else:
        log("❌ Some tests failed. Review the logs above for details.", RED, True)
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
