#!/bin/bash

# Quick test script for PagerDuty integration without Kubernetes

echo "🚀 Quick PagerDuty Integration Test"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from simple template..."
    cp .env.simple .env
    echo "⚠️  Please edit .env and add your ANTHROPIC_API_KEY"
    echo "   Then run this script again."
    exit 1
fi

# Check if ANTHROPIC_API_KEY is set
if grep -q "ANTHROPIC_API_KEY=your-api-key-here" .env; then
    echo "❌ Please add your ANTHROPIC_API_KEY to .env file"
    echo "   Edit .env and replace 'your-api-key-here' with your actual key"
    exit 1
fi

echo "✅ Configuration looks good!"
echo ""
echo "📦 Installing dependencies..."
uv sync

echo ""
echo "🚀 Starting API server in background..."
# Kill any existing API server
pkill -f "python api_server.py" 2>/dev/null || true

# Start API server in background
nohup uv run python api_server.py > api_server.log 2>&1 &
API_PID=$!
echo "   API server PID: $API_PID"

# Wait for API to start
echo "⏳ Waiting for API server to start..."
sleep 5

# Check if API is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ API server failed to start. Check api_server.log for errors"
    exit 1
fi

echo "✅ API server is running!"
echo ""
echo "🧪 Sending test alerts..."
echo ""

# Send a variety of test alerts
echo "1️⃣ Testing database alert..."
uv run python test_pagerduty_alerts.py --type database

echo ""
echo "2️⃣ Testing server alert..."
uv run python test_pagerduty_alerts.py --type server

echo ""
echo "3️⃣ Testing security alert..."
uv run python test_pagerduty_alerts.py --type security

echo ""
echo "✅ Test complete!"
echo ""
echo "📊 Summary:"
echo "   - API server is running on http://localhost:8000"
echo "   - API logs are in api_server.log"
echo "   - You can send more test alerts with:"
echo "     uv run python test_pagerduty_alerts.py --all"
echo ""
echo "🛑 To stop the API server:"
echo "   kill $API_PID"
echo ""
echo "📚 For more testing options, see:"
echo "   python test_pagerduty_alerts.py --help"