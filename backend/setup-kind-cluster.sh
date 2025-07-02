#!/bin/bash

# Setup Kind cluster for oncall-agent testing

CLUSTER_NAME="oncall-test"
NAMESPACE="oncall-demo"

echo "🚀 Setting up Kind cluster for oncall-agent testing..."

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo "❌ Kind is not installed. Please install it first:"
    echo "   brew install kind"
    echo "   or"
    echo "   go install sigs.k8s.io/kind@latest"
    exit 1
fi

# Check if docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if cluster already exists
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "✅ Cluster '${CLUSTER_NAME}' already exists"
    echo "   To delete and recreate: kind delete cluster --name ${CLUSTER_NAME}"
else
    echo "📦 Creating Kind cluster '${CLUSTER_NAME}'..."
    
    # Create kind cluster with custom configuration
    cat <<EOF | kind create cluster --name ${CLUSTER_NAME} --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
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
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
EOF

    if [ $? -ne 0 ]; then
        echo "❌ Failed to create Kind cluster"
        exit 1
    fi
fi

echo ""
echo "🔧 Setting up kubectl context..."
kubectl cluster-info --context kind-${CLUSTER_NAME}

echo ""
echo "📋 Creating test namespace '${NAMESPACE}'..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "🚀 Deploying sample applications for testing..."

# Deploy nginx deployment
echo "Deploying nginx..."
kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.21
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
EOF

# Deploy a pod that will crash (for testing CrashLoopBackOff)
echo ""
echo "Deploying crasher pod (intentionally failing)..."
kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: crasher-pod
  labels:
    app: crasher
spec:
  containers:
  - name: crasher
    image: busybox
    command: ['sh', '-c', 'echo "I am going to crash!" && exit 1']
    resources:
      requests:
        memory: "32Mi"
        cpu: "10m"
EOF

# Deploy a pod with high memory usage (for testing OOM scenarios)
echo ""
echo "Deploying memory-hungry pod..."
kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: memory-hungry
  labels:
    app: memory-test
spec:
  containers:
  - name: memory-consumer
    image: polinux/stress
    command: ["stress"]
    args: ["--vm", "1", "--vm-bytes", "150M", "--vm-hang", "1"]
    resources:
      requests:
        memory: "64Mi"
        cpu: "50m"
      limits:
        memory: "100Mi"
        cpu: "100m"
EOF

# Deploy a simple web app
echo ""
echo "Deploying hello-world app..."
kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hello-world
  labels:
    app: hello-world
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hello-world
  template:
    metadata:
      labels:
        app: hello-world
    spec:
      containers:
      - name: hello
        image: gcr.io/google-samples/hello-app:1.0
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
        resources:
          requests:
            memory: "32Mi"
            cpu: "10m"
          limits:
            memory: "64Mi"
            cpu: "50m"
---
apiVersion: v1
kind: Service
metadata:
  name: hello-world-service
spec:
  selector:
    app: hello-world
  ports:
    - protocol: TCP
      port: 8080
      targetPort: 8080
  type: ClusterIP
EOF

echo ""
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=60s deployment/nginx-deployment -n ${NAMESPACE}
kubectl wait --for=condition=available --timeout=60s deployment/hello-world -n ${NAMESPACE}

echo ""
echo "📊 Cluster Status:"
echo "=================="
kubectl get nodes
echo ""
kubectl get pods -n ${NAMESPACE}
echo ""
kubectl get services -n ${NAMESPACE}

echo ""
echo "🎉 Kind cluster '${CLUSTER_NAME}' is ready!"
echo ""
echo "📝 Connection Details:"
echo "====================="
echo "Cluster Name: ${CLUSTER_NAME}"
echo "Context: kind-${CLUSTER_NAME}"
echo "Namespace: ${NAMESPACE}"
echo ""
echo "To use this cluster:"
echo "  kubectl config use-context kind-${CLUSTER_NAME}"
echo "  kubectl get pods -n ${NAMESPACE}"
echo ""
echo "To connect from the UI:"
echo "1. Go to the Kubernetes integration settings"
echo "2. The context 'kind-${CLUSTER_NAME}' should appear in the dropdown"
echo "3. Select it and test the connection"
echo ""
echo "To simulate issues for testing:"
echo "  ./simulate-k8s-issues.sh"
echo ""
echo "To delete this cluster:"
echo "  kind delete cluster --name ${CLUSTER_NAME}"