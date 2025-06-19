#!/bin/bash
# Production Deployment Script for Swarm MCP Project

set -e

echo "🚀 Starting Swarm MCP Production Deployment..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your production values"
    exit 1
fi

# Verify required environment variables
required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "SECRET_KEY"
    "OPENROUTER_API_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Missing required environment variable: $var"
        exit 1
    fi
done

# Build and start services
echo "📦 Building Docker containers..."
docker-compose build

echo "🗄️ Starting database..."
docker-compose up -d postgres redis

# Wait for postgres to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10

echo "🔧 Running database migrations..."
docker-compose run --rm app python init/init_database.py

echo "🚀 Starting all services..."
docker-compose up -d

echo "✅ Deployment complete!"
echo "📱 Application: http://localhost:8000"
echo "🔧 Nginx Proxy: http://localhost:80"
echo "📊 Health Check: http://localhost:8000/health"

# Show running containers
echo -e "\n📦 Running containers:"
docker-compose ps