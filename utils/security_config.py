"""
Security Configuration Management
Centralized security settings and utilities for the SWARM system
"""

import os
import secrets
import base64
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from flask import Flask

from utils.logging_config import get_logger

logger = get_logger(__name__)


class SecurityConfig:
    """Centralized security configuration management"""
    
    # Security defaults
    DEFAULT_JWT_EXPIRY_HOURS = 24
    DEFAULT_API_KEY_LENGTH = 32
    DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds
    DEFAULT_PASSWORD_MIN_LENGTH = 12
    
    # Trusted IP patterns (for development)
    TRUSTED_IP_PATTERNS = [
        '127.0.0.1',
        '::1',
        '10.*',
        '192.168.*',
        '172.16.*',
        '172.17.*',
        '172.18.*',
        '172.19.*',
        '172.20.*',
        '172.21.*',
        '172.22.*',
        '172.23.*',
        '172.24.*',
        '172.25.*',
        '172.26.*',
        '172.27.*',
        '172.28.*',
        '172.29.*',
        '172.30.*',
        '172.31.*'
    ]
    
    # Suspicious patterns
    SUSPICIOUS_PATTERNS = [
        'bot',
        'crawler',
        'scanner',
        'hack',
        'attack',
        'exploit'
    ]
    
    @classmethod
    def get_environment(cls) -> str:
        """Get current environment"""
        return os.getenv('FLASK_ENV', 'production').lower()
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production"""
        return cls.get_environment() == 'production'
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development"""
        return cls.get_environment() == 'development'
    
    @classmethod
    def generate_secure_key(cls, length: int = 32) -> str:
        """Generate a cryptographically secure key"""
        return secrets.token_urlsafe(length)
    
    @classmethod
    def generate_api_key(cls, prefix: str = 'sk-swarm') -> str:
        """Generate a secure API key with prefix"""
        key_data = secrets.token_urlsafe(cls.DEFAULT_API_KEY_LENGTH)
        return f"{prefix}-{key_data}"
    
    @classmethod
    def hash_api_key(cls, api_key: str) -> str:
        """Hash an API key for secure storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @classmethod
    def verify_api_key(cls, provided_key: str, stored_hash: str) -> bool:
        """Verify an API key against stored hash"""
        return hashlib.sha256(provided_key.encode()).hexdigest() == stored_hash
    
    @classmethod
    def get_security_headers_config(cls) -> Dict[str, Any]:
        """Get security headers configuration"""
        return {
            'enabled': os.getenv('ENABLE_SECURITY_HEADERS', 'true').lower() == 'true',
            'hsts_enabled': os.getenv('ENABLE_HSTS', 'true').lower() == 'true',
            'hsts_max_age': int(os.getenv('HSTS_MAX_AGE', '31536000')),
            'hsts_include_subdomains': os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'true').lower() == 'true',
            'hsts_preload': os.getenv('HSTS_PRELOAD', 'false').lower() == 'true',
            'csp_environment': os.getenv('CSP_ENVIRONMENT', 'production'),
            'csp_nonce_enabled': os.getenv('CSP_NONCE_ENABLED', 'true').lower() == 'true',
            'disable_csp': os.getenv('DISABLE_CSP', 'false').lower() == 'true'
        }
    
    @classmethod
    def get_rate_limit_config(cls) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            'enabled': os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            'storage': os.getenv('RATE_LIMIT_STORAGE', 'redis'),
            'default_window': cls.DEFAULT_RATE_LIMIT_WINDOW,
            'policies': {
                'authentication': {
                    'per_minute': int(os.getenv('RATE_LIMIT_AUTHENTICATION_PER_MINUTE', '5')),
                    'per_hour': int(os.getenv('RATE_LIMIT_AUTHENTICATION_PER_HOUR', '20'))
                },
                'api_standard': {
                    'per_minute': int(os.getenv('RATE_LIMIT_API_STANDARD_PER_MINUTE', '60')),
                    'per_hour': int(os.getenv('RATE_LIMIT_API_STANDARD_PER_HOUR', '1000'))
                },
                'api_intensive': {
                    'per_minute': int(os.getenv('RATE_LIMIT_API_INTENSIVE_PER_MINUTE', '10')),
                    'per_hour': int(os.getenv('RATE_LIMIT_API_INTENSIVE_PER_HOUR', '100'))
                },
                'file_upload': {
                    'per_minute': int(os.getenv('RATE_LIMIT_FILE_UPLOAD_PER_MINUTE', '5')),
                    'per_hour': int(os.getenv('RATE_LIMIT_FILE_UPLOAD_PER_HOUR', '50'))
                },
                'webhook': {
                    'per_minute': int(os.getenv('RATE_LIMIT_WEBHOOKS_PER_MINUTE', '100')),
                    'per_hour': int(os.getenv('RATE_LIMIT_WEBHOOKS_PER_HOUR', '2000'))
                },
                'monitoring': {
                    'per_minute': int(os.getenv('RATE_LIMIT_MONITORING_PER_MINUTE', '300')),
                    'per_hour': int(os.getenv('RATE_LIMIT_MONITORING_PER_HOUR', '5000'))
                },
                'public': {
                    'per_minute': int(os.getenv('RATE_LIMIT_PUBLIC_PER_MINUTE', '30')),
                    'per_hour': int(os.getenv('RATE_LIMIT_PUBLIC_PER_HOUR', '300'))
                }
            },
            'ip_policies': {
                'default': {
                    'per_minute': int(os.getenv('RATE_LIMIT_IP_DEFAULT_PER_MINUTE', '30')),
                    'per_hour': int(os.getenv('RATE_LIMIT_IP_DEFAULT_PER_HOUR', '300'))
                },
                'trusted': {
                    'per_minute': int(os.getenv('RATE_LIMIT_IP_TRUSTED_PER_MINUTE', '120')),
                    'per_hour': int(os.getenv('RATE_LIMIT_IP_TRUSTED_PER_HOUR', '2000'))
                },
                'suspicious': {
                    'per_minute': int(os.getenv('RATE_LIMIT_IP_SUSPICIOUS_PER_MINUTE', '5')),
                    'per_hour': int(os.getenv('RATE_LIMIT_IP_SUSPICIOUS_PER_HOUR', '20'))
                }
            }
        }
    
    @classmethod
    def get_cookie_config(cls) -> Dict[str, Any]:
        """Get secure cookie configuration"""
        is_prod = cls.is_production()
        return {
            'secure': os.getenv('SESSION_COOKIE_SECURE', str(is_prod)).lower() == 'true',
            'httponly': os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true',
            'samesite': os.getenv('SESSION_COOKIE_SAMESITE', 'Lax'),
            'max_age': int(os.getenv('SESSION_COOKIE_MAX_AGE', '3600'))  # 1 hour
        }
    
    @classmethod
    def get_cors_config(cls) -> Dict[str, Any]:
        """Get CORS configuration"""
        if cls.is_development():
            return {
                'origins': ['*'],
                'allow_headers': ['*'],
                'expose_headers': ['*'],
                'supports_credentials': False
            }
        else:
            return {
                'origins': os.getenv('CORS_ORIGINS', 'https://your-domain.com').split(','),
                'allow_headers': ['Content-Type', 'Authorization', 'X-API-Key'],
                'expose_headers': ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'],
                'supports_credentials': True
            }
    
    @classmethod
    def classify_ip(cls, ip_address: str) -> str:
        """Classify an IP address as trusted, default, or suspicious"""
        if not ip_address:
            return 'suspicious'
        
        # Check for trusted patterns (development/local)
        for pattern in cls.TRUSTED_IP_PATTERNS:
            if pattern.endswith('*'):
                if ip_address.startswith(pattern[:-1]):
                    return 'trusted'
            elif pattern == ip_address:
                return 'trusted'
        
        # Check for suspicious patterns in user agent or other headers
        # This would need request context to check headers
        return 'default'
    
    @classmethod
    def is_suspicious_request(cls, user_agent: Optional[str] = None, referer: Optional[str] = None) -> bool:
        """Check if a request appears suspicious"""
        if user_agent:
            user_agent_lower = user_agent.lower()
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if pattern in user_agent_lower:
                    return True
        
        # Check for suspicious referers
        if referer and ('hack' in referer.lower() or 'exploit' in referer.lower()):
            return True
        
        return False
    
    @classmethod
    def get_feature_flags(cls) -> Dict[str, bool]:
        """Get security-related feature flags"""
        return {
            'rate_limiting': os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true',
            'ip_whitelisting': os.getenv('ENABLE_IP_WHITELISTING', 'false').lower() == 'true',
            'request_signing': os.getenv('ENABLE_REQUEST_SIGNING', 'false').lower() == 'true',
            'api_key_rotation': os.getenv('ENABLE_API_KEY_ROTATION', 'true').lower() == 'true',
            'adaptive_rate_limiting': os.getenv('ENABLE_ADAPTIVE_RATE_LIMITING', 'false').lower() == 'true',
            'circuit_breakers': os.getenv('ENABLE_CIRCUIT_BREAKERS', 'true').lower() == 'true',
            'audit_logging': os.getenv('ENABLE_AUDIT_LOGGING', 'true').lower() == 'true'
        }
    
    @classmethod
    def configure_app_security(cls, app: Flask) -> None:
        """Configure Flask app with security settings"""
        # Basic security configuration
        app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY') or cls.generate_secure_key()
        
        # Session configuration
        cookie_config = cls.get_cookie_config()
        app.config['SESSION_COOKIE_SECURE'] = cookie_config['secure']
        app.config['SESSION_COOKIE_HTTPONLY'] = cookie_config['httponly']
        app.config['SESSION_COOKIE_SAMESITE'] = cookie_config['samesite']
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=cookie_config['max_age'])
        
        # File upload security
        app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', '52428800'))  # 50MB
        
        # Production-specific settings
        if cls.is_production():
            app.config['SESSION_COOKIE_SECURE'] = True
            app.config['PREFERRED_URL_SCHEME'] = 'https'
        
        logger.info("Flask app security configuration applied")
    
    @classmethod
    def validate_security_config(cls) -> List[str]:
        """Validate current security configuration and return warnings"""
        warnings = []
        
        # Check for required environment variables
        required_vars = ['SECRET_KEY', 'JWT_SECRET_KEY']
        for var in required_vars:
            if not os.getenv(var):
                warnings.append(f"Missing required environment variable: {var}")
        
        # Check for weak keys in production
        if cls.is_production():
            secret_key = os.getenv('SECRET_KEY', '')
            if len(secret_key) < 32:
                warnings.append("SECRET_KEY should be at least 32 characters in production")
            
            if secret_key in ['development', 'debug', 'test', 'secret']:
                warnings.append("SECRET_KEY appears to be a default/weak value")
        
        # Check HTTPS in production
        if cls.is_production():
            if not os.getenv('FORCE_HTTPS', 'false').lower() == 'true':
                warnings.append("FORCE_HTTPS should be enabled in production")
        
        # Check rate limiting
        if not os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true':
            warnings.append("Rate limiting is disabled - this may allow abuse")
        
        return warnings


# Global security config instance
security_config = SecurityConfig()


def setup_security_monitoring(app: Flask) -> None:
    """Setup security monitoring and logging"""
    @app.before_request
    def log_security_events():
        """Log security-relevant events"""
        from flask import request, g
        
        # Generate request ID for tracking
        g.request_id = secrets.token_hex(8)
        
        # Log suspicious requests
        if security_config.is_suspicious_request(
            request.headers.get('User-Agent'),
            request.headers.get('Referer')
        ):
            logger.warning(
                "Suspicious request detected",
                extra={
                    'request_id': g.request_id,
                    'ip': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent'),
                    'path': request.path
                }
            )


def generate_csp_nonce() -> str:
    """Generate a cryptographically secure nonce for CSP"""
    return base64.b64encode(secrets.token_bytes(16)).decode('utf-8')


def get_security_context() -> Dict[str, Any]:
    """Get current security context information"""
    return {
        'environment': SecurityConfig.get_environment(),
        'production': SecurityConfig.is_production(),
        'security_headers_enabled': SecurityConfig.get_security_headers_config()['enabled'],
        'rate_limiting_enabled': SecurityConfig.get_rate_limit_config()['enabled'],
        'feature_flags': SecurityConfig.get_feature_flags(),
        'timestamp': datetime.utcnow().isoformat()
    }
