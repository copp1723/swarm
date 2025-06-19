"""Authentication and authorization utilities for SWARM"""
import os
import secrets
import jwt
from functools import wraps
from datetime import datetime, timedelta
from flask import request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from typing import Optional, Dict, Any
import logging
from models.core import db
from sqlalchemy import Column, String, DateTime, Boolean

# --------------------------------------------------------------------------- #
# Optional Redis support for JWT black-listing
# --------------------------------------------------------------------------- #

def _get_redis_connection():
    """
    Return a Redis connection if REDIS_URL is configured and redis is installed.
    Falls back to ``None`` if Redis is unavailable so that the codebase does not
    hard-depend on redis-py in all environments (e.g. local development).
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis  # type: ignore
    except ImportError:
        logger.warning("REDIS_URL set but 'redis' package not installed – "
                       "JWT revocation disabled.")
        return None
    try:
        return redis.Redis.from_url(redis_url, decode_responses=True)
    except Exception as exc:  # pragma: no cover
        logger.error(f"Cannot connect to Redis at {redis_url}: {exc}")
        return None

logger = logging.getLogger(__name__)


class APIKey(db.Model):
    """Model for storing API keys"""
    __tablename__ = 'api_keys'
    
    id = Column(String(100), primary_key=True)
    user_id = Column(String(50), nullable=False)
    key_hash = Column(String(255), nullable=False)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)


class AuthManager:
    """Manages authentication and authorization for the application"""
    
    def __init__(self, app=None):
        self.app = app
        self.secret_key = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the auth manager with Flask app"""
        self.app = app
        self.secret_key = app.config.get('JWT_SECRET_KEY', os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(32)))
        
        # Store the secret key in config for consistency
        app.config['JWT_SECRET_KEY'] = self.secret_key
    
    def generate_api_key(self, user_id: str, key_name: str = "default") -> str:
        """Generate a new API key for a user"""
        timestamp = datetime.utcnow().timestamp()
        return f"swarm_{user_id}_{key_name}_{secrets.token_urlsafe(32)}"
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage"""
        return generate_password_hash(api_key)
    
    def verify_api_key(self, api_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash"""
        return check_password_hash(hashed_key, api_key)
    
    def generate_jwt_token(self, user_id: str, role: str = "user", expires_in: int = 3600) -> str:
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'role': role,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'jti': secrets.token_urlsafe(16)  # JWT ID for revocation
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])

            # ------------------------------------------------------------------
            # Redis-backed blacklist check
            # ------------------------------------------------------------------
            redis_conn = _get_redis_connection()
            if redis_conn:
                jti = payload.get("jti")
                if jti and redis_conn.sismember("jwt_blacklist", jti):
                    logger.warning("JWT token has been revoked (black-list hit)")
                    return None

            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def revoke_token(self, jti: str):
        """Add token to revocation list (implement with Redis/DB)"""
        redis_conn = _get_redis_connection()
        if not redis_conn:
            logger.warning("Token revocation requested but Redis not available")
            return
        try:
            # Store in a Redis set for O(1) blacklist checks
            redis_conn.sadd("jwt_blacklist", jti)
            logger.info(f"JWT token revoked (jti={jti})")
        except Exception as exc:  # pragma: no cover
            logger.error(f"Failed to revoke JWT token {jti}: {exc}")


# Global auth manager instance
auth_manager = AuthManager()


def require_auth(f):
    """Decorator to require authentication via API key or JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if auth is bypassed in development
        try:
            from config.auth_config import AUTH_BYPASS_ENABLED, DEV_PUBLIC_ENDPOINTS
            if AUTH_BYPASS_ENABLED:
                # Check if current endpoint should be public in dev
                if any(request.path.startswith(endpoint) for endpoint in DEV_PUBLIC_ENDPOINTS):
                    request.is_authenticated = True
                    request.user_id = 'dev_user'
                    request.auth_method = 'dev_bypass'
                    return f(*args, **kwargs)
        except ImportError:
            pass
        
        # Check for API key first
        api_key = request.headers.get('X-API-Key')
        if api_key:
            # Validate API key (simplified for now)
            # In production, check against database
            if validate_api_key_simple(api_key):
                request.auth_method = 'api_key'
                request.user_id = extract_user_from_api_key(api_key)
                return f(*args, **kwargs)
        
        # Check for JWT token
        auth_header = request.headers.get('Authorization')
        if auth_header:
            try:
                # Extract token from "Bearer TOKEN" format
                parts = auth_header.split(' ')
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                    payload = auth_manager.verify_jwt_token(token)
                    if payload:
                        request.auth_method = 'jwt'
                        request.user_id = payload['user_id']
                        request.user_role = payload.get('role', 'user')
                        return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error processing auth header: {e}")
        
        return jsonify({
            'error': 'Authentication required',
            'message': 'Please provide a valid API key or JWT token'
        }), 401
    
    return decorated_function


def require_role(*allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            # For API key auth, assume 'api_user' role
            if hasattr(request, 'auth_method') and request.auth_method == 'api_key':
                user_role = 'api_user'
            else:
                user_role = getattr(request, 'user_role', 'user')
            
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires one of these roles: {", ".join(allowed_roles)}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def optional_auth(f):
    """Decorator for endpoints that work with or without authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Try to authenticate but don't fail if not authenticated
        api_key = request.headers.get('X-API-Key')
        auth_header = request.headers.get('Authorization')
        
        request.is_authenticated = False
        
        if api_key and validate_api_key_simple(api_key):
            request.is_authenticated = True
            request.auth_method = 'api_key'
            request.user_id = extract_user_from_api_key(api_key)
        elif auth_header:
            try:
                parts = auth_header.split(' ')
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
                    payload = auth_manager.verify_jwt_token(token)
                    if payload:
                        request.is_authenticated = True
                        request.auth_method = 'jwt'
                        request.user_id = payload['user_id']
                        request.user_role = payload.get('role', 'user')
            except:
                pass
        
        return f(*args, **kwargs)
    
    return decorated_function


# Simplified validation functions (replace with database lookups in production)
def validate_api_key_simple(api_key: str) -> bool:
    """Simple API key validation - replace with database lookup"""
    # Accept production-grade keys that follow the canonical pattern.
    if api_key.startswith("swarm_") and len(api_key) > 50:
        return True

    # Optionally allow a single development key **only** when explicitly
    # enabled and not running in production.
    dev_key = os.getenv("SWARM_DEV_API_KEY")
    allow_dev_flag = os.getenv("ALLOW_DEV_API_KEY", "false").lower() == "true"
    is_production = os.getenv("FLASK_ENV", "production").lower() == "production"

    if (
        allow_dev_flag
        and not is_production
        and dev_key
        and api_key == dev_key
    ):
        logger.debug("Dev API key accepted due to ALLOW_DEV_API_KEY=true")
        return True

    return False


def extract_user_from_api_key(api_key: str) -> str:
    """Extract user ID from API key"""
    # Format: swarm_USERID_KEYNAME_RANDOM
    parts = api_key.split('_')
    if len(parts) >= 4:
        return parts[1]
    return 'unknown'


def generate_default_api_key() -> str:
    """Generate a default API key for development"""
    key = f"swarm_dev_default_{secrets.token_urlsafe(32)}"
    logger.info(f"Generated development API key: {key}")
    return key