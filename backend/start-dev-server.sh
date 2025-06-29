#!/bin/bash
# Start the API server in development mode

echo "Starting API server in development mode..."
echo "This will:"
echo "- Load .env.local configuration"
echo "- Enable all integrations (NEXT_PUBLIC_DEV_MODE=true)"
echo "- Set all new users to Pro plan"
echo "- Enable hot reload"
echo ""

# Set environment variables and start server
NODE_ENV=development NEXT_PUBLIC_DEV_MODE=true uv run python api_server.py