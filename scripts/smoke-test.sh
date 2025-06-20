#!/bin/bash

# Local smoke test script for MCP Executive Platform
# This script mimics the GitHub Action workflow for local testing

set -e  # Exit on any error

# Configuration
DOCKER_IMAGE="mcp-executive"
CONTAINER_NAME="mcp-test-container"
TEST_PORT="10000"
DOCKERFILE_PATH="deployment/Dockerfile"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    
    # Show container logs for debugging
    if docker ps -a | grep -q "$CONTAINER_NAME"; then
        log_info "Container logs:"
        docker logs "$CONTAINER_NAME" || true
    fi
    
    # Stop and remove container
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    # Remove image
    docker rmi "$DOCKER_IMAGE:test" 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "$DOCKERFILE_PATH" ]; then
    log_error "Dockerfile not found at $DOCKERFILE_PATH"
    log_error "Please run this script from the project root directory"
    exit 1
fi

log_info "Starting smoke test for MCP Executive Platform..."

# Step 1: Build Docker image
log_info "Building Docker image..."
docker build \
    --file "$DOCKERFILE_PATH" \
    --tag "$DOCKER_IMAGE:test" \
    --build-arg INSTALL_DEV=false \
    .
log_success "Docker image built successfully"

# Step 2: Start container
log_info "Starting container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    --publish "$TEST_PORT:10000" \
    --env FLASK_ENV=production \
    --env DATABASE_URL=sqlite:///test.db \
    --env REDIS_URL=redis://localhost:6379 \
    --env ENABLE_CELERY=false \
    --env SECRET_KEY=test-secret-key-for-local \
    --env PORT=10000 \
    --health-cmd="curl -f http://localhost:10000/api/monitoring/simple-health || exit 1" \
    --health-interval=10s \
    --health-timeout=5s \
    --health-retries=3 \
    --health-start-period=30s \
    "$DOCKER_IMAGE:test"
log_success "Container started"

# Step 3: Wait for container to be healthy
log_info "Waiting for container to be healthy..."
timeout=180  # 3 minutes timeout
interval=5
elapsed=0

while [ $elapsed -lt $timeout ]; do
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_NAME")
    log_info "Container health status: $health_status (${elapsed}s elapsed)"
    
    if [ "$health_status" = "healthy" ]; then
        log_success "Container is healthy"
        break
    elif [ "$health_status" = "unhealthy" ]; then
        log_error "Container is unhealthy"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
    
    sleep $interval
    elapsed=$((elapsed + interval))
done

if [ $elapsed -ge $timeout ]; then
    log_error "Timeout waiting for container to be healthy"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

# Step 4: Test readiness endpoint
log_info "Testing /ready endpoint..."
response=$(curl -s -w "%{http_code}" -o /tmp/ready_response.json \
    "http://localhost:$TEST_PORT/api/monitoring/ready")

log_info "Response status: $response"
log_info "Response body:"
cat /tmp/ready_response.json | jq '.' 2>/dev/null || cat /tmp/ready_response.json

# Check if the status code is 200 or 503 (both are acceptable for readiness)
if [ "$response" = "200" ] || [ "$response" = "503" ]; then
    log_success "Readiness endpoint responded correctly"
else
    log_error "Readiness endpoint failed with status: $response"
    exit 1
fi

# Step 5: Test simple health endpoint
log_info "Testing /simple-health endpoint..."
response=$(curl -s -w "%{http_code}" -o /tmp/health_response.json \
    "http://localhost:$TEST_PORT/api/monitoring/simple-health")

log_info "Response status: $response"
log_info "Response body:"
cat /tmp/health_response.json | jq '.' 2>/dev/null || cat /tmp/health_response.json

if [ "$response" = "200" ]; then
    # Verify the response contains expected fields
    status=$(cat /tmp/health_response.json | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$status" = "healthy" ]; then
        log_success "Simple health endpoint is working correctly"
    else
        log_error "Health endpoint returned unexpected status: $status"
        exit 1
    fi
else
    log_error "Simple health endpoint failed with status: $response"
    exit 1
fi

# Step 6: Test basic API endpoint
log_info "Testing basic API functionality..."
response=$(curl -s -w "%{http_code}" -o /tmp/metrics_response.json \
    "http://localhost:$TEST_PORT/api/monitoring/metrics")

log_info "Response status: $response"
log_info "Response body:"
cat /tmp/metrics_response.json | jq '.' 2>/dev/null || cat /tmp/metrics_response.json

if [ "$response" = "200" ]; then
    # Verify the response contains expected fields
    status=$(cat /tmp/metrics_response.json | jq -r '.status' 2>/dev/null || echo "unknown")
    if [ "$status" = "success" ]; then
        log_success "Basic API endpoint is working correctly"
    else
        log_error "API endpoint returned unexpected status: $status"
        exit 1
    fi
else
    log_error "Basic API endpoint failed with status: $response"
    exit 1
fi

# Step 7: Test container resource usage
log_info "Checking container resource usage..."
docker stats "$CONTAINER_NAME" --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check if container is still running
if docker ps | grep -q "$CONTAINER_NAME"; then
    log_success "Container is still running after tests"
else
    log_error "Container stopped unexpectedly"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

# Final success message
log_success "All smoke tests passed! 🎉"
log_info "The MCP Executive Platform is working correctly"

# Clean up temp files
rm -f /tmp/ready_response.json /tmp/health_response.json /tmp/metrics_response.json

exit 0

