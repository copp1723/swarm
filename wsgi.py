"""
WSGI entry point for the MCP Executive Platform.
This file is used by Gunicorn to serve the application.
"""
import os
from app import app, socketio

# The main application for Gunicorn to run
# Flask-SocketIO wraps the Flask app, so we pass the socketio object
application = socketio

if __name__ == '__main__':
    # This block is for local development and won't be executed by Gunicorn
    port = int(os.environ.get('PORT', 10000))
    # Use the socketio.run() method for development to get WebSocket support
    socketio.run(app, host='0.0.0.0', port=port, debug=True)

