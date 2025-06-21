#!/bin/bash
set -e

echo "🚀 Deploying sample applications with various issues to EKS cluster..."

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured. Please run: aws eks update-kubeconfig --name <cluster-name>"
    exit 1
fi

# Apply namespace
echo "📦 Creating namespace..."
kubectl apply -f sample-apps/namespace.yaml

# Deploy all sample apps
echo "🔧 Deploying problematic applications..."
kubectl apply -f sample-apps/

# Wait for deployments
echo "⏳ Waiting for deployments to be created..."
sleep 10

# Show status
echo -e "\n📊 Current status of test applications:"
kubectl get all -n test-apps

echo -e "\n🔍 Pod details:"
kubectl get pods -n test-apps -o wide

echo -e "\n⚠️  Expected issues:"
echo "1. config-missing-app: CrashLoopBackOff (missing ConfigMap)"
echo "2. memory-hog-app: OOMKilled (memory limit exceeded)"
echo "3. bad-image-app: ImagePullBackOff (non-existent image)"
echo "4. cpu-intensive-app: CPU Throttling (high CPU usage)"
echo "5. unhealthy-app: Liveness probe failures after ~90 seconds"

echo -e "\n✅ Sample applications deployed! Use these for testing the oncall agent."
echo "To remove all test apps: kubectl delete namespace test-apps"