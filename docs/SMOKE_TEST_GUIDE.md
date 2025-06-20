# Smoke Test Guide

## Overview

This document describes the smoke test implementation for the MCP Executive Platform. The smoke tests are designed to catch regressions early by testing basic functionality in a containerized environment.

## What are Smoke Tests?

Smoke tests are a subset of test cases that cover the most important functionality of an application. They are designed to:

- Verify that the application starts correctly
- Test basic functionality without going into details
- Catch major regressions quickly
- Provide rapid feedback during development

## Implementation

We have implemented smoke tests in two ways:

### 1. GitHub Actions Workflow (`.github/workflows/smoke-test.yml`)

Automatically runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Manual trigger via GitHub Actions UI

### 2. Local Script (`scripts/smoke-test.sh`)

Can be run locally for testing before pushing changes.

## Test Scenarios

The smoke tests cover the following scenarios:

### 1. Docker Image Build
- **Test**: Build the Docker image using the production Dockerfile
- **Success Criteria**: Image builds without errors
- **Failure**: Non-zero exit code from `docker build`

### 2. Container Startup
- **Test**: Start container with production-like configuration
- **Success Criteria**: Container starts and passes health checks
- **Failure**: Container fails to start or health checks fail

### 3. Readiness Endpoint (`/api/monitoring/ready`)
- **Test**: HTTP GET request to readiness endpoint
- **Success Criteria**: Returns HTTP 200 or 503 with valid JSON
- **Failure**: Non-200/503 status code or invalid response

### 4. Simple Health Endpoint (`/api/monitoring/simple-health`)
- **Test**: HTTP GET request to simple health endpoint
- **Success Criteria**: Returns HTTP 200 with `{"status": "healthy"}`
- **Failure**: Non-200 status code or unexpected response content

### 5. Basic API Functionality (`/api/monitoring/metrics`)
- **Test**: HTTP GET request to metrics endpoint
- **Success Criteria**: Returns HTTP 200 with `{"status": "success"}`
- **Failure**: Non-200 status code or unexpected response content

### 6. Container Resource Check
- **Test**: Verify container is still running and responsive
- **Success Criteria**: Container is running and consuming reasonable resources
- **Failure**: Container stopped unexpectedly or excessive resource usage

## Configuration

### Environment Variables

The smoke tests use the following environment variables:

```bash
FLASK_ENV=production
DATABASE_URL=sqlite:///test.db
REDIS_URL=redis://localhost:6379
ENABLE_CELERY=false
SECRET_KEY=test-secret-key-for-ci
PORT=10000
```

### Docker Configuration

- **Image**: Built from `deployment/Dockerfile`
- **Port**: 10000 (mapped to host)
- **Health Check**: Curl to `/api/monitoring/simple-health`
- **Build Args**: `INSTALL_DEV=false` for production-like build

## Running Smoke Tests

### GitHub Actions (Automatic)

Smoke tests run automatically on push/PR. View results in the GitHub Actions tab.

### Local Testing

Run the local smoke test script:

```bash
# From project root directory
./scripts/smoke-test.sh
```

Requirements:
- Docker installed and running
- `curl` command available
- `jq` command available (optional, for pretty JSON output)

## Test Output

### Success Output

```
[INFO] Starting smoke test for MCP Executive Platform...
[INFO] Building Docker image...
[SUCCESS] Docker image built successfully
[INFO] Starting container...
[SUCCESS] Container started
[INFO] Waiting for container to be healthy...
[SUCCESS] Container is healthy
[INFO] Testing /ready endpoint...
[SUCCESS] Readiness endpoint responded correctly
[INFO] Testing /simple-health endpoint...
[SUCCESS] Simple health endpoint is working correctly
[INFO] Testing basic API functionality...
[SUCCESS] Basic API endpoint is working correctly
[INFO] Checking container resource usage...
[SUCCESS] Container is still running after tests
[SUCCESS] All smoke tests passed! 🎉
```

### Failure Output

The tests will exit with a non-zero code and show detailed error information including:
- Container logs
- HTTP response details
- Docker system information

## Troubleshooting

### Common Issues

1. **Docker not running**
   ```
   [ERROR] Docker is not running. Please start Docker and try again.
   ```
   Solution: Start Docker Desktop or Docker daemon

2. **Port already in use**
   ```
   Error response from daemon: port is already allocated
   ```
   Solution: Stop other containers using port 10000 or change TEST_PORT

3. **Container fails health check**
   ```
   [ERROR] Container is unhealthy
   ```
   Solution: Check container logs for application startup errors

4. **Endpoint returns unexpected status**
   ```
   [ERROR] Readiness endpoint failed with status: 500
   ```
   Solution: Check application configuration and dependencies

### Debugging Steps

1. **Check container logs**:
   ```bash
   docker logs mcp-test-container
   ```

2. **Test endpoints manually**:
   ```bash
   curl http://localhost:10000/api/monitoring/simple-health
   ```

3. **Check container status**:
   ```bash
   docker ps -a
   docker inspect mcp-test-container
   ```

## Integration with CI/CD

### Regression Detection

The smoke tests will fail the CI build if:
- Docker image cannot be built
- Application fails to start
- Critical endpoints return errors
- Container crashes during testing

### Build Status

- ✅ **Pass**: All tests passed, safe to deploy
- ❌ **Fail**: Critical issues detected, do not deploy
- ⚠️ **Warning**: Tests passed but with degraded performance

## Extending Smoke Tests

To add new smoke test scenarios:

1. **GitHub Actions**: Add new step to `.github/workflows/smoke-test.yml`
2. **Local Script**: Add new test section to `scripts/smoke-test.sh`
3. **Documentation**: Update this guide with new test details

### Example: Adding New Endpoint Test

```bash
# Test new endpoint
log_info "Testing new endpoint..."
response=$(curl -s -w "%{http_code}" -o /tmp/new_response.json \
    "http://localhost:$TEST_PORT/api/new-endpoint")

if [ "$response" = "200" ]; then
    log_success "New endpoint is working correctly"
else
    log_error "New endpoint failed with status: $response"
    exit 1
fi
```

## Best Practices

### Test Design
- Keep tests simple and fast
- Test critical paths only
- Use realistic but minimal data
- Avoid external dependencies when possible

### Maintenance
- Update tests when API changes occur
- Keep test data minimal and predictable
- Regular review of test coverage
- Monitor test execution time

### Security
- Use test-specific secrets/keys
- Avoid real credentials in test configuration
- Clean up test data after runs
- Isolated test environment

## Related Documentation

- [Deployment Guide](../deployment/DEPLOYMENT_GUIDE.md)
- [Monitoring Guide](../docs/observability_guide.md)
- [API Documentation](../docs/API_DOCUMENTATION.md)
- [Docker Configuration](../deployment/DOCKERFILE_HARDENING.md)

