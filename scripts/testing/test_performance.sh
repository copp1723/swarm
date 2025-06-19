#!/bin/bash
# Quick performance test script

echo "🚀 Testing SWARM Performance Optimizations"
echo "=========================================="

# Start the server in background
echo "📡 Starting server..."
python run_production.py production &
SERVER_PID=$!

# Wait for server to start
sleep 3

# Test endpoints
echo "🔍 Testing health endpoint..."
curl -s "http://localhost:5006/health" | python -m json.tool

echo -e "\n⚡ Testing async performance endpoint..."
curl -s "http://localhost:5006/api/async-demo/performance-test" | python -m json.tool

echo -e "\n🔄 Testing bulk operations..."
curl -s "http://localhost:5006/api/async-demo/bulk-operations" | python -m json.tool

# Cleanup
echo -e "\n🛑 Stopping server..."
kill $SERVER_PID

echo "✅ Performance test complete!"