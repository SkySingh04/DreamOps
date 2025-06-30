#!/bin/bash

# Kubernetes Incident Simulation Script for DreamOps Testing
# This script helps you create various Kubernetes incidents to test the AI agent

export PATH="$HOME/bin:$PATH"
export KUBECONFIG="/home/harsh/kubeconfig-oncall"

echo "🚨 Kubernetes Incident Simulation Menu"
echo "======================================"
echo ""
echo "Available incident types:"
echo "1. OOM Kill (Out of Memory)"
echo "2. Pod Crash Loop"
echo "3. Service Unavailable (Scale to 0)"
echo "4. Image Pull Error"
echo "5. Resource Exhaustion"
echo "6. Reset all (fix everything)"
echo "7. Show current status"
echo ""

read -p "Select incident type (1-7): " choice

case $choice in
    1)
        echo "🧠 Simulating OOM Kill..."
        kubectl patch deployment memory-hog -n test-apps -p '{"spec":{"template":{"spec":{"containers":[{"name":"nginx","image":"polinux/stress","command":["stress"],"args":["--vm","1","--vm-bytes","100M"]}]}}}}'
        echo "✅ Memory stress test deployed. This will cause OOM kills due to the 64Mi limit."
        ;;
    2) 
        echo "💥 Simulating Pod Crash Loop..."
        kubectl patch deployment test-nginx -n test-apps -p '{"spec":{"template":{"spec":{"containers":[{"name":"nginx","image":"nginx:invalid-tag"}]}}}}'
        echo "✅ Invalid image deployed. Pods will enter ImagePullBackOff/CrashLoopBackOff."
        ;;
    3)
        echo "🚫 Simulating Service Unavailable..."
        kubectl scale deployment test-nginx --replicas=0 -n test-apps
        kubectl scale deployment memory-hog --replicas=0 -n test-apps
        echo "✅ All pods scaled to 0. Services are now unavailable."
        ;;
    4)
        echo "📦 Simulating Image Pull Error..."
        kubectl patch deployment test-nginx -n test-apps -p '{"spec":{"template":{"spec":{"containers":[{"name":"nginx","image":"nonexistent/image:latest"}]}}}}'
        echo "✅ Non-existent image deployed. Pods will fail to pull image."
        ;;
    5)
        echo "⚡ Simulating Resource Exhaustion..."
        kubectl patch deployment memory-hog -n test-apps -p '{"spec":{"replicas":5,"template":{"spec":{"containers":[{"name":"nginx","image":"polinux/stress","command":["stress"],"args":["--vm","2","--vm-bytes","50M"],"resources":{"requests":{"memory":"100Mi","cpu":"500m"},"limits":{"memory":"120Mi","cpu":"1000m"}}}]}}}}'
        echo "✅ Multiple high-resource pods deployed. This may exhaust cluster resources."
        ;;
    6)
        echo "🔧 Resetting all applications to healthy state..."
        kubectl delete namespace test-apps
        kubectl create namespace test-apps
        
        # Redeploy healthy applications
        kubectl create deployment test-nginx --image=nginx:1.21 -n test-apps
        kubectl scale deployment test-nginx --replicas=2 -n test-apps
        kubectl expose deployment test-nginx --port=80 --target-port=80 --name=test-nginx-service -n test-apps
        
        kubectl create deployment memory-hog --image=nginx:1.21 -n test-apps
        kubectl patch deployment memory-hog -n test-apps -p '{"spec":{"template":{"spec":{"containers":[{"name":"nginx","resources":{"limits":{"memory":"128Mi","cpu":"200m"},"requests":{"memory":"64Mi","cpu":"100m"}}}]}}}}'
        
        echo "✅ All applications reset to healthy state."
        ;;
    7)
        echo "📊 Current Cluster Status"
        echo "========================"
        echo ""
        echo "Namespaces:"
        kubectl get namespaces
        echo ""
        echo "Pods in test-apps:"
        kubectl get pods -n test-apps -o wide
        echo ""
        echo "Deployments in test-apps:"
        kubectl get deployments -n test-apps
        echo ""
        echo "Services in test-apps:"
        kubectl get services -n test-apps
        echo ""
        echo "Events (last 10):"
        kubectl get events -n test-apps --sort-by='.lastTimestamp' | tail -10
        ;;
    *)
        echo "❌ Invalid choice. Please select 1-7."
        exit 1
        ;;
esac

echo ""
echo "📝 To monitor the incident:"
echo "  kubectl get pods -n test-apps -w"
echo "  kubectl describe pod <pod-name> -n test-apps"
echo "  kubectl logs <pod-name> -n test-apps"
echo ""
echo "🤖 The DreamOps AI agent should detect and respond to these incidents automatically."
echo "   Check the backend logs and frontend dashboard for AI responses."