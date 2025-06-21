# Oncall AI Agent - Kubernetes Debugging Demo Summary

## 🎯 Demonstration Overview

This demo showcased how the Oncall AI Agent automatically debugs Kubernetes issues by:
1. Detecting alert patterns
2. Gathering contextual information
3. Analyzing with AI
4. Suggesting remediation actions

## 🔍 Agent's Thinking Process

### Step 1: Alert Detection
```
Alert: "Pod payment-service-7d9f8b6c5-x2n4m is in CrashLoopBackOff state"
   ↓
Pattern Match: pod_crash (regex: "CrashLoopBackOff")
```

### Step 2: Context Gathering
The agent automatically queries Kubernetes for:
- **Pod Status**: CrashLoopBackOff, 6 restarts
- **Pod Logs**: Found "ERROR: Configuration file /config/app.conf not found!"
- **Pod Events**: Multiple restart events
- **Pod Description**: Controlled by ReplicaSet (safe to restart)

### Step 3: Root Cause Analysis
```
Logs Analysis → Missing config file → Configuration issue
   ↓
Confidence: HIGH (explicit error message)
```

### Step 4: Resolution Strategy
The agent evaluated multiple strategies:

| Action | Confidence | Risk | Reasoning |
|--------|------------|------|-----------|
| Check ConfigMaps | 0.7 | Low | Config error in logs |
| Restart Pod | 0.6 | Low | Managed by controller |
| Manual Investigation | 0.9 | Low | Too many restarts |

### Step 5: AI Analysis
Claude provided:
- Detailed kubectl commands to investigate
- Step-by-step fix instructions
- Automated fix script
- Escalation criteria

## 📊 Key Features Demonstrated

### 1. **Intelligent Pattern Detection**
- Recognized "CrashLoopBackOff" as a pod crash scenario
- Triggered Kubernetes-specific debugging workflow

### 2. **Automated Context Collection**
```python
# The agent automatically gathered:
- get_pod_logs()      # Found the root cause
- get_pod_events()    # Checked restart history
- describe_pod()      # Verified it's safe to restart
```

### 3. **Safety Mechanisms**
- Checked if pod is managed by a controller before suggesting restart
- Respected `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false` setting
- Provided confidence scores for each action

### 4. **Comprehensive Analysis**
The AI provided:
- Root cause identification
- Immediate fix commands
- Investigation commands
- Automation scripts
- Escalation guidelines

## 🛠️ The Fix

The agent correctly identified the missing ConfigMap. The fix was:
```bash
# 1. Create ConfigMap
kubectl create configmap payment-config --from-literal=app.conf='...'

# 2. Mount it to the deployment
kubectl patch deployment payment-service ...

# Result: Pod running successfully ✅
```

## 🎮 How to Run This Demo

1. **Setup Kind cluster**:
   ```bash
   kind create cluster --name oncall-test
   ```

2. **Deploy problematic pod**:
   ```bash
   kubectl apply -f test-deployment.yaml
   ```

3. **Run the agent**:
   ```bash
   cd backend
   uv run python demo_k8s_debug.py
   ```

## 🔄 Decision Tree Implementation

```
Alert Received
   ↓
Is it K8s-related? → Yes → Detect specific type
   ↓                         ↓
   No                    pod_crash
   ↓                         ↓
Standard Analysis      Gather K8s context
                            ↓
                      Analyze logs/events
                            ↓
                      Determine root cause
                            ↓
                      Generate fix actions
                            ↓
                      Execute if allowed
```

## 💡 Key Takeaways

1. **Automated Debugging**: The agent automatically identified the root cause without human intervention
2. **Context-Aware**: It gathered relevant K8s information based on the alert type
3. **Safe Operations**: Included safety checks before suggesting destructive actions
4. **Actionable Output**: Provided exact commands to fix the issue
5. **Audit Trail**: All operations are logged for compliance

## 🚀 Production Considerations

In production with `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`, the agent would:
- Automatically create the missing ConfigMap
- Patch the deployment
- Monitor the pod startup
- Alert only if the automatic fix fails

This demonstrates how AI agents can significantly reduce MTTR (Mean Time To Resolution) for common Kubernetes issues.