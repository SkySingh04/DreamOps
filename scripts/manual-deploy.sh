#!/bin/bash
set -e

# DreamOps Manual Deployment Script
# Usage: ./scripts/manual-deploy.sh

echo "🚀 DreamOps Manual Deployment"
echo "=============================="
echo ""

# Configuration
SERVER_HOST="${SERVER_HOST:-37.27.111.47}"
SERVER_USER="${SERVER_USER:-root}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-507254053937}"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "📋 Configuration:"
echo "  Server: $SERVER_USER@$SERVER_HOST"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  AWS Region: $AWS_REGION"
echo ""

# Check if we can SSH to the server
echo "🔐 Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 $SERVER_USER@$SERVER_HOST "echo 'SSH connection successful'" 2>/dev/null; then
    echo "❌ Cannot connect to server. Please check your SSH credentials."
    exit 1
fi
echo "✅ SSH connection successful"
echo ""

# Build backend
echo "🏗️  Building backend Docker image..."
cd backend
docker build -f Dockerfile.prod -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/dreamops-backend:latest .
cd ..
echo "✅ Backend image built"
echo ""

# Build frontend
echo "🏗️  Building frontend Docker image..."
cd frontend
docker build -f Dockerfile -t $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/dreamops-frontend:latest .
cd ..
echo "✅ Frontend image built"
echo ""

# Login to ECR
echo "🔐 Logging in to AWS ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo "✅ ECR login successful"
echo ""

# Push images
echo "📤 Pushing backend image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/dreamops-backend:latest
echo "✅ Backend image pushed"
echo ""

echo "📤 Pushing frontend image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/dreamops-frontend:latest
echo "✅ Frontend image pushed"
echo ""

# Deploy to server
echo "🚀 Deploying to server..."
ssh $SERVER_USER@$SERVER_HOST << 'ENDSSH'
cd /opt/dreamops

# Login to ECR
echo "🔐 Logging in to ECR on server..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 507254053937.dkr.ecr.us-east-1.amazonaws.com

# Pull latest images
echo "📥 Pulling latest images..."
docker-compose pull

# Restart services
echo "🔄 Restarting services..."
docker-compose up -d

# Wait for health checks
echo "⏳ Waiting for health checks..."
sleep 10

# Show status
echo "📊 Service status:"
docker-compose ps

# Clean up old images
echo "🧹 Cleaning up old images..."
docker image prune -af

echo "✅ Deployment complete!"
ENDSSH

echo ""
echo "✅ Deployment successful!"
echo ""
echo "🔍 Check application:"
echo "  Backend health: curl http://$SERVER_HOST:8000/health"
echo "  Frontend: https://dreamops.yourdomain.com"
echo ""
echo "📊 View logs:"
echo "  ssh $SERVER_USER@$SERVER_HOST 'cd /opt/dreamops && docker-compose logs -f'"
echo ""
