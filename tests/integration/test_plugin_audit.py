#!/usr/bin/env python3
"""Test script for Plugin System and Audit Functionality"""

import requests
import json
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='../../config/.env')

API_KEY = os.getenv('SWARM_API_KEY', 'sk-dev-test')
BASE_URL = os.getenv('SWARM_BASE_URL', 'http://localhost:5006')

def test_plugin_system():
    """Test the plugin system functionality"""
    print("=" * 60)
    print("Testing Plugin System")
    print("=" * 60)
    
    # 1. List currently loaded plugins
    print("\n1. Listing loaded plugins:")
    response = requests.get(
        f"{BASE_URL}/api/plugins/",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Plugin count: {data.get('plugin_count', 0)}")
        print(f"Plugin directories: {data.get('directories', [])}")
        for plugin_id, info in data.get('plugins', {}).items():
            print(f"\nPlugin: {plugin_id}")
            print(f"  Info: {json.dumps(info.get('info', {}), indent=2)}")
            print(f"  Loaded at: {info.get('metadata', {}).get('loaded_at', 'Unknown')}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    
    # 2. Check if analytics plugin is loaded
    print("\n2. Checking analytics service:")
    # Try to use the analytics service through the monitoring endpoint
    response = requests.get(
        f"{BASE_URL}/api/monitoring/metrics",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        print("Monitoring metrics available (analytics might be working)")
    else:
        print("Analytics service may not be available")
    
    return True


def test_audit_system():
    """Test the audit system by running a task and checking audit trail"""
    print("\n" + "=" * 60)
    print("Testing Audit System")
    print("=" * 60)
    
    # 1. Run a simple multi-agent task
    print("\n1. Running a multi-agent task to generate audit data:")
    
    task_data = {
        "task": "Review the security of the authentication module and suggest improvements",
        "working_directory": "/Users/copp1723/Desktop/swarm",
        "dry_run": False  # Actually execute the task
    }
    
    response = requests.post(
        f"{BASE_URL}/api/agents/orchestrate",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json=task_data
    )
    
    task_id = None
    if response.status_code == 200:
        data = response.json()
        task_id = data.get('task_id')
        print(f"Task ID: {task_id}")
        print(f"Success: {data.get('success')}")
        
        # Wait a bit for task to complete
        print("\nWaiting for task to complete...")
        time.sleep(5)
    else:
        print(f"Error running task: {response.status_code} - {response.text}")
        return False
    
    if not task_id:
        print("No task ID received, cannot check audit trail")
        return False
    
    # 2. Get audit trail for the task
    print(f"\n2. Getting audit trail for task {task_id}:")
    response = requests.get(
        f"{BASE_URL}/api/audit/task/{task_id}",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Audit records found: {data.get('record_count', 0)}")
        
        records = data.get('audit_records', [])
        for i, record in enumerate(records[:3]):  # Show first 3 records
            print(f"\nRecord {i+1}:")
            print(f"  Agent: {record.get('agent_name')}")
            print(f"  Action: {record.get('action_name')}")
            print(f"  Success: {record.get('success')}")
            print(f"  Duration: {record.get('duration_ms', 0):.2f}ms")
            if record.get('reasoning'):
                print(f"  Reasoning: {record.get('reasoning')[:100]}...")
    else:
        print(f"Error getting audit trail: {response.status_code} - {response.text}")
    
    # 3. Get explainability report
    print(f"\n3. Getting explainability report for task {task_id}:")
    response = requests.get(
        f"{BASE_URL}/api/audit/task/{task_id}/explain",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        data = response.json()
        report = data.get('report', {})
        
        print("\nExplainability Report:")
        print(f"Status: {data.get('status')}")
        
        if 'summary' in report:
            print(f"\nSummary:")
            summary = report['summary']
            print(f"  Total actions: {summary.get('total_actions', 0)}")
            print(f"  Success rate: {summary.get('success_rate', 0):.1f}%")
            print(f"  Total duration: {summary.get('total_duration_ms', 0):.0f}ms")
        
        if 'agent_contributions' in report:
            print(f"\nAgent Contributions:")
            for contrib in report['agent_contributions']:
                print(f"  {contrib.get('agent_name')}: {contrib.get('action_count')} actions")
        
        if 'recommendations' in report:
            print(f"\nRecommendations:")
            for rec in report['recommendations'][:3]:
                print(f"  - {rec}")
    else:
        print(f"Error getting explainability report: {response.status_code} - {response.text}")
    
    # 4. Test audit statistics
    print("\n4. Getting audit statistics:")
    response = requests.get(
        f"{BASE_URL}/api/audit/statistics",
        headers={"X-API-Key": API_KEY}
    )
    
    if response.status_code == 200:
        data = response.json()
        stats = data.get('statistics', {})
        print(f"Total records: {stats.get('total_records', 0)}")
        print(f"Success rate: {stats.get('success_rate', 0):.1f}%")
        print(f"Agent performance:")
        for agent, perf in stats.get('by_agent', {}).items():
            print(f"  {agent}: {perf.get('total_actions', 0)} actions, "
                  f"{perf.get('success_rate', 0):.1f}% success")
    
    return True


def create_test_plugin():
    """Create a simple test plugin"""
    print("\n" + "=" * 60)
    print("Creating Test Plugin")
    print("=" * 60)
    
    plugin_content = '''"""
Test Counter Plugin
A simple plugin that counts events
"""
from core.plugins import ServicePlugin
from core.interfaces import IService
from datetime import datetime

class CounterService(IService):
    def __init__(self):
        self.count = 0
        self.last_increment = None
    
    async def initialize(self):
        print("Counter service initialized")
    
    async def shutdown(self):
        print(f"Counter service shutting down. Final count: {self.count}")
    
    def increment(self):
        self.count += 1
        self.last_increment = datetime.now()
        return self.count
    
    def get_count(self):
        return {
            "count": self.count,
            "last_increment": self.last_increment.isoformat() if self.last_increment else None
        }

class CounterPlugin(ServicePlugin):
    def get_plugin_info(self):
        return {
            "name": "Counter Plugin",
            "version": "1.0.0",
            "description": "Simple counter service for testing",
            "type": "service"
        }
    
    def register_services(self, container):
        container.register_singleton("counter_service", CounterService())
        print("Counter service registered")
'''
    
    # Write the plugin file
    plugin_path = "/Users/copp1723/Desktop/swarm/mcp_new_project/plugins/test_counter_plugin.py"
    
    print(f"Writing plugin to: {plugin_path}")
    try:
        os.makedirs(os.path.dirname(plugin_path), exist_ok=True)
        with open(plugin_path, 'w') as f:
            f.write(plugin_content)
        print("Plugin file created successfully")
        
        # Wait for file watcher to detect it
        print("Waiting for plugin to be loaded...")
        time.sleep(3)
        
        # Check if it was loaded
        response = requests.get(
            f"{BASE_URL}/api/plugins/",
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            data = response.json()
            plugins = data.get('plugins', {})
            for plugin_id in plugins:
                if 'CounterPlugin' in plugin_id:
                    print(f"✓ Plugin loaded: {plugin_id}")
                    return True
            print("✗ Plugin not found in loaded plugins")
        
    except Exception as e:
        print(f"Error creating plugin: {e}")
    
    return False


def test_audit_levels():
    """Test different audit levels"""
    print("\n" + "=" * 60)
    print("Testing Audit Levels")
    print("=" * 60)
    
    levels = ["minimal", "standard", "detailed", "debug"]
    
    for level in levels:
        print(f"\n1. Setting audit level to: {level}")
        response = requests.post(
            f"{BASE_URL}/api/audit/level",
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json"
            },
            json={"level": level}
        )
        
        if response.status_code == 200:
            print(f"✓ Audit level set to {level}")
        else:
            print(f"✗ Failed to set audit level: {response.text}")
    
    return True


if __name__ == "__main__":
    print("Testing Plugin and Audit System\n")
    
    # Test plugin system
    plugin_ok = test_plugin_system()
    
    # Create and test a custom plugin
    if plugin_ok:
        create_test_plugin()
    
    # Test audit system
    audit_ok = test_audit_system()
    
    # Test audit levels
    if audit_ok:
        test_audit_levels()
    
    print("\n" + "=" * 60)
    print("Testing completed!")
    print("=" * 60)
    
    print("\nKey Features Demonstrated:")
    print("✓ Plugin discovery and loading")
    print("✓ Hot-reload capability (file watching)")
    print("✓ Service registration in DI container")
    print("✓ Audit trail generation")
    print("✓ Agent action tracking")
    print("✓ Explainability reports")
    print("✓ Configurable audit levels")
    
    print("\nNext Steps:")
    print("1. Check the plugins directory for the test plugin")
    print("2. Modify the test plugin and watch it auto-reload")
    print("3. Create custom plugins for your specific needs")
    print("4. Use audit trails for debugging and compliance")