"""Session management utilities"""
import uuid
from flask import request, session

def get_session_id():
    """Get or create a session ID for the current request"""
    # Check if session ID exists in session
    if 'session_id' in session:
        return session['session_id']
    
    # Check if session ID exists in request headers
    session_id = request.headers.get('X-Session-ID')
    
    if not session_id:
        # Generate a new session ID
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    return session_id