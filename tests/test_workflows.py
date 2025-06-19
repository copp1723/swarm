#!/usr/bin/env python3
"""
Test script for the Chain-of-Agents workflow templates
"""
import requests
import json
import time

BASE_URL = "http://localhost:5006"

def test_workflow_templates():
    """Test the workflow template functionality"""
    print("Testing Chain-of-Agents Workflow Templates")
    print("=" * 50)
    
    # 1. Get available templates
    print("\n1. Getting available workflow templates...")
    response = requests.get(f"{BASE_URL}/api/workflows/templates")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {len(data['templates'])} templates")
        for template in data['templates']:
            print(f"  - {template['name']}: {template['steps']} steps, {len(template['agents'])} agents")
    else:
        print(f"✗ Failed to get templates: {response.status_code}")
        return
    
    # 2. Get detailed template info
    print("\n2. Getting detailed template information...")
    template_id = "code_review_detailed"
    response = requests.get(f"{BASE_URL}/api/workflows/templates/{template_id}")
    if response.status_code == 200:
        template = response.json()['template']
        print(f"✓ Template: {template['name']}")
        print(f"  Description: {template['description']}")
        print(f"  Steps:")
        for i, step in enumerate(template['steps']):
            print(f"    {i+1}. {step['agent']}: {step['task'][:50]}...")
            if step['dependencies']:
                print(f"       Dependencies: {', '.join(step['dependencies'])}")
    else:
        print(f"✗ Failed to get template details: {response.status_code}")
    
    # 3. Execute a workflow
    print("\n3. Executing workflow...")
    execution_data = {
        "template_id": "code_review_detailed",
        "working_directory": "/Users/copp1723/Desktop/swarm/mcp_new_project",
        "execution_mode": "staged",
        "context": {
            "focus": "Check for code quality and potential issues"
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/api/workflows/execute",
        json=execution_data
    )
    
    if response.status_code == 200:
        data = response.json()
        execution_id = data['execution_id']
        print(f"✓ Workflow started: {execution_id}")
        print(f"  Mode: {data['mode']}")
        print(f"  Task ID: {data.get('task_id', 'N/A')}")
        
        # 4. Poll execution status
        print("\n4. Monitoring execution progress...")
        for i in range(30):  # Poll for up to 30 seconds
            time.sleep(2)
            response = requests.get(f"{BASE_URL}/api/workflows/executions/{execution_id}")
            if response.status_code == 200:
                exec_data = response.json()
                execution = exec_data['execution']
                progress = sum(1 for s in execution['steps'] if s['status'] == 'completed')
                total = len(execution['steps'])
                
                print(f"\r  Progress: {progress}/{total} steps ({execution['status']})", end='', flush=True)
                
                if execution['status'] in ['completed', 'error']:
                    print(f"\n✓ Workflow {execution['status']}")
                    if execution['duration_minutes']:
                        print(f"  Duration: {execution['duration_minutes']} minutes")
                    break
            else:
                print(f"\n✗ Failed to get execution status: {response.status_code}")
                break
    else:
        print(f"✗ Failed to execute workflow: {response.status_code}")
        print(f"  Error: {response.json().get('error', 'Unknown error')}")
    
    print("\n" + "=" * 50)
    print("Workflow template test complete!")

if __name__ == "__main__":
    test_workflow_templates()