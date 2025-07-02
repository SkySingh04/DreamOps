#!/bin/bash

echo "🚀 Enabling YOLO Mode for Oncall Agent"
echo "======================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Creating from .env.example..."
    cp .env.example .env
fi

# Function to update or add an environment variable
update_env() {
    local key=$1
    local value=$2
    
    if grep -q "^${key}=" .env; then
        # Update existing key
        sed -i.bak "s/^${key}=.*/${key}=${value}/" .env
        echo "✅ Updated ${key}=${value}"
    else
        # Add new key
        echo "${key}=${value}" >> .env
        echo "✅ Added ${key}=${value}"
    fi
}

# Enable destructive operations (required for YOLO mode)
update_env "K8S_ENABLE_DESTRUCTIVE_OPERATIONS" "true"

# Ensure Kubernetes is enabled
update_env "K8S_ENABLED" "true"

# Optional: Set log level to DEBUG for better visibility
read -p "Enable DEBUG logging? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    update_env "LOG_LEVEL" "DEBUG"
fi

echo ""
echo "✅ YOLO Mode configuration complete!"
echo ""
echo "IMPORTANT: YOLO Mode Requirements"
echo "================================="
echo "1. ✅ K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true (now set)"
echo "2. ✅ K8S_ENABLED=true (now set)"
echo "3. 📋 In the frontend, set AI Mode to 'YOLO'"
echo "4. 🔑 Ensure ANTHROPIC_API_KEY is set in .env"
echo "5. 🎯 Kubernetes cluster must be accessible"
echo ""
echo "To verify configuration:"
echo "  grep -E 'K8S_ENABLE_DESTRUCTIVE_OPERATIONS|K8S_ENABLED' .env"
echo ""
echo "To start the API server with YOLO mode support:"
echo "  uv run python api_server.py"
echo ""