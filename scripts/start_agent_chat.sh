#!/bin/bash

# Start script for MCP Agent Chat System

echo "🚀 Starting MCP Agent Chat System..."
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
echo "Checking dependencies..."
pip install -q -r requirements.txt 2>/dev/null

# Check for API key
if [ -z "$OPENROUTER_API_KEY" ] && [ -z "$OPEN_ROUTER" ]; then
    echo "⚠️  WARNING: OpenRouter API key not set!"
    echo "Set it with: export OPENROUTER_API_KEY='your_key_here'"
    echo
fi

# Start the application
echo "Starting Flask application..."
echo "Open http://localhost:5006 in your browser"
echo
python app.py