#!/bin/bash

# Celery Worker Startup Script
# This script starts Celery workers for the MCP Multi-Agent Platform

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Celery Workers for MCP Multi-Agent Platform${NC}"

# Check if Redis is running
echo -e "\n${YELLOW}Checking Redis connection...${NC}"
redis-cli ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}Error: Redis is not running. Please start Redis first.${NC}"
    echo "You can start Redis with: redis-server"
    exit 1
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "\n${YELLOW}Activating virtual environment...${NC}"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo -e "${GREEN}✓ Virtual environment activated${NC}"
    else
        echo -e "${RED}Error: Virtual environment not found. Please create it first.${NC}"
        echo "Run: python -m venv venv"
        exit 1
    fi
fi

# Function to start a worker
start_worker() {
    local queue=$1
    local concurrency=$2
    local worker_name=$3
    
    echo -e "\n${YELLOW}Starting $worker_name worker...${NC}"
    celery -A config.celery_config:celery_app worker \
        --loglevel=info \
        --concurrency=$concurrency \
        --hostname=$worker_name@%h \
        --queues=$queue \
        --pool=prefork \
        --without-gossip \
        --without-mingle \
        --without-heartbeat &
    
    local pid=$!
    echo $pid >> celery_workers.pid
    echo -e "${GREEN}✓ $worker_name worker started (PID: $pid)${NC}"
}

# Clean up any existing PID file
rm -f celery_workers.pid

# Start workers for different queues
echo -e "\n${GREEN}Starting specialized workers...${NC}"

# Email queue worker (2 concurrent processes)
start_worker "email_queue" 2 "email"

# Webhook queue worker (3 concurrent processes for higher throughput)
start_worker "webhook_queue" 3 "webhook"

# Memory queue worker (1 process to avoid conflicts)
start_worker "memory_queue" 1 "memory"

# Default queue worker (2 processes for general tasks)
start_worker "default" 2 "default"

# Wait a moment for workers to start
sleep 2

# Start Celery Beat scheduler in a separate terminal/process
echo -e "\n${YELLOW}Starting Celery Beat scheduler...${NC}"
celery -A config.celery_config:celery_app beat \
    --loglevel=info \
    --pidfile=celerybeat.pid &

BEAT_PID=$!
echo $BEAT_PID >> celery_workers.pid
echo -e "${GREEN}✓ Celery Beat started (PID: $BEAT_PID)${NC}"

# Display worker status
echo -e "\n${GREEN}Worker Status:${NC}"
echo "----------------------------------------"
celery -A config.celery_config:celery_app status

echo -e "\n${GREEN}Active Queues:${NC}"
echo "----------------------------------------"
celery -A config.celery_config:celery_app inspect active_queues

echo -e "\n${GREEN}All Celery workers started successfully!${NC}"
echo -e "\n${YELLOW}Monitor workers with:${NC}"
echo "  celery -A config.celery_config:celery_app events"
echo "  celery -A config.celery_config:celery_app flower  # Web UI monitoring"
echo ""
echo -e "${YELLOW}Stop workers with:${NC}"
echo "  ./scripts/stop_celery_workers.sh"
echo ""
echo -e "${YELLOW}View logs in real-time:${NC}"
echo "  tail -f celery_*.log"