#!/bin/bash

echo "Starting MCP Agent Server..."
echo "=========================="

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start the Flask server
echo "Starting Flask application..."
python app.py

# Note: If you need to run background services, uncomment these:
# echo "Starting Celery worker in background..."
# celery -A tasks.celery_app worker --loglevel=info &
# 
# echo "Starting Redis server..."
# redis-server &