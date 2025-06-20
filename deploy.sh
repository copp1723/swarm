#!/bin/bash

# Multi-Agent Workspace Deployment Script
# =======================================

echo "🚀 Deploying Multi-Agent Workspace..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    exit 1
fi

print_header "Multi-Agent Workspace Deployment"
echo "========================================"

# Install dependencies
print_status "Installing Python dependencies..."
if [ -f "config/requirements/requirements.txt" ]; then
    pip install -r config/requirements/requirements.txt --quiet
    print_status "Dependencies installed successfully"
else
    print_warning "requirements.txt not found, attempting to install basic dependencies..."
    pip install flask flask-cors --quiet
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p instance
mkdir -p uploads
mkdir -p data
mkdir -p logs

# Set permissions
chmod 755 instance uploads data logs

# Check for port availability
PORT=${PORT:-8000}
if lsof -i :$PORT > /dev/null 2>&1; then
    print_warning "Port $PORT is in use. Trying port $((PORT + 1))..."
    PORT=$((PORT + 1))
fi

# Detect which server to use
if [ -f "working_server.py" ]; then
    SERVER_FILE="working_server.py"
    print_status "Using enhanced working server"
elif [ -f "demo_server.py" ]; then
    SERVER_FILE="demo_server.py"
    print_status "Using demo server"
else
    print_error "No server file found!"
    exit 1
fi

# Start the server
print_status "Starting server on port $PORT..."
export PORT=$PORT

# Create a simple process manager
cat > start_server.sh << EOF
#!/bin/bash
echo "Starting Multi-Agent Workspace Server..."
echo "Port: $PORT"
echo "Server: $SERVER_FILE"
echo "Time: \$(date)"
echo "========================================"

python $SERVER_FILE
EOF

chmod +x start_server.sh

# Start server in background
python $SERVER_FILE > server.log 2>&1 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Test if server is running
if curl -s "http://localhost:$PORT/health" > /dev/null; then
    print_status "✅ Server is running successfully!"
    echo ""
    echo "========================================"
    echo "🎉 DEPLOYMENT SUCCESSFUL!"
    echo "========================================"
    echo ""
    echo "📱 Frontend URL: http://localhost:$PORT"
    echo "🔗 API Status:   http://localhost:$PORT/api/agents/profiles"
    echo "💾 Server PID:   $SERVER_PID"
    echo ""
    echo "Features Available:"
    echo "• 🤖 Multi-agent chat interface"
    echo "• 🔄 Drag-and-drop agent workspace"
    echo "• 📝 @ mention autocomplete"
    echo "• ⌨️  Keyboard shortcuts (Ctrl+1-9 for agent switching)"
    echo "• 🌙 Dark mode toggle"
    echo "• 📱 Mobile responsive design"
    echo "• 🔧 Fallback support when backend is unavailable"
    echo ""
    echo "Keyboard Shortcuts:"
    echo "• Ctrl/Cmd + 1-9: Switch between agents"
    echo "• Ctrl/Cmd + K:   Focus current agent input"
    echo "• Esc:            Close modals"
    echo ""
    echo "To stop the server: kill $SERVER_PID"
    echo "Log file: server.log"
    echo ""
else
    print_error "❌ Server failed to start properly"
    print_error "Check server.log for details"
    exit 1
fi

