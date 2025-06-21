#!/bin/bash
#
# Gunicorn Web Server Service Script for SWARM
# Runs the Flask application with Gunicorn in production mode
#

set -e  # Exit immediately if a command exits with a non-zero status

# Determine the absolute path to the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_DIR="$PROJECT_ROOT/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Add project root to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Load environment variables from .env files if they exist
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading environment variables from .env"
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Default configuration values (can be overridden by environment variables)
: "${FLASK_ENV:=production}"
: "${FLASK_DEBUG:=False}"
: "${GUNICORN_WORKERS:=4}"  # (2 * CPU_COUNT) + 1 is recommended
: "${GUNICORN_THREADS:=2}"
: "${GUNICORN_TIMEOUT:=120}"
: "${GUNICORN_KEEPALIVE:=2}"
: "${GUNICORN_MAX_REQUESTS:=1000}"
: "${GUNICORN_MAX_REQUESTS_JITTER:=100}"
: "${PORT:=5006}"
: "${HOST:=0.0.0.0}"
: "${APP_MODULE:=app:app}"
: "${LOG_LEVEL:=info}"

# Export for Gunicorn
export FLASK_ENV
export FLASK_DEBUG

# Log file paths
ACCESS_LOG="$LOG_DIR/gunicorn_access.log"
ERROR_LOG="$LOG_DIR/gunicorn_error.log"

echo "Starting Gunicorn web server for SWARM..."
echo "Environment: $FLASK_ENV"
echo "Workers: $GUNICORN_WORKERS"
echo "Listening on: $HOST:$PORT"
echo "Log level: $LOG_LEVEL"
echo "Logs: $LOG_DIR"

# Function to handle shutdown
cleanup() {
    echo "Received shutdown signal. Stopping Gunicorn gracefully..."
    # You might want to add additional cleanup here
    exit 0
}

# Register signal handlers
trap cleanup SIGINT SIGTERM

# Start Gunicorn with gevent worker class for WebSocket support
exec gunicorn \
    --workers "$GUNICORN_WORKERS" \
    --threads "$GUNICORN_THREADS" \
    --worker-class gevent \
    --bind "$HOST:$PORT" \
    --timeout "$GUNICORN_TIMEOUT" \
    --keep-alive "$GUNICORN_KEEPALIVE" \
    --max-requests "$GUNICORN_MAX_REQUESTS" \
    --max-requests-jitter "$GUNICORN_MAX_REQUESTS_JITTER" \
    --access-logfile "$ACCESS_LOG" \
    --error-logfile "$ERROR_LOG" \
    --log-level "$LOG_LEVEL" \
    --capture-output \
    --preload \
    --forwarded-allow-ips="*" \
    --statsd-host="${STATSD_HOST:-localhost:8125}" \
    "$APP_MODULE"
