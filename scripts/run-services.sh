#!/bin/bash
#
# SWARM Service Manager
# Controls all services for the SWARM multi-agent platform
#
# Usage: ./run-services.sh [command] [service...]
#
# Commands:
#   start    - Start services
#   stop     - Stop services
#   restart  - Restart services
#   status   - Show service status
#   logs     - View service logs
#
# Services:
#   web      - Gunicorn web server (Flask application)
#   worker   - Celery worker for background tasks
#   beat     - Celery beat scheduler for periodic tasks
#   flower   - Flower monitoring interface
#   all      - All services (default if none specified)
#
# Examples:
#   ./run-services.sh start           # Start all services
#   ./run-services.sh start web worker # Start only web and worker services
#   ./run-services.sh stop            # Stop all services
#   ./run-services.sh restart worker  # Restart only the worker service
#   ./run-services.sh status          # Show status of all services
#   ./run-services.sh logs web        # View logs for the web service
#

set -e  # Exit immediately if a command exits with a non-zero status

# Determine the absolute path to the project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICES_DIR="$SCRIPT_DIR/services"
LOG_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/run"

# Create necessary directories
mkdir -p "$LOG_DIR" "$PID_DIR"

# Add project root to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Load environment variables from .env files if they exist
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading environment variables from .env"
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a
fi

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Define service information
declare -A SERVICE_SCRIPTS
SERVICE_SCRIPTS["web"]="$SERVICES_DIR/gunicorn_web.sh"
SERVICE_SCRIPTS["worker"]="$SERVICES_DIR/celery_worker.sh"
SERVICE_SCRIPTS["beat"]="$SERVICES_DIR/celery_beat.sh"
SERVICE_SCRIPTS["flower"]="$SERVICES_DIR/flower_monitor.sh"

declare -A SERVICE_PIDS
SERVICE_PIDS["web"]="$PID_DIR/gunicorn.pid"
SERVICE_PIDS["worker"]="$PID_DIR/celery_worker.pid"
SERVICE_PIDS["beat"]="$PID_DIR/celery_beat.pid"
SERVICE_PIDS["flower"]="$PID_DIR/flower.pid"

declare -A SERVICE_LOGS
SERVICE_LOGS["web"]="$LOG_DIR/gunicorn_access.log $LOG_DIR/gunicorn_error.log"
SERVICE_LOGS["worker"]="$LOG_DIR/celery_worker.log"
SERVICE_LOGS["beat"]="$LOG_DIR/celery_beat.log"
SERVICE_LOGS["flower"]="$LOG_DIR/flower_monitor.log"

declare -A SERVICE_NAMES
SERVICE_NAMES["web"]="Gunicorn Web Server"
SERVICE_NAMES["worker"]="Celery Worker"
SERVICE_NAMES["beat"]="Celery Beat Scheduler"
SERVICE_NAMES["flower"]="Flower Monitor"

# All available services
ALL_SERVICES=("web" "worker" "beat" "flower")

# Function to display usage information
show_usage() {
    echo -e "${BLUE}SWARM Service Manager${NC}"
    echo "Controls all services for the SWARM multi-agent platform"
    echo ""
    echo -e "${YELLOW}Usage:${NC} $0 [command] [service...]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo "  start    - Start services"
    echo "  stop     - Stop services"
    echo "  restart  - Restart services"
    echo "  status   - Show service status"
    echo "  logs     - View service logs"
    echo ""
    echo -e "${YELLOW}Services:${NC}"
    echo "  web      - Gunicorn web server (Flask application)"
    echo "  worker   - Celery worker for background tasks"
    echo "  beat     - Celery beat scheduler for periodic tasks"
    echo "  flower   - Flower monitoring interface"
    echo "  all      - All services (default if none specified)"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 start           # Start all services"
    echo "  $0 start web worker # Start only web and worker services"
    echo "  $0 stop            # Stop all services"
    echo "  $0 restart worker  # Restart only the worker service"
    echo "  $0 status          # Show status of all services"
    echo "  $0 logs web        # View logs for the web service"
}

# Function to check if a service is running
is_service_running() {
    local service=$1
    local pid_file=${SERVICE_PIDS[$service]}
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # Service is running
        else
            # PID file exists but process is not running
            rm -f "$pid_file"
        fi
    fi
    
    return 1  # Service is not running
}

# Function to start a service
start_service() {
    local service=$1
    local service_name=${SERVICE_NAMES[$service]}
    local service_script=${SERVICE_SCRIPTS[$service]}
    local pid_file=${SERVICE_PIDS[$service]}
    
    echo -e "${BLUE}Starting ${service_name}...${NC}"
    
    if is_service_running "$service"; then
        echo -e "${YELLOW}${service_name} is already running.${NC}"
        return 0
    fi
    
    if [ ! -f "$service_script" ]; then
        echo -e "${RED}Error: Service script not found: $service_script${NC}"
        return 1
    fi
    
    # Make the script executable if it's not already
    chmod +x "$service_script"
    
    # Start the service
    "$service_script" &
    
    # Wait a moment for the service to start
    sleep 2
    
    # Check if the service started successfully
    if is_service_running "$service"; then
        echo -e "${GREEN}${service_name} started successfully.${NC}"
        return 0
    else
        echo -e "${RED}Failed to start ${service_name}.${NC}"
        return 1
    fi
}

# Function to stop a service
stop_service() {
    local service=$1
    local service_name=${SERVICE_NAMES[$service]}
    local pid_file=${SERVICE_PIDS[$service]}
    
    echo -e "${BLUE}Stopping ${service_name}...${NC}"
    
    if ! is_service_running "$service"; then
        echo -e "${YELLOW}${service_name} is not running.${NC}"
        return 0
    fi
    
    local pid=$(cat "$pid_file")
    
    # Send SIGTERM to the process
    kill -15 "$pid" 2>/dev/null
    
    # Wait for the process to terminate
    local timeout=30
    local counter=0
    while [ $counter -lt $timeout ] && kill -0 "$pid" 2>/dev/null; do
        echo -n "."
        sleep 1
        counter=$((counter + 1))
    done
    echo ""
    
    # If the process is still running, send SIGKILL
    if kill -0 "$pid" 2>/dev/null; then
        echo -e "${YELLOW}Force stopping ${service_name}...${NC}"
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi
    
    # Remove the PID file
    rm -f "$pid_file"
    
    echo -e "${GREEN}${service_name} stopped.${NC}"
    return 0
}

# Function to restart a service
restart_service() {
    local service=$1
    local service_name=${SERVICE_NAMES[$service]}
    
    echo -e "${BLUE}Restarting ${service_name}...${NC}"
    
    stop_service "$service"
    sleep 2
    start_service "$service"
}

# Function to show service status
show_service_status() {
    local service=$1
    local service_name=${SERVICE_NAMES[$service]}
    local pid_file=${SERVICE_PIDS[$service]}
    
    if is_service_running "$service"; then
        local pid=$(cat "$pid_file")
        local uptime=$(ps -o etime= -p "$pid")
        echo -e "${GREEN}● ${service_name} (PID: $pid) is ${GREEN}running${NC} - uptime: $uptime${NC}"
    else
        echo -e "${RED}○ ${service_name} is ${RED}stopped${NC}${NC}"
    fi
}

# Function to show service logs
show_service_logs() {
    local service=$1
    local service_name=${SERVICE_NAMES[$service]}
    local logs=${SERVICE_LOGS[$service]}
    
    echo -e "${BLUE}Showing logs for ${service_name}...${NC}"
    
    if [ -z "$logs" ]; then
        echo -e "${RED}No log files defined for ${service_name}.${NC}"
        return 1
    fi
    
    for log_file in $logs; do
        if [ -f "$log_file" ]; then
            echo -e "${PURPLE}=== $log_file ===${NC}"
            tail -n 50 "$log_file"
            echo ""
        else
            echo -e "${YELLOW}Log file not found: $log_file${NC}"
        fi
    done
}

# Function to process command for all services
process_all_services() {
    local command=$1
    local success=true
    
    for service in "${ALL_SERVICES[@]}"; do
        case "$command" in
            start)
                start_service "$service" || success=false
                ;;
            stop)
                stop_service "$service" || success=false
                ;;
            restart)
                restart_service "$service" || success=false
                ;;
            status)
                show_service_status "$service"
                ;;
            logs)
                show_service_logs "$service"
                ;;
            *)
                echo -e "${RED}Error: Unknown command: $command${NC}"
                show_usage
                return 1
                ;;
        esac
    done
    
    if [ "$success" = false ]; then
        return 1
    fi
    
    return 0
}

# Function to process command for specific services
process_services() {
    local command=$1
    shift
    local services=("$@")
    local success=true
    
    for service in "${services[@]}"; do
        if [[ "$service" == "all" ]]; then
            process_all_services "$command" || success=false
            continue
        fi
        
        # Check if the service is valid
        if [[ ! " ${ALL_SERVICES[*]} " =~ " ${service} " ]]; then
            echo -e "${RED}Error: Unknown service: $service${NC}"
            echo -e "${YELLOW}Available services: ${ALL_SERVICES[*]}${NC}"
            success=false
            continue
        fi
        
        case "$command" in
            start)
                start_service "$service" || success=false
                ;;
            stop)
                stop_service "$service" || success=false
                ;;
            restart)
                restart_service "$service" || success=false
                ;;
            status)
                show_service_status "$service"
                ;;
            logs)
                show_service_logs "$service"
                ;;
            *)
                echo -e "${RED}Error: Unknown command: $command${NC}"
                show_usage
                return 1
                ;;
        esac
    done
    
    if [ "$success" = false ]; then
        return 1
    fi
    
    return 0
}

# Main script execution

# Check if a command was provided
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

# Get the command
COMMAND=$1
shift

# If no services were specified, use all services
if [ $# -eq 0 ]; then
    process_all_services "$COMMAND"
    exit $?
fi

# Process the specified services
process_services "$COMMAND" "$@"
exit $?
