"""
Replay Protection Middleware
Integrates token replay cache to prevent replay attacks
"""

import logging
from functools import wraps
from flask import request, jsonify, g
from typing import Optional, Callable, Dict, Any
from services.token_replay_cache import get_token_replay_cache
from utils.async_wrapper import async_manager

logger = logging.getLogger(__name__)

class ReplayProtectionMiddleware:
    """Middleware to prevent token replay attacks"""
    
    def __init__(self, app=None):
        self.app = app
        self.token_cache = get_token_replay_cache()
        self.excluded_paths = {
            '/health',
            '/api/status',
            '/static',
            '/',
            '/favicon.ico'
        }
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with a Flask app"""
        self.app = app
        app.before_request(self.check_replay_attack)
    
    def should_check_path(self, path: str) -> bool:
        """Determine if the path should be checked for replay attacks"""
        # Skip static files and excluded paths
        for excluded in self.excluded_paths:
            if path.startswith(excluded):
                return False
        
        # Only check API endpoints that modify state
        if path.startswith('/api/') and request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            return True
        
        return False
    
    def extract_token(self) -> Optional[str]:
        """Extract token from the request"""
        # Try different token locations in order of preference
        
        # 1. Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]
        
        # 2. X-Request-Token header (custom token)
        request_token = request.headers.get('X-Request-Token')
        if request_token:
            return request_token
        
        # 3. Token in JSON body
        if request.is_json:
            data = request.get_json(silent=True)
            if data and isinstance(data, dict):
                token = data.get('request_token') or data.get('token')
                if token:
                    return token
        
        # 4. Token in form data
        if request.form:
            return request.form.get('request_token') or request.form.get('token')
        
        # 5. Token in query parameters (least secure, not recommended)
        return request.args.get('token')
    
    def get_request_context(self) -> Dict[str, Any]:
        """Get context information about the request"""
        return {
            'method': request.method,
            'path': request.path,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')[:50],  # Truncate for privacy
            'session_id': g.get('session_id')  # If available
        }
    
    @async_manager.async_route
    async def check_replay_attack(self):
        """Check if the request is a replay attack"""
        # Skip if path shouldn't be checked
        if not self.should_check_path(request.path):
            return None
        
        # Extract token
        token = self.extract_token()
        if not token:
            # No token provided - let the endpoint handle authentication
            logger.debug(f"No replay token found for {request.method} {request.path}")
            return None
        
        # Get request context
        context = self.get_request_context()
        
        # Check if token has been seen
        is_replay = await self.token_cache.has_seen_token(token, context)
        
        if is_replay:
            logger.warning(f"Replay attack detected from {context['ip']} for {context['path']}")
            return jsonify({
                'error': 'Invalid or expired token',
                'code': 'REPLAY_DETECTED',
                'message': 'This request has already been processed'
            }), 400
        
        # Token is valid, continue processing
        g.replay_token = token  # Store for potential use in endpoint
        return None


def replay_protection_required(extract_token_func: Optional[Callable] = None):
    """
    Decorator to require replay protection for specific endpoints.
    
    Args:
        extract_token_func: Optional custom function to extract token from request
    """
    def decorator(f):
        @wraps(f)
        @async_manager.async_route
        async def decorated_function(*args, **kwargs):
            token_cache = get_token_replay_cache()
            
            # Use custom token extraction if provided
            if extract_token_func:
                token = extract_token_func(request)
            else:
                # Use default extraction
                middleware = ReplayProtectionMiddleware()
                token = middleware.extract_token()
            
            if not token:
                return jsonify({
                    'error': 'Token required',
                    'code': 'MISSING_TOKEN',
                    'message': 'This endpoint requires a unique request token'
                }), 400
            
            # Get context
            context = {
                'endpoint': request.endpoint,
                'method': request.method,
                'ip': request.remote_addr
            }
            
            # Check replay
            is_replay = await token_cache.has_seen_token(token, context)
            if is_replay:
                logger.warning(f"Replay attack on {request.endpoint} from {request.remote_addr}")
                return jsonify({
                    'error': 'Token already used',
                    'code': 'REPLAY_DETECTED',
                    'message': 'This token has already been used'
                }), 400
            
            # Token is valid, proceed with the request
            return await f(*args, **kwargs)
        
        return decorated_function
    return decorator


# Convenience decorator without custom extraction
require_replay_protection = replay_protection_required()