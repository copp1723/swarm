#!/bin/bash
#
# Celery Beat Service Script for SWARM
# Runs the Celery Beat scheduler for periodic task scheduling in production mode
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
: "${CELERY_LOG_LEVEL:=info}"
: "${CELERY_SCHEDULE_FILE:=$PROJECT_ROOT/celerybeat-schedule}"
: "${CELERY_MAX_INTERVAL:=300}"  # Maximum interval between rechecking schedule (seconds)

# Log file path
BEAT_LOG="$LOG_DIR/celery_beat.log"

echo "Starting Celery Beat scheduler for SWARM..."
echo "Application: $CELERY_APP"
echo "Log level: $CELERY_LOG_LEVEL"
echo "Schedule file: $CELERY_SCHEDULE_FILE"
echo "Log file: $BEAT_LOG"

# Function to handle shutdown
cleanup() {
    echo "Received shutdown signal. Stopping Celery Beat gracefully..."
    # Send TERM signal to the Celery Beat process
    kill -TERM "$PID" 2>/dev/null || true
    wait "$PID"
    exit 0
}

# Register signal handlers
trap cleanup SIGINT SIGTERM

# Start Celery Beat
celery -A "$CELERY_APP" beat \
    --loglevel="$CELERY_LOG_LEVEL" \
    --logfile="$BEAT_LOG" \
    --schedule="$CELERY_SCHEDULE_FILE" \
    --max-interval="$CELERY_MAX_INTERVAL" \
    --pidfile="${PROJECT_ROOT}/celery_beat.pid" &

PID=$!

# Wait for the process to complete or be terminated
wait $PID
