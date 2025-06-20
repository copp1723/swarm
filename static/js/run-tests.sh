#!/bin/bash

# JavaScript Runtime Error Fixes - Test Runner
# This script installs dependencies and runs the test suite

echo "🔧 Setting up JavaScript testing environment..."

# Navigate to the js directory
cd "$(dirname "$0")"

# Install dependencies if package-lock.json doesn't exist
if [ ! -f "package-lock.json" ]; then
    echo "📦 Installing Jest and testing dependencies..."
    npm install
fi

echo "🧪 Running JavaScript unit tests..."

# Run tests with coverage
npm run test:coverage

echo ""
echo "✅ Test execution complete!"
echo ""
echo "📊 Coverage report generated in ./coverage/"
echo "🌐 Open ./coverage/lcov-report/index.html to view detailed coverage"
echo ""
echo "🚀 To run tests in watch mode: npm run test:watch"
echo "🐛 To run tests in debug mode: npm run test:debug"

