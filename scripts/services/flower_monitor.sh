#!/bin/bash
#
# Flower Monitor Service Script for SWARM
# Runs the Flower monitoring interface for Celery task monitoring in production mode
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
: "${CELERY_APP:=config.celery_config:celery_app}"
: "${FLOWER_PORT:=5555}"
: "${FLOWER_HOST:=0.0.0.0}"
: "${FLOWER_URL_PREFIX:=}"
: "${FLOWER_LOG_LEVEL:=info}"
: "${FLOWER_PERSISTENT:=true}"
: "${FLOWER_DB:=$PROJECT_ROOT/flower.db}"
: "${FLOWER_BASIC_AUTH:=}"  # Format: user1:password1,user2:password2
: "${FLOWER_BROKER_API:=}"  # Redis monitoring API URL (optional)
: "${FLOWER_MAX_TASKS:=10000}"
: "${FLOWER_AUTO_REFRESH:=3.0}"  # Seconds

# Log file path
FLOWER_LOG="$LOG_DIR/flower_monitor.log"

echo "Starting Flower monitoring service for SWARM..."
echo "Application: $CELERY_APP"
echo "Listening on: $FLOWER_HOST:$FLOWER_PORT"
echo "Log level: $FLOWER_LOG_LEVEL"
echo "Log file: $FLOWER_LOG"
echo "Persistent storage: $FLOWER_PERSISTENT"

# Build command arguments
FLOWER_ARGS=(
    -A "$CELERY_APP"
    flower
    --port="$FLOWER_PORT"
    --address="$FLOWER_HOST"
    --log-file-prefix="$FLOWER_LOG"
    --logging="$FLOWER_LOG_LEVEL"
    --max-tasks="$FLOWER_MAX_TASKS"
    --auto-refresh="$FLOWER_AUTO_REFRESH"
)

# Add optional arguments if set
if [ -n "$FLOWER_URL_PREFIX" ]; then
    FLOWER_ARGS+=(--url-prefix="$FLOWER_URL_PREFIX")
fi

if [ "$FLOWER_PERSISTENT" = "true" ]; then
    FLOWER_ARGS+=(--persistent=true --db="$FLOWER_DB")
fi

if [ -n "$FLOWER_BASIC_AUTH" ]; then
    FLOWER_ARGS+=(--basic-auth="$FLOWER_BASIC_AUTH")
fi

if [ -n "$FLOWER_BROKER_API" ]; then
    FLOWER_ARGS+=(--broker-api="$FLOWER_BROKER_API")
fi

# Function to handle shutdown
cleanup() {
    echo "Received shutdown signal. Stopping Flower monitor gracefully..."
    # Send TERM signal to the Flower process
    kill -TERM "$PID" 2>/dev/null || true
    wait "$PID"
    exit 0
}

# Register signal handlers
trap cleanup SIGINT SIGTERM

# Start Flower monitor
celery "${FLOWER_ARGS[@]}" --pidfile="${PROJECT_ROOT}/flower_monitor.pid" &

PID=$!

# Wait for the process to complete or be terminated
wait $PID
