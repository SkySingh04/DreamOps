#!/bin/bash

# Fuck Kubernetes - Simulate random Kubernetes issues for PagerDuty testing
# Usage: ./fuck_kubernetes.sh [issue_number|all|random]

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Debug: Show environment info
echo -e "${YELLOW}Debug: Running as user: $(whoami)${NC}"
echo -e "${YELLOW}Debug: HOME=$HOME${NC}"
echo -e "${YELLOW}Debug: KUBECONFIG=$KUBECONFIG${NC}"
echo -e "${YELLOW}Debug: PATH=$PATH${NC}"
echo -e "${YELLOW}Debug: AWS_PROFILE=$AWS_PROFILE${NC}"
echo -e "${YELLOW}Debug: AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION${NC}"

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl command not found. Please install kubectl first.${NC}"
    echo -e "${YELLOW}Debug: Checking common kubectl locations...${NC}"
    
    # List of possible kubectl locations including Docker Desktop
    kubectl_paths=(
        "/usr/local/bin/kubectl"
        "/usr/bin/kubectl" 
        "/opt/homebrew/bin/kubectl"
        "/mnt/c/Program Files/Docker/Docker/resources/bin/kubectl.exe"
        "/c/Program Files/Docker/Docker/resources/bin/kubectl.exe"
    )
    
    kubectl_found=false
    for loc in "${kubectl_paths[@]}"; do
        if [ -f "$loc" ]; then
            echo -e "${YELLOW}Found kubectl at: $loc${NC}"
            # Create a symlink or alias for easier access
            if [[ "$loc" == *".exe" ]]; then
                # For Windows executable, create an alias
                echo -e "${YELLOW}Setting up kubectl wrapper for Windows executable${NC}"
                # Create a simple wrapper script instead of function
                mkdir -p /tmp/kubectl-wrapper 2>/dev/null
                cat > /tmp/kubectl-wrapper/kubectl << EOF
#!/bin/bash
exec "$loc" "\$@"
EOF
                chmod +x /tmp/kubectl-wrapper/kubectl
                export PATH="/tmp/kubectl-wrapper:$PATH"
            else
                export PATH="$(dirname $loc):$PATH"
            fi
            kubectl_found=true
            break
        fi
    done
    
    # Check again after updating PATH
    if [ "$kubectl_found" = false ] || ! kubectl version --client &> /dev/null; then
        echo -e "${RED}Error: kubectl not found or not working${NC}"
        exit 1
    fi
fi

# Set default kubeconfig if not set
if [ -z "$KUBECONFIG" ]; then
    export KUBECONFIG="$HOME/.kube/config"
    echo -e "${YELLOW}Debug: Using default KUBECONFIG=$KUBECONFIG${NC}"
fi

# Check if kubeconfig file exists
if [ ! -f "$KUBECONFIG" ]; then
    echo -e "${RED}Error: KUBECONFIG file not found at: $KUBECONFIG${NC}"
    echo -e "${YELLOW}Debug: Looking for kubeconfig in common locations...${NC}"
    for loc in "$HOME/.kube/config" "/etc/kubernetes/admin.conf"; do
        if [ -f "$loc" ]; then
            echo -e "${YELLOW}Found kubeconfig at: $loc${NC}"
            export KUBECONFIG="$loc"
            break
        fi
    done
fi

# Check if we have a valid kubernetes context
echo -e "${YELLOW}Debug: Testing kubectl connection...${NC}"

# Try to get cluster info without producing stderr output
if kubectl cluster-info &> /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"
    DEMO_MODE=false
else
    echo -e "${YELLOW}Warning: No valid kubernetes cluster context found.${NC}"
    echo -e "${YELLOW}Debug: Current context:${NC}"
    # Suppress error output and file access attempts
    kubectl config current-context 2>/dev/null || echo "No context set"
    echo -e "${YELLOW}Debug: Available contexts:${NC}"
    kubectl config get-contexts 2>/dev/null || echo "No contexts available"
    echo -e "${YELLOW}Running in DEMO MODE - simulating chaos operations...${NC}"
    DEMO_MODE=true
fi

# Function to print usage
usage() {
    echo "Usage: $0 [option]"
    echo "Options:"
    echo "  1         - Simulate pod crash (CrashLoopBackOff)"
    echo "  2         - Simulate image pull error (ImagePullBackOff)"
    echo "  3         - Simulate OOM kill"
    echo "  4         - Simulate deployment failure"
    echo "  5         - Simulate service unavailable"
    echo "  all       - Run all simulations sequentially"
    echo "  random    - Run a random simulation (default)"
    echo "  clean     - Clean up all test resources"
    echo "  trigger   - Force CloudWatch alarms to trigger PagerDuty"
    echo "  loop      - Continuous testing loop with auto-triggering"
    exit 1
}

# Namespace for testing
NAMESPACE="fuck-kubernetes-test"

# Ensure namespace exists
ensure_namespace() {
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        echo -e "${YELLOW}Creating namespace: $NAMESPACE${NC}"
        kubectl create namespace $NAMESPACE
    fi
}

# Function to simulate pod crash
fuck_pod_crash() {
    echo -e "${RED}🔥 Fucking Kubernetes: Simulating Pod Crash (CrashLoopBackOff)${NC}"
    
    if [ "$DEMO_MODE" = true ]; then
        echo -e "${YELLOW}DEMO MODE: Simulating Pod Crash deployment...${NC}"
        sleep 2
        echo -e "${GREEN}✓ Pod crash simulation deployed (demo). CrashLoopBackOff incoming!${NC}"
        echo -e "${YELLOW}Demo: kubectl apply -f crashloop-deployment.yaml${NC}"
        echo -e "${YELLOW}Demo: Deployment would create pods that crash immediately${NC}"
        return 0
    fi
    
    ensure_namespace
    
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crashloop-app
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crashloop
  template:
    metadata:
      labels:
        app: crashloop
    spec:
      containers:
      - name: crash-container
        image: busybox
        command: ["/bin/sh", "-c"]
        args: ["echo 'Starting up...'; sleep 5; echo 'Crashing now!'; exit 1"]
        resources:
          requests:
            memory: "64Mi"
            cpu: "250m"
          limits:
            memory: "128Mi"
            cpu: "500m"
EOF
    
    echo -e "${GREEN}✓ Pod crash simulation deployed. Watch it crash and burn!${NC}"
    echo "Run 'kubectl get pods -n $NAMESPACE' to see the CrashLoopBackOff"
}

# Function to simulate image pull error
fuck_image_pull() {
    echo -e "${RED}🔥 Fucking Kubernetes: Simulating Image Pull Error${NC}"
    ensure_namespace
    
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imagepull-error-app
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: imagepull-error
  template:
    metadata:
      labels:
        app: imagepull-error
    spec:
      containers:
      - name: bad-image
        image: totally-fake-registry.com/this-image-does-not-exist:v666
        ports:
        - containerPort: 80
EOF
    
    echo -e "${GREEN}✓ Image pull error simulation deployed. Good luck pulling that image!${NC}"
    echo "Run 'kubectl get pods -n $NAMESPACE' to see the ImagePullBackOff"
}

# Function to simulate OOM kill
fuck_oom_kill() {
    echo -e "${RED}🔥 Fucking Kubernetes: Simulating OOM Kill${NC}"
    
    if [ "$DEMO_MODE" = true ]; then
        echo -e "${YELLOW}DEMO MODE: Simulating OOM Kill deployment...${NC}"
        sleep 2
        echo -e "${GREEN}✓ OOM kill simulation deployed (demo). Memory massacre incoming!${NC}"
        echo -e "${YELLOW}Demo: kubectl apply -f oom-kill-deployment.yaml${NC}"
        echo -e "${YELLOW}Demo: Deployment would consume excessive memory and trigger OOMKilled${NC}"
        return 0
    fi
    
    ensure_namespace
    
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-app
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom-killer
  template:
    metadata:
      labels:
        app: oom-killer
    spec:
      containers:
      - name: memory-hog
        image: polinux/stress
        command: ["stress"]
        args: ["--vm", "1", "--vm-bytes", "1000M", "--vm-hang", "1"]
        resources:
          requests:
            memory: "50Mi"
            cpu: "100m"
          limits:
            memory: "100Mi"
            cpu: "200m"
EOF
    
    echo -e "${GREEN}✓ OOM kill simulation deployed. Memory massacre incoming!${NC}"
    echo "Run 'kubectl get pods -n $NAMESPACE' to see the OOMKilled status"
}

# Function to simulate deployment failure
fuck_deployment() {
    echo -e "${RED}🔥 Fucking Kubernetes: Simulating Deployment Failure${NC}"
    ensure_namespace
    
    # First create a working deployment
    cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: failed-deployment
  namespace: $NAMESPACE
spec:
  replicas: 3
  selector:
    matchLabels:
      app: fail-deploy
  template:
    metadata:
      labels:
        app: fail-deploy
    spec:
      containers:
      - name: nginx
        image: nginx:1.14
        ports:
        - containerPort: 80
EOF
    
    sleep 5
    
    # Now update with bad image to trigger failure
    kubectl set image deployment/failed-deployment nginx=nginx:totally-broken-tag -n $NAMESPACE
    
    echo -e "${GREEN}✓ Deployment failure simulation initiated. Rolling update will fail!${NC}"
    echo "Run 'kubectl rollout status deployment/failed-deployment -n $NAMESPACE' to see the failure"
}

# Function to simulate service unavailable
fuck_service() {
    echo -e "${RED}🔥 Fucking Kubernetes: Simulating Service Unavailable${NC}"
    ensure_namespace
    
    # Create a service with no matching pods
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: broken-service
  namespace: $NAMESPACE
spec:
  selector:
    app: non-existent-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wrong-label-app
  namespace: $NAMESPACE
spec:
  replicas: 2
  selector:
    matchLabels:
      app: wrong-label
  template:
    metadata:
      labels:
        app: wrong-label  # Intentionally wrong label
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        ports:
        - containerPort: 80
EOF
    
    echo -e "${GREEN}✓ Service unavailable simulation deployed. Service has no endpoints!${NC}"
    echo "Run 'kubectl describe service broken-service -n $NAMESPACE' to see no endpoints"
}

# Function to clean up all test resources
clean_up() {
    echo -e "${YELLOW}🧹 Cleaning up all test resources...${NC}"
    
    if kubectl get namespace $NAMESPACE &> /dev/null; then
        kubectl delete namespace $NAMESPACE --grace-period=0 --force &> /dev/null || true
        echo -e "${GREEN}✓ Cleaned up namespace: $NAMESPACE${NC}"
    else
        echo "Nothing to clean up."
    fi
}

# Function to run all simulations
run_all() {
    echo -e "${YELLOW}🔥 Running ALL Kubernetes fuckery simulations!${NC}"
    
    fuck_pod_crash
    echo -e "\n${YELLOW}Waiting 10 seconds before next simulation...${NC}\n"
    sleep 10
    
    fuck_image_pull
    echo -e "\n${YELLOW}Waiting 10 seconds before next simulation...${NC}\n"
    sleep 10
    
    fuck_oom_kill
    echo -e "\n${YELLOW}Waiting 10 seconds before next simulation...${NC}\n"
    sleep 10
    
    fuck_deployment
    echo -e "\n${YELLOW}Waiting 10 seconds before next simulation...${NC}\n"
    sleep 10
    
    fuck_service
    
    echo -e "\n${GREEN}✓ All simulations deployed! Your Kubernetes is properly fucked!${NC}"
    echo -e "${YELLOW}Run 'kubectl get all -n $NAMESPACE' to see the chaos${NC}"
    echo -e "${YELLOW}Run '$0 clean' to clean up when done${NC}"
    
    # Auto-trigger CloudWatch alarms
    echo -e "\n${YELLOW}⚡ Auto-triggering CloudWatch alarms...${NC}"
    sleep 5  # Give a few seconds for metrics to propagate
    trigger_alarms all
}

# Function to force CloudWatch alarms to trigger
trigger_alarms() {
    local scenario="${1:-all}"
    echo -e "${YELLOW}🔔 Forcing CloudWatch alarms to trigger PagerDuty...${NC}"
    
    # Check if AWS CLI is available
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}Error: AWS CLI not found. Cannot trigger alarms.${NC}"
        return 1
    fi
    
    # Define alarms for each scenario
    local alarms=()
    
    case "$scenario" in
        1|pod_crash)
            alarms=("eks-any-pod-error" "eks-instant-pod-issue" "eks-problem-pods-detected")
            echo -e "${YELLOW}Triggering alarms for: Pod Crash scenario${NC}"
            ;;
        2|image_pull)
            alarms=("eks-image-pull-error" "eks-any-pod-error" "eks-problem-pods-detected")
            echo -e "${YELLOW}Triggering alarms for: Image Pull Error scenario${NC}"
            ;;
        3|oom_kill)
            alarms=("eks-oom-kill" "eks-any-pod-error" "eks-problem-pods-detected")
            echo -e "${YELLOW}Triggering alarms for: OOM Kill scenario${NC}"
            ;;
        4|deployment)
            alarms=("eks-any-pod-error" "eks-problem-pods-detected")
            echo -e "${YELLOW}Triggering alarms for: Deployment Failure scenario${NC}"
            ;;
        5|service)
            alarms=("eks-any-pod-error")
            echo -e "${YELLOW}Triggering alarms for: Service Unavailable scenario${NC}"
            ;;
        all|*)
            alarms=(
                "eks-any-pod-error"
                "eks-image-pull-error"
                "eks-oom-kill"
                "eks-instant-pod-issue"
                "eks-problem-pods-detected"
            )
            echo -e "${YELLOW}Triggering alarms for: ALL scenarios${NC}"
            ;;
    esac
    
    for alarm in "${alarms[@]}"; do
        # Get current state
        local current_state=$(AWS_PROFILE=burner aws cloudwatch describe-alarms --alarm-names "$alarm" --query "MetricAlarms[0].StateValue" --output text 2>/dev/null || echo "NOT_FOUND")
        
        if [ "$current_state" == "ALARM" ]; then
            echo -e "  📍 ${alarm} is in ALARM state - forcing re-trigger..."
            
            # Set to OK temporarily
            AWS_PROFILE=burner aws cloudwatch set-alarm-state \
                --alarm-name "$alarm" \
                --state-value OK \
                --state-reason "Testing: Forcing re-trigger" 2>/dev/null || true
            
            sleep 2
            
            # Set back to ALARM to trigger SNS
            AWS_PROFILE=burner aws cloudwatch set-alarm-state \
                --alarm-name "$alarm" \
                --state-value ALARM \
                --state-reason "Testing: Re-triggering alarm" 2>/dev/null || true
                
            echo -e "  ${GREEN}✓ ${alarm} re-triggered!${NC}"
        elif [ "$current_state" == "OK" ]; then
            echo -e "  ⏭️  ${alarm} is in OK state - checking if it should be ALARM..."
            # Force evaluation by setting to alarm if there are issues
            if kubectl get pods -n $NAMESPACE 2>/dev/null | grep -E "Error|CrashLoop|ImagePull|OOM" >/dev/null; then
                AWS_PROFILE=burner aws cloudwatch set-alarm-state \
                    --alarm-name "$alarm" \
                    --state-value ALARM \
                    --state-reason "Testing: Found pod issues" 2>/dev/null || true
                echo -e "  ${GREEN}✓ ${alarm} set to ALARM!${NC}"
            fi
        else
            echo -e "  ❌ ${alarm} not found or error checking state"
        fi
    done
    
    echo -e "\n${GREEN}✅ Alarm triggering complete! Check PagerDuty for alerts.${NC}"
}

# Function for continuous testing loop
test_loop() {
    echo -e "${YELLOW}🔁 Starting continuous PagerDuty test loop...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}\n"
    
    local iteration=1
    
    while true; do
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${YELLOW}Iteration #${iteration} - $(date)${NC}"
        echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        
        # Clean and create fresh issue
        echo -e "\n1️⃣  Cleaning up previous test..."
        clean_up >/dev/null 2>&1
        sleep 3
        
        # Create random issue
        echo -e "\n2️⃣  Creating new Kubernetes issue..."
        RANDOM_FUCK=$((RANDOM % 5 + 1))
        case $RANDOM_FUCK in
            1) fuck_pod_crash ;;
            2) fuck_image_pull ;;
            3) fuck_oom_kill ;;
            4) fuck_deployment ;;
            5) fuck_service ;;
        esac
        
        # Wait for CloudWatch to detect
        echo -e "\n3️⃣  Waiting 60 seconds for CloudWatch to detect issue..."
        sleep 60
        
        # Force trigger alarms
        echo -e "\n4️⃣  Triggering alarms..."
        trigger_alarms $RANDOM_FUCK
        
        # Show pod status
        echo -e "\n5️⃣  Current pod status:"
        kubectl get pods -n $NAMESPACE 2>/dev/null || echo "No pods found"
        
        echo -e "\n${GREEN}✅ Iteration #${iteration} complete!${NC}"
        echo -e "${YELLOW}Waiting 2 minutes before next iteration...${NC}\n"
        
        iteration=$((iteration + 1))
        sleep 120
    done
}

# Main logic
case "${1:-random}" in
    1)
        fuck_pod_crash
        echo -e "\n${YELLOW}⚡ Auto-triggering CloudWatch alarms...${NC}"
        sleep 5
        trigger_alarms 1
        ;;
    2)
        fuck_image_pull
        echo -e "\n${YELLOW}⚡ Auto-triggering CloudWatch alarms...${NC}"
        sleep 5
        trigger_alarms 2
        ;;
    3)
        fuck_oom_kill
        echo -e "\n${YELLOW}⚡ Auto-triggering CloudWatch alarms...${NC}"
        sleep 5
        trigger_alarms 3
        ;;
    4)
        fuck_deployment
        echo -e "\n${YELLOW}⚡ Auto-triggering CloudWatch alarms...${NC}"
        sleep 5
        trigger_alarms 4
        ;;
    5)
        fuck_service
        echo -e "\n${YELLOW}⚡ Auto-triggering CloudWatch alarms...${NC}"
        sleep 5
        trigger_alarms 5
        ;;
    all)
        run_all
        ;;
    clean)
        clean_up
        ;;
    trigger)
        trigger_alarms
        exit 0
        ;;
    loop)
        test_loop
        exit 0
        ;;
    random|"")
        # Generate random number between 1 and 5
        RANDOM_FUCK=$((RANDOM % 5 + 1))
        echo -e "${YELLOW}🎲 Randomly selected simulation: $RANDOM_FUCK${NC}\n"
        
        case $RANDOM_FUCK in
            1) fuck_pod_crash ;;
            2) fuck_image_pull ;;
            3) fuck_oom_kill ;;
            4) fuck_deployment ;;
            5) fuck_service ;;
        esac
        
        echo -e "\n${YELLOW}⚡ Auto-triggering CloudWatch alarms...${NC}"
        sleep 5
        trigger_alarms $RANDOM_FUCK
        ;;
    *)
        usage
        ;;
esac

# Only show these messages if not running trigger or loop
if [[ "$1" != "trigger" && "$1" != "loop" && "$1" != "clean" ]]; then
    echo -e "\n${YELLOW}📊 CloudWatch alarms have been automatically triggered!${NC}"
    echo -e "${YELLOW}Check your Slack for alerts from PagerDuty${NC}"
    echo -e "\n${YELLOW}💡 TIP: Run '$0 loop' for continuous testing with auto-triggering${NC}"
fi