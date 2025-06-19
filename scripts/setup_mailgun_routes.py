#!/usr/bin/env python3
"""
Mailgun Route Setup Script for Individual Agent Email Addresses
This script creates Mailgun routes for each agent to receive emails
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add project root to path
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

def setup_mailgun_routes():
    """Setup Mailgun routes for all agents"""
    
    # Load environment variables
    mailgun_api_key = os.environ.get('MAILGUN_API_KEY')
    mailgun_domain = os.environ.get('MAILGUN_DOMAIN')
    webhook_url = os.environ.get('SWARM_BASE_URL', 'https://yourdomain.com') + '/api/email-agent/webhooks/mailgun'
    
    if not mailgun_api_key or not mailgun_domain:
        print("❌ Error: MAILGUN_API_KEY and MAILGUN_DOMAIN must be set in your .env file")
        return False
    
    # Load agent configuration
    agents_file = project_dir / 'config' / 'agents.json'
    try:
        with open(agents_file) as f:
            agents_config = json.load(f)
            agents = agents_config['AGENT_PROFILES']
    except Exception as e:
        print(f"❌ Error loading agents.json: {e}")
        return False
    
    print(f"🚀 Setting up Mailgun routes for domain: {mailgun_domain}")
    print(f"📡 Webhook URL: {webhook_url}")
    print()
    
    # Mailgun API endpoint
    api_url = f"https://api.mailgun.net/v3/routes"
    auth = ("api", mailgun_api_key)
    
    success_count = 0
    total_agents = len(agents)
    
    for agent_id, agent_data in agents.items():
        agent_name = agent_data.get('name', agent_id)
        agent_email = agent_data.get('email')
        
        if not agent_email:
            print(f"⚠️  Skipping {agent_name}: No email address configured")
            continue
        
        # Create route data
        route_data = {
            'priority': 10,
            'description': f'{agent_name} Email Route',
            'expression': f'match_recipient("{agent_email}")',
            'action': f'forward("{webhook_url}")'
        }
        
        print(f"📧 Creating route for {agent_name} ({agent_email})...")
        
        try:
            response = requests.post(api_url, auth=auth, data=route_data)
            
            if response.status_code == 200:
                route_info = response.json()
                print(f"   ✅ Route created successfully (ID: {route_info['route']['id']})")
                success_count += 1
            else:
                print(f"   ❌ Failed to create route: {response.status_code} - {response.text}")
                
        except requests.RequestException as e:
            print(f"   ❌ Network error: {e}")
    
    print()
    print(f"📊 Summary: {success_count}/{total_agents} routes created successfully")
    
    if success_count == total_agents:
        print("🎉 All agent email routes configured successfully!")
        print()
        print("📋 Next steps:")
        print("1. Update your .env file with your actual domain name")
        print("2. Deploy your application to make the webhook URL accessible")
        print("3. Test by sending emails to your agents")
        return True
    else:
        print("⚠️  Some routes failed to create. Check the errors above.")
        return False

def list_existing_routes():
    """List existing Mailgun routes"""
    mailgun_api_key = os.environ.get('MAILGUN_API_KEY')
    
    if not mailgun_api_key:
        print("❌ Error: MAILGUN_API_KEY must be set")
        return
    
    api_url = f"https://api.mailgun.net/v3/routes"
    auth = ("api", mailgun_api_key)
    
    try:
        response = requests.get(api_url, auth=auth)
        if response.status_code == 200:
            routes = response.json()
            print(f"📋 Existing routes ({len(routes['items'])}):")
            for route in routes['items']:
                print(f"  - {route['description']}: {route['expression']} → {route['actions']}")
        else:
            print(f"❌ Failed to fetch routes: {response.status_code}")
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")

def delete_agent_routes():
    """Delete all agent email routes (cleanup function)"""
    mailgun_api_key = os.environ.get('MAILGUN_API_KEY')
    
    if not mailgun_api_key:
        print("❌ Error: MAILGUN_API_KEY must be set")
        return
    
    api_url = f"https://api.mailgun.net/v3/routes"
    auth = ("api", mailgun_api_key)
    
    try:
        # Get all routes
        response = requests.get(api_url, auth=auth)
        if response.status_code != 200:
            print(f"❌ Failed to fetch routes: {response.status_code}")
            return
        
        routes = response.json()
        agent_routes = [r for r in routes['items'] if 'Agent Email Route' in r.get('description', '')]
        
        if not agent_routes:
            print("ℹ️  No agent email routes found to delete")
            return
        
        print(f"🗑️  Found {len(agent_routes)} agent routes to delete")
        confirm = input("Are you sure you want to delete all agent email routes? (y/N): ")
        
        if confirm.lower() != 'y':
            print("❌ Cancelled")
            return
        
        for route in agent_routes:
            route_id = route['id']
            description = route['description']
            
            delete_response = requests.delete(f"{api_url}/{route_id}", auth=auth)
            if delete_response.status_code == 200:
                print(f"✅ Deleted: {description}")
            else:
                print(f"❌ Failed to delete {description}: {delete_response.status_code}")
                
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Mailgun Route Management for Agent Emails')
    parser.add_argument('action', choices=['setup', 'list', 'delete'], 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'setup':
        setup_mailgun_routes()
    elif args.action == 'list':
        list_existing_routes()
    elif args.action == 'delete':
        delete_agent_routes()

