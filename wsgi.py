"""
WSGI entry point for production deployment with gunicorn
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app
from app import app, socketio

# For SocketIO support with gunicorn
application = socketio

# Fallback to regular Flask app if SocketIO has issues
if __name__ == "__main__":
    # Development mode
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5006)))

