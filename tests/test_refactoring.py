#!/usr/bin/env python3
"""
Test script to verify the refactored frontend is working correctly
"""

import requests
import json
import time

BASE_URL = "http://localhost:5006"

def test_static_files():
    """Test that static files are being served correctly"""
    print("Testing static file serving...")
    
    files_to_test = [
        "/",
        "/css/main.css",
        "/css/chat.css", 
        "/css/components.css",
        "/js/app.js",
        "/js/agents/agent-config.js",
        "/js/services/api.js"
    ]
    
    for file_path in files_to_test:
        try:
            response = requests.get(f"{BASE_URL}{file_path}")
            if response.status_code == 200:
                print(f"✅ {file_path} - OK")
            else:
                print(f"❌ {file_path} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {file_path} - Error: {str(e)}")

def test_api_endpoints():
    """Test that API endpoints are working"""
    print("\nTesting API endpoints...")
    
    endpoints = [
        ("/health", "GET"),
        ("/api/agents", "GET"),
        ("/api/agents/workflows", "GET"),
        ("/api/templates", "GET")
    ]
    
    for endpoint, method in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            
            if response.status_code in [200, 201]:
                print(f"✅ {method} {endpoint} - OK")
            else:
                print(f"❌ {method} {endpoint} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {method} {endpoint} - Error: {str(e)}")

def test_websocket_connection():
    """Test WebSocket connectivity"""
    print("\nTesting WebSocket connection...")
    try:
        import socketio
        sio = socketio.Client()
        
        @sio.event
        def connect():
            print("✅ WebSocket connected")
            sio.disconnect()
        
        @sio.event
        def connect_error(data):
            print(f"❌ WebSocket connection error: {data}")
        
        sio.connect(BASE_URL)
        time.sleep(1)
    except Exception as e:
        print(f"❌ WebSocket test failed: {str(e)}")

if __name__ == "__main__":
    print("=" * 50)
    print("Frontend Refactoring Test Suite")
    print("=" * 50)
    
    test_static_files()
    test_api_endpoints()
    test_websocket_connection()
    
    print("\n" + "=" * 50)
    print("Test suite completed!")
    print("=" * 50)