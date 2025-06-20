"""
WSGI entry point for production deployment with gunicorn
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app and SocketIO
from app import app, socketio

# For SocketIO support with gunicorn, expose the SocketIO WSGI application
# This ensures WebSocket functionality works properly in production
application = socketio

# Ensure the Flask app is also available for compatibility
flask_app = app

if __name__ == "__main__":
    # Development mode - use SocketIO.run for WebSocket support
    port = int(os.environ.get('PORT', 5006))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

