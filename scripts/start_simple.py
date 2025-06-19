#!/usr/bin/env python3
"""
Simplified server start script with better error handling
"""
import os
import sys
import subprocess
from pathlib import Path

# Change to project directory
project_dir = Path(__file__).parent.parent
os.chdir(project_dir)

# Set environment variables
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'
os.environ['PORT'] = '5006'

# Load .env file if exists
env_file = project_dir / 'config' / '.env'
if env_file.exists():
    print("Loading environment from .env file...")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# Initialize database
print("Initializing database...")
try:
    subprocess.run([sys.executable, 'init/init_database.py'], check=True)
    print("✓ Database initialized")
except subprocess.CalledProcessError:
    print("✗ Database initialization failed - continuing anyway")

# Start the server
print(f"\nStarting server on port {os.environ['PORT']}...")
print(f"API Key: {os.environ.get('SWARM_DEV_API_KEY', 'Not set')}")
print("\nServer URLs:")
print(f"  Main Interface: http://localhost:{os.environ['PORT']}/")
print(f"  Debug Interface: http://localhost:{os.environ['PORT']}/chat-debug.html")
print(f"  Health Check: http://localhost:{os.environ['PORT']}/health")
print("\nPress Ctrl+C to stop the server")
print("-" * 50)

# Run the app
try:
    subprocess.run([sys.executable, 'app.py'])
except KeyboardInterrupt:
    print("\nServer stopped")
except Exception as e:
    print(f"Error: {e}")