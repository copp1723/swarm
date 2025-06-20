#!/bin/bash
set -e

echo "🚀 Starting MCP Executive on Render..."

# Set environment variables
export PORT=${PORT:-10000}
export FLASK_ENV=${FLASK_ENV:-production}
export WEB_CONCURRENCY=${WEB_CONCURRENCY:-2}

# Run database migrations
if [ ! -z "$DATABASE_URL" ]; then
    echo "🔧 Running database migrations..."
    flask db upgrade
fi

# Start Gunicorn
echo "🚀 Starting Gunicorn..."
exec gunicorn --config gunicorn.conf.py wsgi:application

