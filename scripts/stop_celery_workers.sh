#!/bin/bash

# Celery Worker Stop Script
# Gracefully stops all Celery workers and Beat scheduler

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Celery Workers...${NC}"

# Function to stop process gracefully
stop_process() {
    local pid=$1
    local name=$2
    
    if kill -0 $pid 2>/dev/null; then
        echo -e "${YELLOW}Stopping $name (PID: $pid)...${NC}"
        kill -TERM $pid
        
        # Wait for graceful shutdown (max 10 seconds)
        local count=0
        while kill -0 $pid 2>/dev/null && [ $count -lt 10 ]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if kill -0 $pid 2>/dev/null; then
            echo -e "${RED}Force stopping $name...${NC}"
            kill -KILL $pid
        fi
        
        echo -e "${GREEN}✓ $name stopped${NC}"
    fi
}

# Stop all workers from PID file
if [ -f "celery_workers.pid" ]; then
    echo -e "\n${YELLOW}Reading PIDs from celery_workers.pid...${NC}"
    while read pid; do
        if [ ! -z "$pid" ]; then
            stop_process $pid "Worker"
        fi
    done < celery_workers.pid
    
    # Remove PID file
    rm -f celery_workers.pid
    echo -e "${GREEN}✓ PID file removed${NC}"
else
    echo -e "${YELLOW}No PID file found. Searching for Celery processes...${NC}"
    
    # Find and stop Celery processes by name
    pkill -f "celery.*worker" || true
    pkill -f "celery.*beat" || true
fi

# Clean up Beat PID file
if [ -f "celerybeat.pid" ]; then
    rm -f celerybeat.pid
    echo -e "${GREEN}✓ Beat PID file removed${NC}"
fi

# Clean up Beat schedule file
if [ -f "celerybeat-schedule" ]; then
    rm -f celerybeat-schedule
    echo -e "${GREEN}✓ Beat schedule file removed${NC}"
fi

# Verify all processes are stopped
echo -e "\n${YELLOW}Verifying all Celery processes are stopped...${NC}"
if pgrep -f "celery.*worker|celery.*beat" > /dev/null; then
    echo -e "${RED}Warning: Some Celery processes may still be running${NC}"
    echo -e "${YELLOW}Remaining processes:${NC}"
    ps aux | grep -E "celery.*(worker|beat)" | grep -v grep
else
    echo -e "${GREEN}✓ All Celery processes stopped successfully${NC}"
fi

echo -e "\n${GREEN}Celery shutdown complete!${NC}"