# Kind Kubernetes Setup for Oncall Agent Testing

This guide helps you set up a local Kubernetes cluster using Kind to test the PagerDuty to Oncall Agent integration end-to-end.

## Prerequisites

- Docker Desktop running on Windows (since WSL doesn't support Docker directly)
- kubectl installed in WSL
- Kind installed on Windows
- Python environment set up in the backend directory

## Setup Instructions

### 1. Create Kind Cluster (Run on Windows)

```powershell
# Create the Kind cluster using the provided configuration
kind create cluster --config kind-config.yaml --name oncall-agent

# Export the kubeconfig
kind get kubeconfig --name oncall-agent > oncall-agent-kubeconfig

# Verify cluster is running
kubectl cluster-info --context kind-oncall-agent
```

### 2. Configure WSL Environment

```bash
# Copy the kubeconfig to WSL
mkdir -p ~/.kube
cp /mnt/c/path/to/oncall-agent-kubeconfig ~/.kube/oncall-agent-config

# Set KUBECONFIG environment variable
export KUBECONFIG=~/.kube/oncall-agent-config

# Verify connection from WSL
kubectl cluster-info
```

### 3. Set Up Demo Applications

```bash
cd backend

# Run the setup script
./setup-k8s-demo.sh

# Or manually:
kubectl create namespace demo-apps
kubectl apply -f k8s-demo-apps.yaml
```

### 4. Configure Oncall Agent

```bash
# Copy the Kind-specific environment file
cp .env.kind .env

# Edit .env and add your ANTHROPIC_API_KEY
# ANTHROPIC_API_KEY=your-actual-key-here
```

### 5. Start the API Server

```bash
# In the backend directory
uv run python api_server.py
```

### 6. Test the Integration

#### Option A: Use the automated monitoring script
```bash
# This will monitor the cluster and send alerts automatically
uv run python test_k8s_pagerduty_integration.py

# Run once to see current issues
uv run python test_k8s_pagerduty_integration.py --once
```

#### Option B: Send test alerts manually
```bash
# Send all predefined test scenarios
uv run python test_pagerduty_alerts.py --all

# Send specific alert type
uv run python test_pagerduty_alerts.py --type kubernetes

# Stress test with multiple alerts
uv run python test_pagerduty_alerts.py --stress 10 --rate 1.0
```

## Demo Applications

The setup creates several intentionally broken applications to test different scenarios:

| Application | Issue | Expected Alert |
|------------|-------|----------------|
| payment-service | Missing config file | CrashLoopBackOff |
| analytics-service | Non-existent image | ImagePullBackOff |
| memory-hog | Memory limit exceeded | OOMKilled |
| cpu-intensive | High CPU usage | Performance warning |
| broken-database | Missing password | CrashLoopBackOff |
| frontend-app | Scaled to 0 replicas | No available replicas |
| orphan-service | No matching pods | No endpoints |
| healthy-app | Working properly | No alerts |

## Testing Flow

1. **Kubernetes Issues** → Demo apps create various failure conditions
2. **Monitoring** → The test script detects these issues
3. **Alert Generation** → Issues are converted to PagerDuty-format webhooks
4. **API Processing** → Webhooks are sent to the Oncall Agent API
5. **AI Analysis** → Claude analyzes the issue with Kubernetes context
6. **Response** → Agent provides root cause analysis and remediation steps

## Verifying the Setup

### Check Cluster Status
```bash
kubectl get nodes
kubectl get namespaces
```

### Check Demo Apps
```bash
kubectl get all -n demo-apps
kubectl get events -n demo-apps --sort-by='.lastTimestamp'
```

### Check Specific Pod Issues
```bash
# See why payment-service is crashing
kubectl logs -n demo-apps deployment/payment-service

# Check pod events
kubectl describe pod -n demo-apps -l app=payment-service
```

### Monitor API Logs
```bash
# The API server will show incoming webhooks and processing status
# Check the terminal where you're running api_server.py
```

## Cleanup

When you're done testing:

```bash
# Delete the demo apps
kubectl delete namespace demo-apps

# Delete the Kind cluster (run on Windows)
kind delete cluster --name oncall-agent
```

## Troubleshooting

### Cannot connect to cluster from WSL
- Ensure Docker Desktop is running on Windows
- Check that the kubeconfig path is correct
- Try: `kubectl config view` to see current configuration

### API server connection refused
- Ensure you're running `uv run python api_server.py`
- Check that port 8000 is not in use
- Try accessing http://localhost:8000/health

### No alerts being generated
- Check that demo apps are actually failing: `kubectl get pods -n demo-apps`
- Look for events: `kubectl get events -n demo-apps`
- Check the monitoring script output for errors

### Agent not providing K8s context
- Ensure K8S_ENABLED=true in your .env
- Check that kubectl works from the backend directory
- Look for errors in the API server logs