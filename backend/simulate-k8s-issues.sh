#!/bin/bash

# Simulate various Kubernetes issues for testing the oncall agent

NAMESPACE="oncall-demo"

echo "🔥 Kubernetes Issue Simulator"
echo "============================"
echo ""
echo "Select an issue to simulate:"
echo "1. Pod CrashLoopBackOff"
echo "2. ImagePullBackOff" 
echo "3. OOMKilled"
echo "4. High CPU Usage"
echo "5. Service Down"
echo "6. Deployment Failure"
echo "7. All Issues"
echo "8. Clean up all issues"
echo ""
read -p "Enter your choice (1-8): " choice

case $choice in
    1)
        echo "💥 Simulating Pod CrashLoopBackOff..."
        kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: crash-loop-pod
  labels:
    app: crash-test
spec:
  containers:
  - name: crasher
    image: busybox
    command: ['sh', '-c', 'echo "Starting up..." && sleep 5 && exit 1']
    resources:
      requests:
        memory: "32Mi"
        cpu: "10m"
EOF
        echo "✅ Created crash-loop-pod. It will crash every 5 seconds."
        echo "Watch it with: kubectl get pod crash-loop-pod -n ${NAMESPACE} -w"
        ;;
        
    2)
        echo "🖼️ Simulating ImagePullBackOff..."
        kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: bad-image-pod
  labels:
    app: image-test
spec:
  containers:
  - name: bad-image
    image: this-image-definitely-does-not-exist:latest
    resources:
      requests:
        memory: "32Mi"
        cpu: "10m"
EOF
        echo "✅ Created bad-image-pod with non-existent image."
        ;;
        
    3)
        echo "💾 Simulating OOMKilled..."
        kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: oom-pod
  labels:
    app: oom-test
spec:
  containers:
  - name: memory-hog
    image: polinux/stress
    command: ["stress"]
    args: ["--vm", "1", "--vm-bytes", "200M", "--vm-hang", "1"]
    resources:
      requests:
        memory: "50Mi"
        cpu: "50m"
      limits:
        memory: "100Mi"
        cpu: "100m"
EOF
        echo "✅ Created oom-pod that will consume more memory than allowed."
        ;;
        
    4)
        echo "🔥 Simulating High CPU Usage..."
        kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: cpu-stress-pod
  labels:
    app: cpu-test
spec:
  containers:
  - name: cpu-hog
    image: polinux/stress
    command: ["stress"]
    args: ["--cpu", "2"]
    resources:
      requests:
        memory: "32Mi"
        cpu: "100m"
      limits:
        memory: "64Mi"
        cpu: "200m"
EOF
        echo "✅ Created cpu-stress-pod consuming high CPU."
        ;;
        
    5)
        echo "🔌 Simulating Service Down..."
        # Scale down hello-world deployment to 0
        kubectl scale deployment hello-world --replicas=0 -n ${NAMESPACE}
        echo "✅ Scaled hello-world deployment to 0 replicas. Service has no endpoints."
        ;;
        
    6)
        echo "❌ Simulating Deployment Failure..."
        kubectl apply -n ${NAMESPACE} -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: failing-deployment
  labels:
    app: fail-test
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fail-test
  template:
    metadata:
      labels:
        app: fail-test
    spec:
      containers:
      - name: failing-app
        image: busybox
        command: ['sh', '-c', 'echo "Init failed!" && exit 1']
        resources:
          requests:
            memory: "32Mi"
            cpu: "10m"
EOF
        echo "✅ Created failing-deployment where all pods will fail."
        ;;
        
    7)
        echo "🌪️ Creating ALL issues..."
        $0 <<< "1" > /dev/null
        $0 <<< "2" > /dev/null
        $0 <<< "3" > /dev/null
        $0 <<< "4" > /dev/null
        $0 <<< "5" > /dev/null
        $0 <<< "6" > /dev/null
        echo "✅ All issues created!"
        ;;
        
    8)
        echo "🧹 Cleaning up all test issues..."
        kubectl delete pod crash-loop-pod bad-image-pod oom-pod cpu-stress-pod -n ${NAMESPACE} --ignore-not-found
        kubectl delete deployment failing-deployment -n ${NAMESPACE} --ignore-not-found
        kubectl scale deployment hello-world --replicas=2 -n ${NAMESPACE}
        echo "✅ Cleanup complete!"
        ;;
        
    *)
        echo "❌ Invalid choice. Please run again and select 1-8."
        exit 1
        ;;
esac

echo ""
echo "Current pod status:"
kubectl get pods -n ${NAMESPACE}