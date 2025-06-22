"""
Security Headers Middleware
Adds security headers to all HTTP responses
"""
from flask import Flask, Response, g, request
from typing import Dict, Optional, Callable
import os
import secrets
import base64


class SecurityHeadersMiddleware:
    """Middleware to add security headers to responses"""
    
    # Default security headers
    DEFAULT_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    }
    
    # Content Security Policy for different environments
    CSP_POLICIES = {
        'development': {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "http://localhost:*"],
            'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            'font-src': ["'self'", "https://fonts.gstatic.com"],
            'img-src': ["'self'", "data:", "https:"],
            'connect-src': ["'self'", "http://localhost:*", "ws://localhost:*", "https://api.openrouter.ai"],
        },
        'production': {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://cdn.tailwindcss.com", "https://unpkg.com", "https://cdn.socket.io", "https://cdnjs.cloudflare.com"],
            'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.tailwindcss.com", "https://unpkg.com"],
            'font-src': ["'self'", "https://fonts.gstatic.com", "data:"],
            'img-src': ["'self'", "data:", "https:", "blob:"],
            'connect-src': ["'self'", "https://api.openrouter.ai", "wss:", "ws:", "https:"],
            'frame-ancestors': ["'none'"],
            'base-uri': ["'self'"],
            'form-action': ["'self'"],
            'worker-src': ["'self'", "blob:"],
            'child-src': ["'self'", "blob:"]
        }
    }
    
    def __init__(
        self,
        app: Optional[Flask] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        csp_policy: Optional[Dict[str, list]] = None,
        hsts_enabled: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False
    ):
        """Initialize security headers middleware"""
        self.custom_headers = custom_headers or {}
        self.csp_policy = csp_policy
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the middleware with a Flask app"""
        app.after_request(self.add_security_headers)
        
        # Store config in app
        app.config['SECURITY_HEADERS_MIDDLEWARE'] = self
    
    def add_security_headers(self, response: Response) -> Response:
        """Add security headers to the response"""
        # Check if CSP is disabled via environment variable
        if os.getenv('DISABLE_CSP', '').lower() in ('true', '1', 'yes'):
            # Skip CSP but add other security headers
            for header, value in self.DEFAULT_HEADERS.items():
                response.headers[header] = value
            for header, value in self.custom_headers.items():
                response.headers[header] = value
            return response
        # Add default headers
        for header, value in self.DEFAULT_HEADERS.items():
            response.headers[header] = value
        
        # Add custom headers
        for header, value in self.custom_headers.items():
            response.headers[header] = value
        
        # Add HSTS header (only for HTTPS in production)
        if self.hsts_enabled and self._is_https():
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            response.headers['Strict-Transport-Security'] = hsts_value
        
        # Add Content Security Policy
        csp = self._build_csp()
        if csp:
            response.headers['Content-Security-Policy'] = csp
        
        return response
    
    def _build_csp(self) -> str:
        """Build Content Security Policy string"""
        if self.csp_policy:
            policy = self.csp_policy
        else:
            # Use environment-based policy
            env = os.getenv('FLASK_ENV', 'production')
            policy = self.CSP_POLICIES.get(env, self.CSP_POLICIES['production'])
        
        # Build CSP string
        csp_parts = []
        for directive, sources in policy.items():
            if sources:
                sources_str = ' '.join(sources)
                csp_parts.append(f"{directive} {sources_str}")
        
        return '; '.join(csp_parts)
    
    def _is_https(self) -> bool:
        """Check if the request is over HTTPS"""
        # In production, check for proxy headers
        from flask import request
        return (
            request.is_secure or
            request.headers.get('X-Forwarded-Proto', '').lower() == 'https'
        )


def init_security_headers(
    app: Flask,
    **kwargs
) -> SecurityHeadersMiddleware:
    """Initialize security headers for the Flask app"""
    return SecurityHeadersMiddleware(app, **kwargs)


# Additional security utilities
def secure_filename_check(filename: str, allowed_extensions: set) -> tuple[bool, Optional[str]]:
    """Enhanced secure filename checking"""
    if not filename:
        return False, "No filename provided"
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename: contains path separators"
    
    # Check extension
    if '.' not in filename:
        return False, "Invalid filename: no extension"
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        return False, f"Invalid file type: .{ext} not allowed"
    
    # Check for double extensions that might bypass filters
    parts = filename.lower().split('.')
    if len(parts) > 2:
        for part in parts[:-1]:
            if part in ['php', 'exe', 'sh', 'bat', 'cmd', 'com']:
                return False, "Invalid filename: suspicious double extension"
    
    return True, None


def validate_file_path(
    path: str,
    base_directory: str = "/Users/copp1723/Desktop",
    must_exist: bool = False,
    must_be_file: bool = False
) -> tuple[bool, str, Optional[Response]]:
    """Validate file path for security"""
    import os
    from utils.api_response import error_response
    
    # Normalize and resolve the path
    try:
        # Convert to absolute path
        if not os.path.isabs(path):
            abs_path = os.path.abspath(os.path.join(base_directory, path))
        else:
            abs_path = os.path.abspath(path)
        
        # Ensure it's within allowed directory
        if not abs_path.startswith(os.path.abspath(base_directory)):
            return False, "", error_response("Access denied: Path outside allowed directory", 403)
        
        # Check existence if required
        if must_exist and not os.path.exists(abs_path):
            return False, "", error_response("Path not found", 404)
        
        # Check if it's a file when required
        if must_be_file and os.path.exists(abs_path) and not os.path.isfile(abs_path):
            return False, "", error_response("Path is not a file", 400)
        
        return True, abs_path, None
        
    except Exception as e:
        return False, "", error_response(f"Invalid path: {str(e)}", 400)