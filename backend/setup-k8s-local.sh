#!/bin/bash

# Setup local Kubernetes for DreamOps development
# This script creates a kind cluster and sets up basic resources for testing

echo "Setting up local Kubernetes development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running or not accessible."
    echo ""
    echo "Please ensure Docker is running:"
    echo "  Option 1: Install Docker Desktop for Windows and enable WSL2 integration"
    echo "  Option 2: Start Docker service in WSL2: sudo service docker start"
    echo ""
    exit 1
fi

echo "✅ Docker is running"

# Add current user to docker group if needed (for WSL2)
if ! groups | grep -q docker; then
    echo "Adding user to docker group..."
    sudo usermod -aG docker $USER
    echo "⚠️  You may need to restart your terminal or run: newgrp docker"
fi

# Create kind cluster
export PATH="$HOME/bin:$PATH"

if kind get clusters | grep -q "oncall-test"; then
    echo "✅ Kind cluster 'oncall-test' already exists"
else
    echo "Creating kind cluster 'oncall-test'..."
    
    cat > kind-config.yaml << EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: oncall-test
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 8080
    protocol: TCP
  - containerPort: 443
    hostPort: 8443
    protocol: TCP
EOF

    if kind create cluster --config kind-config.yaml; then
        echo "✅ Kind cluster created successfully"
        rm kind-config.yaml
    else
        echo "❌ Failed to create kind cluster"
        exit 1
    fi
fi

# Set kubectl context
kubectl cluster-info --context kind-oncall-test
echo "✅ Kubernetes context set to kind-oncall-test"

# Create test namespace
kubectl create namespace test-apps --dry-run=client -o yaml | kubectl apply -f -
echo "✅ Created test-apps namespace"

# Deploy some test applications for incident simulation
echo "Deploying test applications..."

# Deploy a simple nginx app that we can break for testing
cat > test-app.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-nginx
  namespace: test-apps
  labels:
    app: test-nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: test-nginx
  template:
    metadata:
      labels:
        app: test-nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: test-nginx-service
  namespace: test-apps
spec:
  selector:
    app: test-nginx
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: memory-hog
  namespace: test-apps
  labels:
    app: memory-hog
spec:
  replicas: 1
  selector:
    matchLabels:
      app: memory-hog
  template:
    metadata:
      labels:
        app: memory-hog
    spec:
      containers:
      - name: memory-hog
        image: nginx:1.21
        resources:
          requests:
            memory: "32Mi"
            cpu: "100m"
          limits:
            memory: "64Mi"  # Low limit for OOM testing
            cpu: "200m"
EOF

kubectl apply -f test-app.yaml
rm test-app.yaml

echo "✅ Test applications deployed"

# Wait for pods to be ready
echo "Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=test-nginx -n test-apps --timeout=60s
kubectl wait --for=condition=ready pod -l app=memory-hog -n test-apps --timeout=60s

# Show cluster status
echo ""
echo "🎉 Kubernetes local development environment is ready!"
echo ""
echo "Cluster info:"
kubectl cluster-info --context kind-oncall-test
echo ""
echo "Test applications:"
kubectl get pods -n test-apps
echo ""
echo "To use this cluster:"
echo "  kubectl config use-context kind-oncall-test"
echo ""
echo "To simulate incidents for testing the oncall agent:"
echo "  # Cause OOM kill:"
echo "  kubectl patch deployment memory-hog -n test-apps -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"memory-hog\",\"image\":\"polinux/stress\",\"command\":[\"stress\"],\"args\":[\"--vm\",\"1\",\"--vm-bytes\",\"100M\"]}]}}}}'"
echo ""
echo "  # Cause pod crash:"
echo "  kubectl patch deployment test-nginx -n test-apps -p '{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"nginx\",\"image\":\"nginx:invalid-tag\"}]}}}}'"
echo ""
echo "  # Scale down to zero (service unavailable):"
echo "  kubectl scale deployment test-nginx --replicas=0 -n test-apps"
echo ""
echo "To reset test apps:"
echo "  kubectl delete namespace test-apps"
echo "  kubectl create namespace test-apps"
echo "  # Then rerun this script"