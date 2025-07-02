#!/bin/bash

# Start API Server with MCP Server

echo "Starting DreamOps API Server with Kubernetes MCP Server..."

# Load environment variables
source .env 2>/dev/null || true

# The API server will automatically start the MCP server if K8S_USE_MCP_SERVER=true
echo "Starting API server (MCP server will start automatically if enabled)..."
uv run python api_server.py