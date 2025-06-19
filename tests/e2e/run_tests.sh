#!/bin/bash

# Script to run end-to-end tests with proper setup

echo "🧪 Running End-to-End Tests for Webhook Flow"
echo "==========================================="

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Please start Redis first:"
    echo "   brew services start redis  # macOS"
    echo "   sudo systemctl start redis # Linux"
    exit 1
fi

# Set test environment
export FLASK_ENV=testing
export TESTING=1

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -r requirements-test.txt

# Run linting
echo "🔍 Running code quality checks..."
flake8 services tasks --max-line-length=100 --ignore=E203,W503

# Run type checking
echo "🔍 Running type checks..."
mypy services tasks --ignore-missing-imports

# Clear test Redis database
echo "🗑️  Clearing test Redis database..."
redis-cli -n 15 FLUSHDB

# Run tests with coverage
echo "🧪 Running tests..."
pytest tests/e2e \
    -v \
    --cov=services \
    --cov=tasks \
    --cov=schemas \
    --cov-report=term-missing \
    --cov-report=html \
    --tb=short \
    -x

# Check test results
if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    echo "📊 Coverage report generated in htmlcov/index.html"
    
    # Optional: Open coverage report
    if command -v open > /dev/null; then
        read -p "Open coverage report in browser? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            open htmlcov/index.html
        fi
    fi
else
    echo "❌ Some tests failed. Please check the output above."
    exit 1
fi

# Run specific test suites
echo ""
echo "🔧 Additional test commands:"
echo "  Run webhook tests:    pytest tests/e2e/test_webhook_flow.py -v"
echo "  Run routing tests:    pytest tests/e2e/test_routing_behaviors.py -v"
echo "  Run Convoy tests:     pytest tests/e2e/test_convoy_integration.py -v"
echo "  Run integration only: pytest tests/e2e -m integration"
echo "  Run with parallel:    pytest tests/e2e -n auto"