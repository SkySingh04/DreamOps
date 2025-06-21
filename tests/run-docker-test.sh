#!/bin/bash

echo "🐳 Starting Docker Integration Test for On-Call Agent"
echo "===================================================="

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create test results directory
mkdir -p test-results

echo "📁 Created test-results directory"

# Navigate to the tests directory
cd "$(dirname "$0")"

# Check if .env file exists in parent directory
if [ ! -f ../.env ]; then
    echo "❌ .env file not found in parent directory. Please create one with your API keys."
    echo "   You can copy .env.example to .env and fill in the values."
    exit 1
fi

echo "✅ Found .env file"

# Pull required images
echo ""
echo "📥 Pulling Docker images..."
docker pull nginx:alpine
docker pull python:3.11-slim

# Build and run the test
echo ""
echo "🏗️  Building and starting services..."
docker-compose -f docker-compose.test.yml build

echo ""
echo "🚀 Running integration test..."
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Check test results
if [ -f "test-results/test-summary.txt" ]; then
    echo ""
    echo "📊 Test Results:"
    echo "==============="
    cat test-results/test-summary.txt
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
docker-compose -f docker-compose.test.yml down

echo ""
echo "✅ Docker test completed!"