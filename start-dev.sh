#!/bin/bash

# Start development servers for oncall-agent

echo "🚀 Starting Oncall Agent Development Servers..."

# Start backend in a new terminal
echo "📦 Starting Backend API Server on http://localhost:8000"
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "cd backend && uv run uvicorn api_server:app --reload --host 0.0.0.0 --port 8000; exec bash"
elif command -v xterm &> /dev/null; then
    xterm -e "cd backend && uv run uvicorn api_server:app --reload --host 0.0.0.0 --port 8000; bash" &
else
    echo "Starting backend in background..."
    cd backend && uv run uvicorn api_server:app --reload --host 0.0.0.0 --port 8000 &
    cd ..
fi

# Give backend a moment to start
sleep 3

# Start frontend
echo "🎨 Starting Frontend Dev Server on http://localhost:3000"
cd frontend && npm run dev

echo "✅ Development servers started!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"