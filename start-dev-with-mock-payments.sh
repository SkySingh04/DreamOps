#!/bin/bash
# Development startup script with mock payments enabled

echo "🚀 Starting DreamOps Development Environment with Mock Payments"
echo "=============================================================="

# Set environment variables for mock payments
export USE_MOCK_PAYMENTS=true
export NODE_ENV=development
export NEXT_PUBLIC_USE_MOCK_PAYMENTS=true

# Start backend
echo "📡 Starting Backend API Server..."
cd backend
USE_MOCK_PAYMENTS=true NODE_ENV=development uv run python api_server.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Start frontend
echo "🌐 Starting Frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ Development environment started!"
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend API: http://localhost:8000"
echo "📍 API Health: http://localhost:8000/health"
echo "📍 Payment Debug: http://localhost:8000/api/v1/payments/debug/environment"
echo ""
echo "💳 Mock Payments are ENABLED - no real PhonePe API calls will be made"
echo "🧪 Test Payment: curl -X POST http://localhost:8000/api/v1/payments/test/mock-payment"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ All services stopped"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for processes
wait