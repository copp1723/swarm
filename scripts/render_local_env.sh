#!/bin/bash
# Minimal environment variables to replicate Render deployment
# This script exports the basic environment variables that Render injects

# Flask/Application environment
export FLASK_ENV=production
export NODE_ENV=production
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Port (Render assigns this dynamically, using 10000 as default)
export PORT=10000

# Database URL (using local SQLite for testing, but Render would use PostgreSQL)
export DATABASE_URL=sqlite:///instance/mcp_executive.db

# Redis URL (using local Redis or fallback)
export REDIS_URL=redis://localhost:6379/0

# Security keys (using placeholder values for local testing)
export SECRET_KEY=render-local-test-secret-key-12345
export JWT_SECRET_KEY=render-local-jwt-secret-key-67890

# Disable MCP filesystem server (as Render does)
export DISABLE_MCP_FILESYSTEM=true

# Log level
export LOG_LEVEL=INFO

# Create .render.env file for docker run
cat > .render.env << EOF
FLASK_ENV=production
NODE_ENV=production
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
PORT=10000
DATABASE_URL=sqlite:///instance/mcp_executive.db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=render-local-test-secret-key-12345
JWT_SECRET_KEY=render-local-jwt-secret-key-67890
DISABLE_MCP_FILESYSTEM=true
LOG_LEVEL=INFO
EOF

echo "Environment variables exported for Render local testing"
echo "Created .render.env file for Docker container"

