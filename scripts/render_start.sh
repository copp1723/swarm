#!/bin/bash
set -e

echo "Starting MCP Executive on Render..."

# Ensure PORT is set (Render will set this)
export PORT=${PORT:-10000}

echo "Port: $PORT"
echo "Environment: ${FLASK_ENV:-production}"

# Show environment info
echo "Python version: $(python --version)"
echo "Current working directory: $(pwd)"

# Ensure required directories exist
mkdir -p logs uploads instance

# Run database migrations if needed (only if DATABASE_URL is available)
if [ ! -z "$DATABASE_URL" ]; then
    echo "Running database initialization..."
    python -c "
from app import app
from utils.db_init import initialize_databases
with app.app_context():
    try:
        initialize_databases(app)
        print('Database initialization completed')
    except Exception as e:
        print(f'Database initialization failed: {e}')
        print('Continuing without database...')
" || true
fi

# Start the application with gunicorn
echo "Starting gunicorn with SocketIO support..."
exec gunicorn -c gunicorn.conf.py wsgi:application

