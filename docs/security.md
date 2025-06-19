# Security Configuration Guide

This guide covers security best practices and configuration for the SWARM multi-agent system.

## 🔒 Security Headers

### Automatic Security Headers
The system includes middleware that automatically adds security headers to all HTTP responses:

```python
# In app.py
from middleware.security_headers import init_security_headers

# Initialize with default settings
init_security_headers(app)

# Or customize for your environment
init_security_headers(
    app,
    hsts_enabled=True,
    hsts_max_age=31536000,  # 1 year
    hsts_include_subdomains=True,
    custom_headers={
        'X-Powered-By': 'SWARM-AI'
    }
)
```

### Headers Applied
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection (legacy browsers)
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer info
- `Permissions-Policy` - Restricts browser features
- `Content-Security-Policy` - Controls resource loading
- `Strict-Transport-Security` - Forces HTTPS (production only)

### Content Security Policy (CSP)

#### Development Environment
```python
CSP_POLICIES = {
    'development': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "http://localhost:*"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        'connect-src': ["'self'", "http://localhost:*", "ws://localhost:*", "https://api.openrouter.ai"],
    }
}
```

#### Production Environment
```python
CSP_POLICIES = {
    'production': {
        'default-src': ["'self'"],
        'script-src': ["'self'"],  # No unsafe-inline or eval
        'style-src': ["'self'", "https://fonts.googleapis.com"],
        'connect-src': ["'self'", "https://api.openrouter.ai"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
    }
}
```

## 🔑 Authentication & API Keys

### Environment Variables
Never hardcode sensitive information. Use environment variables:

```bash
# .env file (never commit this!)
OPENROUTER_API_KEY=your_openrouter_key
SWARM_API_KEY=your_internal_api_key
JWT_SECRET_KEY=your_jwt_secret
DATABASE_URL=postgresql://user:pass@localhost/db
```

### API Key Management
```python
# Using the new utilities
from utils.api_response import unauthorized

@app.before_request
def check_api_key():
    if request.endpoint and 'api' in request.endpoint:
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('SWARM_API_KEY'):
            return unauthorized('Invalid API key')
```

### JWT Configuration
```python
# For future JWT implementation
from jose import jwt

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

def create_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET_KEY'), algorithm=JWT_ALGORITHM)
```

## 🛡️ Input Validation

### File Upload Security
```python
from middleware.security_headers import secure_filename_check

# Validate uploaded files
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'md', 'py'}

is_valid, error = secure_filename_check(filename, ALLOWED_EXTENSIONS)
if not is_valid:
    return error_response(error, 400)
```

### Path Traversal Protection
```python
from middleware.security_headers import validate_file_path

# Validate file paths
is_valid, abs_path, error = validate_file_path(
    user_path,
    base_directory='/Users/copp1723/Desktop',
    must_exist=True
)
if not is_valid:
    return error
```

## 🔐 Database Security

### Connection Security
```python
# Use the centralized database manager
from utils.db_connection import get_db_manager

db = get_db_manager()

# Always use parameterized queries
with db.session_scope() as session:
    user = session.query(User).filter_by(email=email).first()
    # Never use string formatting for SQL!
```

### Connection String Security
```python
# The db manager automatically sanitizes URLs for logging
# postgresql://user:****@localhost/db
```

## 🚦 Rate Limiting

### API Rate Limits (from .env)
```bash
RATE_LIMIT_WEBHOOKS_PER_MINUTE=100
RATE_LIMIT_TASKS_PER_MINUTE=50
RATE_LIMIT_SEARCHES_PER_MINUTE=30
```

### Implementation
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/api/agents/chat/<agent_id>')
@limiter.limit("10 per minute")
def chat_endpoint(agent_id):
    # Rate limited to 10 requests per minute
    pass
```

## 📝 Logging Security

### Secure Logging Configuration
```python
from utils.logging_setup import setup_logging

# Initialize secure logging
setup_logging(
    log_level='INFO',
    log_file='logs/app.log',
    use_json=True,  # Structured logging in production
    max_bytes=10*1024*1024,  # 10MB rotation
    backup_count=5
)
```

### Sensitive Data in Logs
```python
# Never log:
# - Passwords or API keys
# - Full credit card numbers
# - Personal identifying information (PII)
# - Session tokens

# Sanitize before logging
logger.info(f"User login: {email}")  # OK
logger.info(f"Password: {password}")  # NEVER DO THIS
```

## 🔄 Dependency Security

### Regular Updates
```bash
# Check for security updates
pip list --outdated

# Update specific packages
pip install --upgrade openai anthropic

# Use pip-audit for vulnerability scanning
pip install pip-audit
pip-audit
```

### Critical Dependencies Updated
- `openai`: 1.3.5 → 1.35.0 (security fixes)
- `anthropic`: 0.7.8 → 0.25.0 (security updates)
- `eventlet` → `gevent` (CVE fix)

## 🚨 Security Checklist

### Development
- [ ] Use `.env` for all secrets
- [ ] Enable debug mode only locally
- [ ] Test with security headers enabled
- [ ] Validate all user inputs
- [ ] Use parameterized database queries

### Pre-Production
- [ ] Run `pip-audit` for vulnerabilities
- [ ] Update all dependencies
- [ ] Review CSP policy for production
- [ ] Enable HTTPS/TLS
- [ ] Set strong JWT secrets
- [ ] Configure rate limiting
- [ ] Enable structured logging
- [ ] Disable debug mode

### Production
- [ ] Enable HSTS headers
- [ ] Use production CSP policy
- [ ] Monitor security logs
- [ ] Regular dependency updates
- [ ] API key rotation schedule
- [ ] Database backup encryption
- [ ] Security monitoring alerts

## 🆘 Security Incident Response

### If a Security Issue is Found:
1. **Assess** - Determine scope and impact
2. **Contain** - Disable affected features if needed
3. **Fix** - Apply security patches
4. **Test** - Verify the fix
5. **Deploy** - Push updates
6. **Monitor** - Watch for exploitation attempts
7. **Document** - Update security docs

### Reporting Security Issues
- Email: security@your-domain.com
- Do not create public GitHub issues for security vulnerabilities
- Include steps to reproduce
- Allow time for fixes before public disclosure

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Guide](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)