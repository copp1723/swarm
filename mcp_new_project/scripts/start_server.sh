#!/bin/bash
# Start script with better error handling and logging

cd /Users/copp1723/Desktop/swarm/mcp_new_project

# Kill any existing processes on port 5006
lsof -ti:5006 | xargs kill -9 2>/dev/null

# Export environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1
export PORT=5006

# Ensure virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create log directory
mkdir -p logs

# Start the server with proper logging
echo "Starting server on port $PORT..."
python app.py 2>&1 | tee logs/server_startup.log