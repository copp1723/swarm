#!/usr/bin/env python3
"""
Multi-Agent Collaboration Test Script
Tests real collaboration between multiple agents using OpenRouter API
"""

import requests
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration
API_BASE_URL = "http://localhost:5006"
COLLABORATION_ENDPOINT = f"{API_BASE_URL}/api/agents/collaborate"
CONVERSATION_ENDPOINT = f"{API_BASE_URL}/api/agents/conversation"
TASK_DESCRIPTION = "Design and implement a secure user authentication system for a web application. Include password requirements, MFA options, and session management best practices."
AGENTS = ["product_01", "coding_01", "bug_01"]
POLL_INTERVAL = 3  # seconds
MAX_WAIT_TIME = 300  # seconds (5 minutes)

# ANSI color codes for prettier output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Track seen messages to avoid duplicates
seen_messages = set()

def print_header(title: str) -> None:
    """Print a formatted header"""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

def print_step(step: str) -> None:
    """Print a step in the process"""
    print(f"{BOLD}{YELLOW}➤ {step}{RESET}")

def print_agent_message(agent: str, message: str) -> None:
    """Print an agent message with appropriate formatting"""
    agent_colors = {
        "product_01": MAGENTA,
        "coding_01": BLUE,
        "bug_01": RED,
        "executive_summary": GREEN,
    }
    color = agent_colors.get(agent, CYAN)
    
    # Format the agent name
    agent_name = agent.replace("_01", "").title()
    if agent == "executive_summary":
        agent_name = "Executive Summary"
    
    # Print the message with timestamp
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n{BOLD}[{timestamp}] {color}{agent_name} Agent:{RESET}")
    print(f"{color}{message.strip()}{RESET}")
    print(f"{BOLD}{'-' * 40}{RESET}")

def start_collaboration() -> Optional[str]:
    """Start a multi-agent collaboration task and return the task ID"""
    print_step("Starting multi-agent collaboration task...")
    
    payload = {
        "task_description": TASK_DESCRIPTION,
        "tagged_agents": AGENTS,
        "working_directory": "./",
        "sequential": True,  # Process agents sequentially for clearer demonstration
        "enhance_prompt": True
    }
    
    try:
        response = requests.post(
            COLLABORATION_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            task_id = data.get("task_id")
            print(f"{GREEN}✓ Collaboration started successfully!{RESET}")
            print(f"{GREEN}✓ Task ID: {task_id}{RESET}")
            return task_id
        else:
            print(f"{RED}✗ Failed to start collaboration: {data.get('error', 'Unknown error')}{RESET}")
            return None
            
    except requests.RequestException as e:
        print(f"{RED}✗ Request error: {str(e)}{RESET}")
        return None

def poll_conversation(task_id: str) -> bool:
    """Poll the conversation endpoint until the task completes or fails"""
    print_step("Polling for updates...")
    
    start_time = time.time()
    last_progress = -1
    completed = False
    
    while time.time() - start_time < MAX_WAIT_TIME:
        try:
            response = requests.get(f"{CONVERSATION_ENDPOINT}/{task_id}")
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                print(f"{RED}✗ Error: {data.get('error', 'Unknown error')}{RESET}")
                return False
                
            status = data.get("status")
            progress = data.get("progress", 0)
            conversations = data.get("conversations", [])
            
            # Update progress bar if changed
            if progress != last_progress:
                progress_bar = f"[{'#' * (progress // 5)}{' ' * (20 - progress // 5)}]"
                print(f"\r{BLUE}Progress: {progress_bar} {progress}%{RESET}", end="", flush=True)
                last_progress = progress
                
            # Display new messages
            display_new_messages(conversations)
            
            # Check if the task is complete
            if status == "completed":
                print(f"\n{GREEN}✓ Task completed successfully!{RESET}")
                completed = True
                break
                
            if status == "error":
                print(f"\n{RED}✗ Task failed: {data.get('error', 'Unknown error')}{RESET}")
                return False
                
            # Wait before polling again
            time.sleep(POLL_INTERVAL)
            
        except requests.RequestException as e:
            print(f"\n{RED}✗ Request error while polling: {str(e)}{RESET}")
            return False
            
    if not completed:
        print(f"\n{YELLOW}⚠ Timed out after {MAX_WAIT_TIME} seconds{RESET}")
        return False
        
    return True

def display_new_messages(conversations: List[Dict[str, Any]]) -> None:
    """Display new messages from the conversation"""
    for message in conversations:
        # Create a unique identifier for this message
        message_id = f"{message.get('agent_id')}:{message.get('timestamp')}"
        
        # Skip if we've seen this message before
        if message_id in seen_messages:
            continue
            
        # Add to seen messages
        seen_messages.add(message_id)
        
        # Print the message
        agent_id = message.get("agent_id")
        content = message.get("content", "")
        
        # Verify this is a real AI response, not a stub
        if "stub" in content.lower() or "(This is a stub response" in content:
            print(f"\n{RED}✗ STUB RESPONSE DETECTED! Not using real AI.{RESET}")
            print(f"{RED}Message: {content}{RESET}")
            print(f"{RED}Please check your OpenRouter API key and configuration.{RESET}")
        else:
            print_agent_message(agent_id, content)
            
            # For executive summary, print a special notice
            if agent_id == "executive_summary":
                print(f"\n{GREEN}✓ Received executive summary - collaboration complete!{RESET}")

def verify_real_responses(conversations: List[Dict[str, Any]]) -> bool:
    """Verify that responses are from real AI, not stubs"""
    for message in conversations:
        content = message.get("content", "").lower()
        if "stub" in content or "(this is a stub response" in content:
            return False
    return True

def main():
    """Main execution flow"""
    print_header("SWARM Multi-Agent Collaboration Test")
    print(f"Task: {BOLD}{TASK_DESCRIPTION}{RESET}")
    print(f"Agents: {', '.join(agent.replace('_01', '').title() for agent in AGENTS)}")
    
    # Start collaboration
    task_id = start_collaboration()
    if not task_id:
        sys.exit(1)
        
    # Poll for updates
    success = poll_conversation(task_id)
    
    if success:
        # Get final conversation to verify real responses
        try:
            response = requests.get(f"{CONVERSATION_ENDPOINT}/{task_id}")
            data = response.json()
            conversations = data.get("conversations", [])
            
            if verify_real_responses(conversations):
                print(f"\n{GREEN}✓ VERIFICATION PASSED: All responses are from real AI models{RESET}")
            else:
                print(f"\n{RED}✗ VERIFICATION FAILED: Stub responses detected{RESET}")
                
        except requests.RequestException as e:
            print(f"\n{RED}✗ Error verifying responses: {str(e)}{RESET}")
    
    print_header("Test Complete")

if __name__ == "__main__":
    main()
