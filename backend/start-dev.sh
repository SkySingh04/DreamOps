#!/bin/bash
# Development startup script

# Set environment variables explicitly
export NODE_ENV=development
export ENVIRONMENT=development

# Force load .env.local by setting NODE_ENV before Python starts
echo "Starting DreamOps API server in development mode..."
echo "NODE_ENV=$NODE_ENV"
echo "ENVIRONMENT=$ENVIRONMENT"

# Start the API server
NODE_ENV=development ENVIRONMENT=development uv run python api_server.py