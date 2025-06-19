#!/bin/bash

echo "Reinstalling all dependencies for MCP Agent Project..."
echo "=================================================="

# Upgrade pip first
echo "1. Upgrading pip..."
pip install --upgrade pip

# Install all requirements
echo -e "\n2. Installing requirements.txt..."
pip install -r requirements.txt

# Check for any missing Flask packages specifically
echo -e "\n3. Ensuring Flask and extensions are installed..."
pip install flask==3.0.0 flask-sqlalchemy==3.1.1 flask-cors==4.0.0 flask-socketio==5.3.6

# Install any additional packages that might be needed
echo -e "\n4. Installing additional packages..."
pip install python-socketio[client]==5.11.0

# Verify key packages
echo -e "\n5. Verifying installation..."
echo "Checking key packages:"
pip show flask | grep -E "(Name|Version)" || echo "Flask NOT installed!"
pip show celery | grep -E "(Name|Version)" || echo "Celery NOT installed!"
pip show marshmallow | grep -E "(Name|Version)" || echo "Marshmallow NOT installed!"
pip show flask-socketio | grep -E "(Name|Version)" || echo "Flask-SocketIO NOT installed!"
pip show loguru | grep -E "(Name|Version)" || echo "Loguru NOT installed!"

echo -e "\nDependency installation complete!"
echo "You can now start the server with: python app.py"