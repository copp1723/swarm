#!/usr/bin/env python3
"""Start the Flask server"""
import os
import sys
from dotenv import load_dotenv

# Change to the project directory
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)

# Add project directory to Python path
sys.path.insert(0, project_dir)

# Load environment variables
load_dotenv()

# Print configuration
print(f"Working directory: {os.getcwd()}")
print(f"API Key configured: {'Yes' if os.environ.get('OPENROUTER_API_KEY') else 'No'}")
print(f"Starting server on port: {os.environ.get('PORT', 5006)}")

# Import and run the app
from app import app, db

# Create database tables
with app.app_context():
    db.create_all()
    print("Database tables created successfully")

# Run the app
port = int(os.environ.get('PORT', 5006))
print(f"\n🚀 Starting MCP Agent Chat System on http://localhost:{port}")
print("Press Ctrl+C to stop the server\n")

app.run(host='0.0.0.0', port=port, debug=True)