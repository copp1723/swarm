"""
WSGI entry point for production deployment with gunicorn
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app and SocketIO
from app import app, socketio

# Initialize application services first
try:
    from app import initialize_application_services
    initialize_application_services()
except Exception as e:
    print(f"Warning: Failed to initialize application services: {e}")

# For SocketIO support with gunicorn, the SocketIO object itself is the WSGI application
# Flask-SocketIO wraps the Flask app and is directly callable
try:
    # Check if SocketIO is properly initialized and callable
    if hasattr(socketio, 'wsgi_app') and callable(socketio):
        print("✅ SocketIO object is callable, using for WSGI")
        application = socketio
    elif hasattr(socketio, '__call__'):
        print("✅ SocketIO has __call__ method, using for WSGI")
        application = socketio
    else:
        print("⚠️  SocketIO object not callable, falling back to Flask app")
        print(f"SocketIO type: {type(socketio)}")
        print(f"SocketIO callable: {callable(socketio)}")
        application = app
except Exception as e:
    print(f"❌ Error with SocketIO setup: {e}, using Flask app")
    application = app

# Verify final application is callable
print(f"Final application type: {type(application)}")
print(f"Final application callable: {callable(application)}")

# Ensure the Flask app is also available for compatibility
flask_app = app

if __name__ == "__main__":
    # Development mode - use SocketIO.run for WebSocket support
    port = int(os.environ.get('PORT', 5006))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)

