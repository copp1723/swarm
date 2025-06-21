#!/bin/bash
#
# Celery Worker Service Script for SWARM
# Runs the Celery worker for background task processing in production mode
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
: "${CELERY_CONCURRENCY:=2}"
: "${CELERY_QUEUES:=agent_queue,analysis_queue}"
: "${CELERY_LOG_LEVEL:=info}"
: "${CELERY_HOSTNAME:=worker@%h}"
: "${CELERY_MAX_TASKS_PER_CHILD:=100}"
: "${CELERY_TASK_TIME_LIMIT:=300}"
: "${CELERY_TASK_SOFT_TIME_LIMIT:=240}"
: "${CELERY_OPTIMIZATION:=fair}"

# Log file path
CELERY_LOG="$LOG_DIR/celery_worker.log"

echo "Starting Celery worker for SWARM..."
echo "Application: $CELERY_APP"
echo "Concurrency: $CELERY_CONCURRENCY"
echo "Queues: $CELERY_QUEUES"
echo "Log level: $CELERY_LOG_LEVEL"
echo "Log file: $CELERY_LOG"

# Function to handle shutdown
cleanup() {
    echo "Received shutdown signal. Stopping Celery worker gracefully..."
    # Send TERM signal to the Celery worker
    kill -TERM "$PID" 2>/dev/null || true
    wait "$PID"
    exit 0
}

# Register signal handlers
trap cleanup SIGINT SIGTERM

# Start Celery worker
celery -A "$CELERY_APP" worker \
    --concurrency="$CELERY_CONCURRENCY" \
    --queues="$CELERY_QUEUES" \
    --hostname="$CELERY_HOSTNAME" \
    --loglevel="$CELERY_LOG_LEVEL" \
    --logfile="$CELERY_LOG" \
    --max-tasks-per-child="$CELERY_MAX_TASKS_PER_CHILD" \
    --time-limit="$CELERY_TASK_TIME_LIMIT" \
    --soft-time-limit="$CELERY_TASK_SOFT_TIME_LIMIT" \
    --optimization="$CELERY_OPTIMIZATION" \
    --without-gossip \
    --without-mingle \
    --pidfile="${PROJECT_ROOT}/celery_worker.pid" &

PID=$!

# Wait for the process to complete or be terminated
wait $PID
