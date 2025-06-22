#!/bin/bash

# Script to simulate EKS issues for testing the oncall agent

echo "🚀 EKS Issue Simulator for Oncall Agent Testing"
echo "=============================================="

# Check if kubectl is configured
if ! kubectl config current-context > /dev/null 2>&1; then
    echo "❌ kubectl is not configured. Please configure kubectl first."
    exit 1
fi

NAMESPACE="oncall-test-apps"

# Function to create namespace if it doesn't exist
create_namespace() {
    if ! kubectl get namespace $NAMESPACE > /dev/null 2>&1; then
        echo "📁 Creating namespace: $NAMESPACE"
        kubectl create namespace $NAMESPACE
    fi
}

# Function to clean up namespace
cleanup() {
    echo "🧹 Cleaning up namespace: $NAMESPACE"
    kubectl delete namespace $NAMESPACE --force --grace-period=0 2>/dev/null || true
}

# Function to simulate CrashLoopBackOff
simulate_crash() {
    echo "💥 Simulating pod crash (CrashLoopBackOff)..."
    kubectl apply -n $NAMESPACE -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crash-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: crash-app
  template:
    metadata:
      labels:
        app: crash-app
    spec:
      containers:
      - name: app
        image: busybox
        command: ["sh", "-c", "echo 'Starting app...'; sleep 5; echo 'Crashing!'; exit 1"]
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
EOF
}

# Function to simulate ImagePullBackOff
simulate_image_pull() {
    echo "🖼️ Simulating image pull error (ImagePullBackOff)..."
    kubectl apply -n $NAMESPACE -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-image-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: bad-image-app
  template:
    metadata:
      labels:
        app: bad-image-app
    spec:
      containers:
      - name: app
        image: this-image-does-not-exist:latest
        imagePullPolicy: Always
EOF
}

# Function to simulate OOMKilled
simulate_oom() {
    echo "💾 Simulating OOM kill..."
    kubectl apply -n $NAMESPACE -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: oom-app
  template:
    metadata:
      labels:
        app: oom-app
    spec:
      containers:
      - name: app
        image: polinux/stress
        command: ["stress"]
        args: ["--vm", "1", "--vm-bytes", "200M", "--vm-hang", "1"]
        resources:
          requests:
            memory: "50Mi"
            cpu: "100m"
          limits:
            memory: "100Mi"
            cpu: "200m"
EOF
}

# Main menu
show_menu() {
    echo ""
    echo "Choose a scenario to simulate:"
    echo "1. Pod Crash (CrashLoopBackOff)"
    echo "2. Image Pull Error (ImagePullBackOff)"
    echo "3. OOM Kill"
    echo "4. All scenarios"
    echo "5. Clean up and exit"
    echo ""
    read -p "Enter your choice (1-5): " choice
}

# Create namespace
create_namespace

# Main loop
while true; do
    show_menu
    
    case $choice in
        1)
            simulate_crash
            echo "✅ Created crashing pods. They will enter CrashLoopBackOff state soon."
            ;;
        2)
            simulate_image_pull
            echo "✅ Created pod with bad image. It will enter ImagePullBackOff state."
            ;;
        3)
            simulate_oom
            echo "✅ Created memory-hungry pods. They will be OOMKilled soon."
            ;;
        4)
            simulate_crash
            simulate_image_pull
            simulate_oom
            echo "✅ Created all problematic scenarios."
            ;;
        5)
            cleanup
            echo "👋 Cleanup complete. Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid choice. Please try again."
            ;;
    esac
    
    echo ""
    echo "📊 Current pod status:"
    kubectl get pods -n $NAMESPACE
    echo ""
    echo "💡 Tip: Watch the pods with: kubectl get pods -n $NAMESPACE -w"
    echo "💡 These issues will trigger CloudWatch alarms → PagerDuty → Oncall Agent"
done