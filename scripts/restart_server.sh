#!/bin/bash

echo "Restarting MCP Agent Server..."

# Kill any existing Python processes running app.py
pkill -f "python.*app.py" 2>/dev/null || true

# Wait a moment for processes to terminate
sleep 2

# Clear browser cache reminder
echo ""
echo "Server stopped. To start again:"
echo "  python app.py"
echo ""
echo "After restarting, remember to:"
echo "1. Clear browser cache (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)"
echo "2. Or open in an incognito/private window"
echo ""
echo "The group chat improvements include:"
echo "- Full-screen takeover when mentioning agents"
echo "- Centered positioning"
echo "- Automatic collaboration start"
echo "- Better polling for agent responses"