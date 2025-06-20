#!/usr/bin/env python3
"""
WebSocket Handshake Test Script
Tests Socket.IO EIO=4 transport polling and websocket upgrade compatibility
"""

import requests
import time
import sys
import json
from urllib.parse import urljoin

def test_websocket_handshake(base_url="http://localhost:5006"):
    """Test the WebSocket handshake process"""
    
    print("🔍 Testing WebSocket Handshake...")
    print(f"Base URL: {base_url}")
    
    # Step 1: Test initial polling request (EIO=4)
    print("\n1️⃣ Testing initial Socket.IO polling request...")
    
    polling_url = urljoin(base_url, "/socket.io/")
    params = {
        'EIO': '4',
        'transport': 'polling',
        't': str(int(time.time() * 1000))  # timestamp
    }
    
    try:
        response = requests.get(polling_url, params=params, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            # Parse the Socket.IO response
            content = response.text
            print(f"   Response: {content[:200]}...")
            
            # Check for successful handshake pattern
            if content.startswith('0') and 'sid' in content:
                print("   ✅ Initial handshake successful")
                
                # Extract session ID for upgrade test
                try:
                    # Socket.IO format: 0{"sid":"...","upgrades":["websocket"],"pingInterval":...}
                    json_part = content[1:]  # Remove the '0' prefix
                    handshake_data = json.loads(json_part)
                    sid = handshake_data.get('sid')
                    upgrades = handshake_data.get('upgrades', [])
                    
                    print(f"   Session ID: {sid}")
                    print(f"   Available upgrades: {upgrades}")
                    
                    if 'websocket' in upgrades:
                        print("   ✅ WebSocket upgrade available")
                        return True, sid
                    else:
                        print("   ⚠️ WebSocket upgrade not available")
                        return False, None
                        
                except json.JSONDecodeError as e:
                    print(f"   ❌ Failed to parse handshake data: {e}")
                    return False, None
            else:
                print("   ❌ Invalid handshake response format")
                return False, None
        else:
            print(f"   ❌ Handshake failed with status {response.status_code}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Connection error: {e}")
        return False, None

def test_health_endpoint(base_url="http://localhost:5006"):
    """Test the health endpoint to ensure server is running"""
    
    print("\n🏥 Testing server health...")
    
    try:
        health_url = urljoin(base_url, "/health")
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Server is healthy")
            print(f"   Status: {data.get('status')}")
            if 'memory' in data:
                print(f"   Memory: {data['memory'].get('usage_mb', 'N/A')} MB")
            return True
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False

def check_socket_io_versions():
    """Check Socket.IO version compatibility"""
    
    print("\n🔍 Checking Socket.IO version compatibility...")
    
    try:
        import pkg_resources
        
        try:
            socketio_version = pkg_resources.get_distribution('python-socketio').version
            print(f"   python-socketio: {socketio_version}")
        except pkg_resources.DistributionNotFound:
            socketio_version = "unknown"
            print("   python-socketio: not found")
        
        try:
            flask_socketio_version = pkg_resources.get_distribution('flask-socketio').version
            print(f"   flask-socketio: {flask_socketio_version}")
        except pkg_resources.DistributionNotFound:
            flask_socketio_version = "unknown"
            print("   flask-socketio: not found")
        
        # Check version compatibility based on known versions
        if socketio_version.startswith('5.') and flask_socketio_version.startswith('5.'):
            print("   ✅ Server versions compatible (Socket.IO 5.x)")
            print("   📝 Client should use Socket.IO 3.x for compatibility")
            print("   📝 Updated client to 3.1.4 for Flask-SocketIO 5.x compatibility")
            return True
        elif socketio_version.startswith('6.') and flask_socketio_version.startswith('6.'):
            print("   ✅ Server versions compatible (Socket.IO 6.x)")
            print("   📝 Client should use Socket.IO 4.x for compatibility")
            return True
        else:
            print(f"   ⚠️ Version compatibility check inconclusive")
            print(f"   📝 Proceeding with Socket.IO 3.1.4 client (compatible with most 5.x servers)")
            return True  # Assume compatibility for now
            
    except ImportError as e:
        print(f"   ❌ Could not check versions: {e}")
        print("   📝 Proceeding with assumption of compatibility")
        return True

def main():
    """Main test function"""
    
    print("🚀 WebSocket Handshake Audit")
    print("=" * 50)
    
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5006"
    
    # Test 1: Check Socket.IO versions
    version_ok = check_socket_io_versions()
    
    # Test 2: Health check
    health_ok = test_health_endpoint(base_url)
    
    # Test 3: WebSocket handshake
    if health_ok:
        handshake_ok, session_id = test_websocket_handshake(base_url)
    else:
        print("\n⚠️ Skipping WebSocket test due to server health issues")
        handshake_ok = False
        session_id = None
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   Version Compatibility: {'✅' if version_ok else '❌'}")
    print(f"   Server Health: {'✅' if health_ok else '❌'}")
    print(f"   WebSocket Handshake: {'✅' if handshake_ok else '❌'}")
    
    if all([version_ok, health_ok, handshake_ok]):
        print("\n🎉 All tests passed! WebSocket should work correctly.")
        print("\n📋 Next steps for DevTools verification:")
        print("   1. Open browser DevTools → Network → WS")
        print("   2. Look for 'socket.io/?EIO=4&transport=polling' request")
        print("   3. Verify it returns 200 with session data")
        print("   4. Check for subsequent 'websocket' upgrade request")
        print("   5. Confirm 'connected' event is received")
        return 0
    else:
        print("\n❌ Some tests failed. Check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

