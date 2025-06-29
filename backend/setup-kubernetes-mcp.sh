#!/bin/bash

# Setup script for Kubernetes MCP Server

echo "Setting up Kubernetes MCP Server..."

# Option 1: Use pnpm package (recommended)
echo "Option 1: Installing via pnpm..."
pnpm add kubernetes-mcp-server

# Option 2: Clone from GitHub (alternative)
# echo "Option 2: Cloning from GitHub..."
# if [ ! -d "kubernetes-mcp-server" ]; then
#     git clone https://github.com/manusa/kubernetes-mcp-server.git
#     cd kubernetes-mcp-server
#     pnpm install
#     pnpm run build
#     cd ..
# fi

echo "Setup complete!"
echo ""
echo "To start the server, run:"
echo "  pnpm exec kubernetes-mcp-server --port 8080"
echo ""
echo "Or use the start script:"
echo "  ./start-kubernetes-mcp-server.sh"