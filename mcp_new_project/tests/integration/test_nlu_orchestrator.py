#!/usr/bin/env python3
"""Test script for NLU and Orchestrator functionality"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../../config/.env')

API_KEY = os.getenv('SWARM_API_KEY', 'sk-dev-test')
BASE_URL = os.getenv('SWARM_BASE_URL', 'http://localhost:5006')

def test_nlu_analysis():
    """Test NLU analysis endpoint"""
    print("=" * 60)
    print("Testing NLU Analysis")
    print("=" * 60)
    
    test_cases = [
        "Fix the bug in the login function that's causing crashes",
        "Implement a new feature for user authentication with OAuth",
        "Review the code in auth.py and provide feedback on security",
        "Write unit tests for the payment processing module",
        "Refactor the database connection pool to improve performance",
        "Document the API endpoints in the user service",
        "Deploy the latest changes to production",
        "Analyze the performance bottlenecks in our application"
    ]
    
    for task in test_cases:
        print(f"\nAnalyzing: '{task}'")
        
        response = requests.post(
            f"{BASE_URL}/api/agents/analyze",
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json"
            },
            json={"task": task}
        )
        
        if response.status_code == 200:
            data = response.json()
            analysis = data.get('analysis', {})
            
            print(f"Intent: {analysis.get('intent', {}).get('primary')} "
                  f"(confidence: {analysis.get('intent', {}).get('confidence'):.2f})")
            
            entities = analysis.get('structured_task', {}).get('entities', {})
            if entities:
                print(f"Entities: {json.dumps(entities, indent=2)}")
            
            recommended = analysis.get('structured_task', {}).get('recommended_agents', [])
            print(f"Recommended agents: {', '.join(recommended)}")
            
            complexity = analysis.get('structured_task', {}).get('context', {}).get('complexity')
            print(f"Complexity: {complexity}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
        
        print("-" * 40)
        time.sleep(0.5)


def test_orchestration():
    """Test orchestration endpoint"""
    print("\n" + "=" * 60)
    print("Testing Task Orchestration")
    print("=" * 60)
    
    # Test with dry run first
    task = "Fix the critical bug in the payment processing that's causing transactions to fail"
    
    print(f"\nTask: '{task}'")
    print("\n1. Dry run (planning only):")
    
    response = requests.post(
        f"{BASE_URL}/api/agents/orchestrate",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "task": task,
            "working_directory": "/Users/copp1723/Desktop/swarm",
            "priority": "high",
            "emergency": True,
            "dry_run": True
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        plan = data.get('plan', {})
        
        print(f"\nTask ID: {plan.get('task_id')}")
        print(f"Priority: {plan.get('priority')}")
        print(f"Estimated duration: {plan.get('estimated_duration')} seconds")
        
        routing = plan.get('routing', {})
        print(f"\nRouting Decision:")
        print(f"  Primary agents: {', '.join(routing.get('primary_agents', []))}")
        print(f"  Workflow type: {routing.get('workflow_type')}")
        print(f"  Confidence: {routing.get('confidence'):.2f}")
        print(f"  Reasoning: {routing.get('reasoning')}")
        
        print(f"\nExecution Steps:")
        for step in plan.get('execution_steps', []):
            print(f"  {step['step_number']}. {step['step']} - "
                  f"Agent: {step['agent']}, Action: {step['action']}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def test_orchestration_execution():
    """Test actual task execution with orchestration"""
    print("\n" + "=" * 60)
    print("Testing Orchestrated Task Execution")
    print("=" * 60)
    
    task = "Create a simple Python function to calculate fibonacci numbers and add unit tests"
    
    print(f"\nTask: '{task}'")
    print("\nExecuting with orchestration...")
    
    response = requests.post(
        f"{BASE_URL}/api/agents/orchestrate",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "task": task,
            "working_directory": "/Users/copp1723/Desktop/swarm",
            "dry_run": False
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"\nSuccess: {data.get('success')}")
        print(f"Task ID: {data.get('task_id')}")
        
        if data.get('orchestration'):
            orch = data['orchestration']
            print(f"\nOrchestration Details:")
            print(f"  Plan ID: {orch.get('plan_id')}")
            print(f"  Workflow: {orch.get('routing_decision', {}).get('workflow_type')}")
            
            timing = orch.get('estimated_vs_actual', {})
            print(f"  Estimated duration: {timing.get('estimated_duration')}s")
            print(f"  Actual duration: {timing.get('actual_duration')}s")
        
        # Show first few conversation entries
        convs = data.get('conversations', [])
        if convs:
            print(f"\nFirst conversation:")
            print(f"  Agent: {convs[0].get('agent')}")
            print(f"  Role: {convs[0].get('role')}")
            print(f"  Message preview: {convs[0].get('content', '')[:200]}...")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def compare_approaches():
    """Compare traditional vs orchestrated approach"""
    print("\n" + "=" * 60)
    print("Comparing Traditional vs Orchestrated Approach")
    print("=" * 60)
    
    task = "Review this code for security vulnerabilities and fix any issues found"
    
    # Traditional approach
    print("\n1. Traditional approach (suggest agents):")
    response = requests.post(
        f"{BASE_URL}/api/agents/suggest",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={"task": task, "include_details": True}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Suggested roles: {', '.join(data.get('suggested_roles', []))}")
        print(f"Reasoning: {data.get('reasoning')}")
    
    # Orchestrated approach
    print("\n2. Orchestrated approach (with NLU):")
    response = requests.post(
        f"{BASE_URL}/api/agents/orchestrate",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={"task": task, "dry_run": True}
    )
    
    if response.status_code == 200:
        data = response.json()
        plan = data.get('plan', {})
        routing = plan.get('routing', {})
        
        print(f"Intent detected: {plan.get('nlu_analysis', {}).get('intent', {}).get('primary')}")
        print(f"Workflow type: {routing.get('workflow_type')}")
        print(f"Primary agents: {', '.join(routing.get('primary_agents', []))}")
        print(f"Reasoning: {routing.get('reasoning')}")
        print(f"Execution steps: {len(plan.get('execution_steps', []))}")


if __name__ == "__main__":
    print("Testing NLU and Orchestrator Integration\n")
    
    # Test NLU analysis
    test_nlu_analysis()
    
    # Test orchestration planning
    test_orchestration()
    
    # Test actual execution
    test_orchestration_execution()
    
    # Compare approaches
    compare_approaches()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)