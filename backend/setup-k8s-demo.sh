#!/bin/bash

# Script to set up Kubernetes demo environment for testing Oncall Agent

echo "🚀 Setting up Kubernetes demo environment..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Set kubeconfig if provided
if [ -n "$1" ]; then
    export KUBECONFIG=$1
    echo "📋 Using kubeconfig: $KUBECONFIG"
fi

# Check cluster connection
echo "🔍 Checking cluster connection..."
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ Cannot connect to Kubernetes cluster. Please ensure:"
    echo "   1. Kind cluster is running"
    echo "   2. KUBECONFIG is set correctly"
    echo "   3. You have copied the kubeconfig to WSL"
    exit 1
fi

echo "✅ Connected to cluster: $(kubectl config current-context)"

# Create demo-apps namespace
echo "📦 Creating demo-apps namespace..."
kubectl create namespace demo-apps --dry-run=client -o yaml | kubectl apply -f -

# Deploy demo applications
echo "🚀 Deploying demo applications..."
kubectl apply -f k8s-demo-apps.yaml

echo ""
echo "✅ Demo environment setup complete!"
echo ""
echo "📊 Deployment Status:"
kubectl get deployments -n demo-apps

echo ""
echo "🔍 Pod Status:"
kubectl get pods -n demo-apps

echo ""
echo "📌 Services:"
kubectl get services -n demo-apps

echo ""
echo "💡 Next steps:"
echo "   1. Copy .env.kind to .env and add your ANTHROPIC_API_KEY"
echo "   2. Run the API server: uv run python api_server.py"
echo "   3. Test alerts: uv run python test_pagerduty_alerts.py --all"
echo ""
echo "🎯 Expected failures:"
echo "   - payment-service: CrashLoopBackOff (missing config)"
echo "   - analytics-service: ImagePullBackOff (bad image)"
echo "   - memory-hog: OOMKilled (memory limit)"
echo "   - broken-database: CrashLoopBackOff (missing password)"
echo "   - frontend-app: 0 replicas (scaled down)"
echo "   - orphan-service: No endpoints"
echo ""
echo "✅ healthy-app should be running normally"