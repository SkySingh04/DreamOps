#!/bin/bash

# Start the Kubernetes MCP Server

echo "Starting Kubernetes MCP Server (manusa/kubernetes-mcp-server)..."

# Get the port from environment or use default
PORT="${K8S_MCP_SERVER_PORT:-8080}"

# Install dependencies if needed
if [ ! -d "node_modules/kubernetes-mcp-server" ]; then
    echo "Installing kubernetes-mcp-server..."
    pnpm install
fi

# Start the server
echo "Starting server on port $PORT..."
pnpm exec kubernetes-mcp-server --http-port "$PORT"