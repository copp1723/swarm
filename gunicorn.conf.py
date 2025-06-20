"""
Gunicorn configuration for MCP Executive with SocketIO support
"""

import os

# Server socket - Render requires binding to 0.0.0.0 and the PORT env var
bind = f"0.0.0.0:{os.environ.get('PORT', 10000)}"
wsproto = "uvloop"
backlog = 2048

# Worker processes - Use fewer workers for Render's resource constraints
workers = int(os.environ.get('WEB_CONCURRENCY', 2))
worker_class = "gevent"  # Use gevent for better performance and compatibility
worker_connections = 1000
timeout = 120  # Increased timeout for long-running operations
keepalive = 5

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'mcp-executive'

# Server mechanics
preload_app = True
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = None
certfile = None

# Application
wsgi_app = "wsgi:app"

