#!/bin/bash
# Quick setup script for Mailgun webhook testing

echo "🚀 Mailgun Local Testing Setup"
echo "=============================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Creating from .env.production..."
    cp .env.production .env
    echo "⚠️  Please edit .env with your Mailgun credentials"
    exit 1
fi

# Check for required env vars
source .env
if [ -z "$MAILGUN_SIGNING_KEY" ]; then
    echo "❌ MAILGUN_SIGNING_KEY not set in .env"
    echo "Get it from: Mailgun Dashboard → Settings → Webhooks → HTTP webhook signing key"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install icalendar pytz

# Start the application
echo "🔧 Starting application..."
./deploy-production.sh &
APP_PID=$!

# Wait for app to start
echo "⏳ Waiting for application to start..."
sleep 10

# Check if app is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Application failed to start"
    kill $APP_PID 2>/dev/null
    exit 1
fi

echo "✅ Application running on http://localhost:8000"

# Instructions for ngrok
echo ""
echo "📡 Next steps:"
echo "1. Install ngrok: brew install ngrok (macOS) or https://ngrok.com"
echo "2. In a new terminal, run: ngrok http 8000"
echo "3. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)"
echo "4. Update Mailgun route with webhook URL:"
echo "   https://YOUR-NGROK-ID.ngrok.io/api/email-agent/webhooks/mailgun"
echo ""
echo "5. Test the webhook:"
echo "   python test-mailgun-webhook.py"
echo ""
echo "6. Send test email to: mailagent@onerylie.com"
echo ""
echo "Press Ctrl+C to stop the application"

# Keep script running
wait $APP_PID