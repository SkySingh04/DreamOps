#!/bin/bash

# inject_k8s_issues.sh - Inject deterministic Kubernetes issues that can be fixed with specific commands
# These issues are designed to be 100% fixable by the oncall agent

set -e

# Set up Kubernetes environment (if needed)
export PATH="$HOME/bin:$PATH"
if [ -f "/home/harsh/kubeconfig-oncall" ]; then
    export KUBECONFIG="/home/harsh/kubeconfig-oncall"
fi

NAMESPACE="oncall-test-apps"
TIMESTAMP=$(date +%s)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔥 Kubernetes Issue Injection Script 🔥${NC}"
echo -e "${YELLOW}Injecting deterministic issues that can be fixed by specific commands${NC}"
echo ""

# Check if PagerDuty integration key is set
if [ -z "$PAGERDUTY_INTEGRATION_KEY" ]; then
    # Try to source from .env file if exists
    if [ -f "backend/.env" ]; then
        export $(grep -E '^PAGERDUTY_INTEGRATION_KEY=' backend/.env | xargs)
    elif [ -f ".env" ]; then
        export $(grep -E '^PAGERDUTY_INTEGRATION_KEY=' .env | xargs)
    fi
fi

# Create namespace if it doesn't exist
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f - --validate=false

# Function to send PagerDuty alert
send_pagerduty_alert() {
    local summary="$1"
    local details="$2"
    local dedup_key="$3"
    local severity="${4:-critical}"
    
    if [ -z "$PAGERDUTY_INTEGRATION_KEY" ]; then
        echo -e "${YELLOW}⚠️  PagerDuty integration key not found. Skipping alert.${NC}"
        return
    fi
    
    echo -e "${YELLOW}📟 Sending PagerDuty alert: $summary${NC}"
    
    # Create PagerDuty event
    curl -s -X POST https://events.pagerduty.com/v2/enqueue \
        -H 'Content-Type: application/json' \
        -d "{\n            \"routing_key\": \"$PAGERDUTY_INTEGRATION_KEY\",\n            \"event_action\": \"trigger\",\n            \"dedup_key\": \"$dedup_key\",\n            \"payload\": {\n                \"summary\": \"$summary\",\n                \"severity\": \"$severity\",\n                \"source\": \"fuck-kubernetes-script\",\n                \"custom_details\": {\n                    \"details\": \"$details\",\n                    \"namespace\": \"$NAMESPACE\",\n                    \"injected_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\n                    \"test_mode\": true\n                }\n            }\n        }" > /dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PagerDuty alert sent successfully${NC}"
    else
        echo -e "${RED}❌ Failed to send PagerDuty alert${NC}"
    fi
}

# Function to display usage
usage() {
    echo "Usage: $0 [1-5|all|random|clean]"
    echo ""
    echo "Issues:"
    echo "  1 - Pod OOM Kill (fixable by scaling deployment to 3 replicas)"
    echo "  2 - Image Pull Error (fixable by updating image to nginx:latest)"  
    echo "  3 - Pod Crash Loop (fixable by deleting the pod)"
    echo "  4 - Resource Limits (fixable by patching memory to 256Mi)"
    echo "  5 - Service Down (fixable by scaling deployment from 0 to 2)"
    echo ""
    echo "  all    - Apply all issues"
    echo "  random - Apply a random issue"
    echo "  clean  - Remove all test resources"
    exit 1
}

# 1. OOM Kill Issue - Fixed by scaling to 3 replicas
apply_oom_issue() {
    echo -e "${RED}💥 Creating OOM Kill issue...${NC}"
    cat <<EOF | kubectl apply -f - --validate=false
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-app
  namespace: $NAMESPACE
  labels:
    issue: oom-kill
spec:
  replicas: 1  # Will be fixed by scaling to 3
  selector:
    matchLabels:
      app: oom-app
  template:
    metadata:
      labels:
        app: oom-app
    spec:
      containers:
      - name: memory-hog
        image: polinux/stress
        command: ["stress"]
        args: ["--vm", "1", "--vm-bytes", "150M", "--vm-hang", "1"]
        resources:
          limits:
            memory: "128Mi"
          requests:
            memory: "64Mi"
EOF
    echo -e "${GREEN}✅ OOM issue created. Fix: kubectl scale deployment oom-app -n $NAMESPACE --replicas=3${NC}"
    
    # Send PagerDuty alert
    send_pagerduty_alert \
        "Kubernetes Pod OOM Kill - oom-app" \
        "Pod in deployment oom-app is experiencing OOM kills due to memory constraints. Fix by scaling to 3 replicas." \
        "k8s-oom-kill-oom-app-$TIMESTAMP" \
        "critical"
}

# 2. Image Pull Error - Fixed by updating image to nginx:latest
apply_image_pull_issue() {
    echo -e "${RED}💥 Creating Image Pull Error...${NC}"
    cat <<EOF | kubectl apply -f - --validate=false
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bad-image-app
  namespace: $NAMESPACE
  labels:
    issue: image-pull-error
spec:
  replicas: 2
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
        image: nonexistent-registry.invalid/fake-image:v999  # Will be fixed by changing to nginx:latest
        ports:
        - containerPort: 80
EOF
    echo -e "${GREEN}✅ Image pull issue created. Fix: kubectl set image deployment/bad-image-app app=nginx:latest -n $NAMESPACE${NC}"
    
    # Send PagerDuty alert
    send_pagerduty_alert \
        "Kubernetes ImagePullBackOff - bad-image-app" \
        "Deployment bad-image-app cannot pull image nonexistent-registry.invalid/fake-image:v999. Fix by updating to nginx:latest." \
        "k8s-image-pull-bad-image-app-$TIMESTAMP" \
        "critical"
}

# 3. Crash Loop - Fixed by deleting the pod (it will recreate with fixed config)
apply_crash_loop_issue() {
    echo -e "${RED}💥 Creating Crash Loop issue...${NC}"
    # First create a working deployment
    cat <<EOF | kubectl apply -f - --validate=false
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crashloop-app
  namespace: $NAMESPACE
  labels:
    issue: crash-loop
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crashloop-app
  template:
    metadata:
      labels:
        app: crashloop-app
    spec:
      containers:
      - name: app
        image: busybox
        command: ["sh", "-c", "exit 1"]  # Always exits, causing crash loop
EOF
    echo -e "${GREEN}✅ Crash loop issue created. Fix: kubectl delete pods -l app=crashloop-app -n $NAMESPACE${NC}"
    
    # Send PagerDuty alert
    send_pagerduty_alert \
        "Kubernetes CrashLoopBackOff - crashloop-app" \
        "Pod in deployment crashloop-app is in CrashLoopBackOff state. Fix by deleting the pod to force recreation." \
        "k8s-crash-loop-crashloop-app-$TIMESTAMP" \
        "critical"
}

# 4. Resource Limits Too Low - Fixed by patching memory to 256Mi
apply_resource_limit_issue() {
    echo -e "${RED}💥 Creating Resource Limit issue...${NC}"
    cat <<EOF | kubectl apply -f - --validate=false
apiVersion: apps/v1
kind: Deployment
metadata:
  name: resource-limited-app
  namespace: $NAMESPACE
  labels:
    issue: resource-limits
spec:
  replicas: 1
  selector:
    matchLabels:
      app: resource-limited-app
  template:
    metadata:
      labels:
        app: resource-limited-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        resources:
          limits:
            memory: "32Mi"  # Too low, will be fixed by patching to 256Mi
            cpu: "50m"
          requests:
            memory: "16Mi"
            cpu: "25m"
EOF
    echo -e "${GREEN}✅ Resource limit issue created. Fix: kubectl patch deployment resource-limited-app -n $NAMESPACE --type json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"256Mi"}]'${NC}"
    
    # Send PagerDuty alert
    send_pagerduty_alert \
        "Kubernetes Resource Constraints - resource-limited-app" \
        "Deployment resource-limited-app has insufficient memory limits (32Mi). Fix by patching memory limit to 256Mi." \
        "k8s-resource-limit-resource-limited-app-$TIMESTAMP" \
        "critical"
}

# 5. Service Down - Fixed by scaling from 0 to 2 replicas
apply_service_down_issue() {
    echo -e "${RED}💥 Creating Service Down issue...${NC}"
    cat <<EOF | kubectl apply -f - --validate=false
apiVersion: apps/v1
kind: Deployment
metadata:
  name: down-service-app
  namespace: $NAMESPACE
  labels:
    issue: service-down
spec:
  replicas: 0  # No pods running, will be fixed by scaling to 2
  selector:
    matchLabels:
      app: down-service-app
  template:
    metadata:
      labels:
        app: down-service-app
    spec:
      containers:
      - name: app
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: down-service
  namespace: $NAMESPACE
spec:
  selector:
    app: down-service-app
  ports:
  - port: 80
    targetPort: 80
EOF
    echo -e "${GREEN}✅ Service down issue created. Fix: kubectl scale deployment down-service-app -n $NAMESPACE --replicas=2${NC}"
    
    # Send PagerDuty alert
    send_pagerduty_alert \
        "Kubernetes Service Unavailable - down-service" \
        "Service down-service has no running pods (0 replicas). Fix by scaling deployment to 2 replicas." \
        "k8s-service-down-down-service-$TIMESTAMP" \
        "critical"
}

# Clean up function
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up all test resources...${NC}"
    kubectl delete namespace $NAMESPACE --ignore-not-found=true
    echo -e "${GREEN}✅ Cleanup complete${NC}"
}

# Show current issues
show_issues() {
    echo -e "${YELLOW}📊 Current Issues in $NAMESPACE:${NC}"
    echo ""
    
    # Check for OOM kills
    echo -e "${YELLOW}OOM Issues:${NC}"
    kubectl get pods -n $NAMESPACE -o wide | grep -E "OOMKilled|Error" || echo "None"
    
    # Check for image pull errors
    echo -e "\n${YELLOW}Image Pull Issues:${NC}"
    kubectl get pods -n $NAMESPACE -o wide | grep "ImagePullBackOff" || echo "None"
    
    # Check for crash loops
    echo -e "\n${YELLOW}Crash Loop Issues:${NC}"
    kubectl get pods -n $NAMESPACE -o wide | grep "CrashLoopBackOff" || echo "None"
    
    # Check deployments
    echo -e "\n${YELLOW}Deployment Status:${NC}"
    kubectl get deployments -n $NAMESPACE
    
    echo -e "\n${YELLOW}All Pods:${NC}"
    kubectl get pods -n $NAMESPACE -o wide
}

# Main logic
case "${1:-}" in
    1)
        apply_oom_issue
        ;;
    2)
        apply_image_pull_issue
        ;;
    3)
        apply_crash_loop_issue
        ;;
    4)
        apply_resource_limit_issue
        ;;
    5)
        apply_service_down_issue
        ;;
    all)
        apply_oom_issue
        sleep 2
        apply_image_pull_issue
        sleep 2
        apply_crash_loop_issue
        sleep 2
        apply_resource_limit_issue
        sleep 2
        apply_service_down_issue
        ;;
    random)
        RANDOM_ISSUE=$((1 + RANDOM % 5))
        echo -e "${YELLOW}Applying random issue: $RANDOM_ISSUE${NC}"
        $0 $RANDOM_ISSUE
        ;;
    clean)
        cleanup
        ;;
    status)
        show_issues
        ;;
    *)
        usage
        ;;
esac

echo ""
echo -e "${YELLOW}Waiting for issues to manifest...${NC}"
sleep 5

# Show final status
show_issues

echo ""
echo -e "${GREEN}✅ Issue injection complete!${NC}"
echo -e "${YELLOW}These issues will trigger CloudWatch alarms within 60 seconds.${NC}"
echo -e "${YELLOW}The oncall agent can fix them with the specific commands shown above.${NC}"