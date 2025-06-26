# YOLO Mode Guide

YOLO Mode is DreamOps' autonomous remediation system that allows the AI agent to automatically execute fixes without human approval. This guide covers configuration, capabilities, and safety considerations.

## Overview

YOLO Mode (You Only Live Once) enables:
- **Autonomous Remediation**: Execute fixes automatically without waiting for human approval
- **Confidence-Based Actions**: All actions are executed regardless of confidence level
- **Pattern-Based Resolution**: Intelligent pattern matching for common incident types
- **Safety Mechanisms**: Built-in safeguards and rollback capabilities

## Prerequisites

1. **Working Kubernetes Cluster**: Required for most remediation actions
2. **Valid API Keys**: Anthropic API key and service integration credentials
3. **RBAC Permissions**: Proper kubectl permissions for cluster operations
4. **Testing Environment**: Recommended to test in staging before production

## Configuration

### Environment Variables

Add these to your `backend/.env` file:

```env
# Enable YOLO Mode
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
K8S_ENABLED=true

# Core configuration
ANTHROPIC_API_KEY=your-anthropic-key
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default

# Optional: Specific namespace for YOLO operations
YOLO_TARGET_NAMESPACE=production
```

### Quick Setup Script

```bash
cd backend
./enable_yolo_mode.sh  # Sets K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
```

### Manual Configuration

1. **Edit `backend/.env`**:
   ```env
   K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
   K8S_ENABLED=true
   ```

2. **Start the API server**:
   ```bash
   uv run python api_server.py
   ```

3. **Set AI Mode in Frontend**: Toggle to "YOLO" mode in the dashboard

## How YOLO Mode Works

### Workflow Overview

1. **Alert Reception**: PagerDuty webhook triggers the agent
2. **Pattern Detection**: Agent matches alert to known patterns
3. **Generic Fallback**: If no pattern matches, uses generic resolution strategies
4. **Action Generation**: Creates remediation actions with confidence scores
5. **Auto-Execution**: Executes ALL actions regardless of confidence level
6. **Verification**: Confirms fixes were successful
7. **Resolution**: Automatically resolves incidents in PagerDuty

### Pattern Recognition

YOLO Mode recognizes these incident patterns:

- **Pod Errors**: CrashLoopBackOff, ImagePullBackOff, OOMKilled
- **Resource Constraints**: CPU limits, memory limits, disk space
- **Deployment Issues**: Failed rollouts, missing replicas
- **Service Problems**: Endpoint failures, DNS issues
- **Generic Fallback**: Unknown patterns trigger generic pod error resolution

### Action Types

YOLO Mode can execute these action types:

#### Pod Management
- `identify_error_pods`: Find pods in error states
- `restart_error_pods`: Delete pods to force restart
- `get_pod_logs`: Retrieve logs for analysis

#### Resource Management
- `check_resource_constraints`: Monitor CPU/memory usage
- `identify_oom_pods`: Find OOM killed pods
- `increase_memory_limits`: Patch deployments with higher memory limits
- `increase_cpu_limits`: Patch deployments with higher CPU limits

#### Deployment Operations
- `scale_deployment`: Scale deployments up or down
- `rollback_deployment`: Rollback to previous version
- `restart_deployment`: Force deployment restart

#### Service Operations
- `check_service_endpoints`: Verify service connectivity
- `restart_service_pods`: Restart pods backing a service

## Implementation Details

### Resolution Strategies

**Generic Pod Error Resolution**:
```python
async def resolve_generic_pod_errors(self, incident_data: Dict[str, Any]) -> List[ResolutionAction]:
    actions = [
        ResolutionAction(
            action_type="identify_error_pods",
            description="Find pods in error states",
            params={"namespace": self.config.K8S_NAMESPACE},
            confidence=0.9
        ),
        ResolutionAction(
            action_type="restart_error_pods", 
            description="Restart pods in error states",
            params={"force": True},
            confidence=0.8
        )
    ]
    return actions
```

**OOM Kill Resolution**:
```python
async def resolve_oom_kills(self, incident_data: Dict[str, Any]) -> List[ResolutionAction]:
    actions = [
        ResolutionAction(
            action_type="identify_oom_pods",
            description="Find OOM killed pods",
            params={"time_range": "30m"},
            confidence=0.95
        ),
        ResolutionAction(
            action_type="increase_memory_limits",
            description="Increase memory limits for affected deployments", 
            params={"multiplier": 2.0, "min_memory": "512Mi"},
            confidence=0.85
        )
    ]
    return actions
```

### Action Execution

In YOLO mode, action execution logic:

```python
async def _should_auto_remediate(self, actions: List[ResolutionAction]) -> bool:
    """In YOLO mode, always execute if ANY actions are found"""
    if self.config.K8S_ENABLE_DESTRUCTIVE_OPERATIONS:
        return len(actions) > 0  # Execute if any actions exist
    return False
```

### Command Execution Examples

**Restart Failed Pods**:
```bash
# Executed automatically by YOLO mode
kubectl delete pod --selector=app=api-gateway --field-selector=status.phase=Failed
```

**Increase Memory Limits**:
```bash
# Patch deployment with new memory limits
kubectl patch deployment api-gateway --patch '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "api-gateway",
          "resources": {
            "limits": {"memory": "2Gi"},
            "requests": {"memory": "1Gi"}
          }
        }]
      }
    }
  }
}'
```

**Scale Deployment**:
```bash
# Scale deployment to handle increased load
kubectl scale deployment worker --replicas=5
```

## Safety Mechanisms

### Built-in Safeguards

1. **Namespace Isolation**: Operations limited to specified namespaces
2. **Rollback Capability**: Most actions support rollback operations
3. **Verification Steps**: Post-action verification of success
4. **Audit Logging**: Complete logging of all operations
5. **Time Limits**: Operations have maximum execution time

### Rollback Procedures

**Deployment Rollback**:
```python
# Automatic rollback if new deployment fails
await k8s.execute_action("rollback_deployment", {
    "deployment": "api-gateway",
    "revision": "previous"
})
```

**Resource Limit Rollback**:
```python
# Revert resource changes if issues occur
await k8s.execute_action("revert_resource_changes", {
    "deployment": "api-gateway", 
    "backup_spec": original_spec
})
```

### Risk Mitigation

1. **Staging Testing**: Test YOLO mode in staging environments first
2. **Gradual Rollout**: Enable for specific namespaces initially
3. **Monitoring**: Continuous monitoring of YOLO mode actions
4. **Manual Override**: Ability to disable YOLO mode instantly
5. **Incident Escalation**: Automatic escalation for repeated failures

## Configuration Examples

### Development Environment

```env
# Conservative YOLO mode for development
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
K8S_ENABLED=true
K8S_NAMESPACE=development
YOLO_MAX_ACTIONS_PER_INCIDENT=3
YOLO_REQUIRE_CONFIRMATION=false
```

### Staging Environment

```env
# Full YOLO mode for staging testing
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
K8S_ENABLED=true
K8S_NAMESPACE=staging
YOLO_MAX_ACTIONS_PER_INCIDENT=5
YOLO_ENABLE_ROLLBACK=true
```

### Production Environment

```env
# Production YOLO mode with safeguards
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
K8S_ENABLED=true
K8S_NAMESPACE=production
YOLO_MAX_ACTIONS_PER_INCIDENT=3
YOLO_ENABLE_ROLLBACK=true
YOLO_REQUIRE_DOUBLE_CONFIRMATION=true
```

## Testing YOLO Mode

### Using the Test Script

```bash
# Simulate Kubernetes failures
./fuck_kubernetes.sh 1  # Pod crashes
./fuck_kubernetes.sh 3  # OOM kills
./fuck_kubernetes.sh all # All failure types
```

### Manual Testing Steps

1. **Enable YOLO Mode**: Set configuration and restart services
2. **Create Test Incident**: Deploy broken application
3. **Trigger Alert**: Send test alert to PagerDuty webhook
4. **Monitor Execution**: Watch logs for YOLO mode actions
5. **Verify Results**: Confirm incident was resolved automatically

### Test Scenarios

**Pod Crash Test**:
```yaml
# crash-loop-test.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crash-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crash-test
  template:
    metadata:
      labels:
        app: crash-test
    spec:
      containers:
      - name: crasher
        image: busybox
        command: ["sh", "-c", "exit 1"]
```

**OOM Test**:
```yaml
# oom-test.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom-test
  template:
    metadata:
      labels:
        app: oom-test
    spec:
      containers:
      - name: memory-hog
        image: progrium/stress
        resources:
          limits:
            memory: "100Mi"
        command: ["stress"]
        args: ["--vm", "1", "--vm-bytes", "200M"]
```

## Monitoring YOLO Mode

### Key Metrics

- **Success Rate**: Percentage of successfully resolved incidents
- **Resolution Time**: Average time from alert to resolution
- **Action Count**: Number of actions executed per incident
- **Rollback Rate**: Frequency of rollback operations
- **Error Rate**: Failed action attempts

### Log Analysis

Look for these log patterns:

```bash
# YOLO mode activation
grep "🚀 YOLO MODE" /var/log/dreamops/agent.log

# Auto-remediation enabled
grep "🤖 AUTO-REMEDIATION ENABLED" /var/log/dreamops/agent.log

# Action execution
grep "Executing action:" /var/log/dreamops/agent.log

# Success confirmations
grep "✅ Action completed successfully" /var/log/dreamops/agent.log
```

### Alerting

Set up alerts for:
- YOLO mode failures exceeding threshold
- Unusual action execution patterns
- Rollback operations
- Extended resolution times

## Troubleshooting

### Common Issues

**YOLO Mode Not Executing**:
1. Verify `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`
2. Check `K8S_ENABLED=true`
3. Ensure kubectl is configured and working
4. Verify API server is running with correct configuration

**Actions Failing**:
1. Check Kubernetes cluster connectivity
2. Verify RBAC permissions
3. Examine kubectl configuration
4. Review agent logs for error details

**PagerDuty Integration Issues**:
1. Verify `PAGERDUTY_API_KEY` and `PAGERDUTY_USER_EMAIL`
2. Check user permissions in PagerDuty
3. Test API connectivity
4. Review webhook configuration

### Debug Commands

```bash
# Test Kubernetes connectivity
kubectl cluster-info

# Check RBAC permissions
kubectl auth can-i create pods
kubectl auth can-i patch deployments

# Test PagerDuty API
curl -H "Authorization: Token token=YOUR_API_KEY" \
     https://api.pagerduty.com/users

# View recent YOLO mode actions
grep -A 10 -B 10 "YOLO MODE" /var/log/dreamops/agent.log
```

## Best Practices

### Gradual Adoption

1. **Start with Staging**: Enable YOLO mode in staging environments first
2. **Specific Namespaces**: Begin with test or development namespaces
3. **Limited Actions**: Start with low-risk actions like pod restarts
4. **Monitor Closely**: Watch all YOLO mode operations initially
5. **Expand Gradually**: Increase scope as confidence builds

### Production Considerations

1. **Backup Strategies**: Ensure proper backup and recovery procedures
2. **Incident Communication**: Notify teams about YOLO mode operations
3. **Escalation Paths**: Define escalation for YOLO mode failures
4. **Regular Reviews**: Periodic review of YOLO mode effectiveness
5. **Manual Override**: Always maintain manual override capabilities

### Security Guidelines

1. **Least Privilege**: Use minimal required Kubernetes permissions
2. **Audit Trails**: Maintain complete audit logs of all operations
3. **Access Control**: Restrict YOLO mode configuration access
4. **Network Security**: Secure communication channels
5. **Secret Management**: Protect API keys and credentials

## Integration with Other Systems

### PagerDuty Workflow

```
Incident Triggered → YOLO Mode Activated → Actions Executed → Incident Resolved
      ↓                      ↓                    ↓               ↓
  Acknowledge         Add Progress Note    Execute Commands   Resolution Note
```

### Slack Notifications (Planned)

```python
# Future integration for team notifications
await slack.send_message(
    channel="#incidents",
    message="🤖 YOLO Mode resolved incident: Pod OOMKilled → Memory increased to 2Gi"
)
```

### Grafana Integration (Planned)

```python
# Future metrics integration
await grafana.record_metric("yolo_mode_resolution", {
    "incident_type": "oom_kill",
    "resolution_time": 120,  # seconds
    "success": True
})
```

## Advanced Configuration

### Custom Resolution Strategies

```python
# Add custom resolution patterns
CUSTOM_PATTERNS = {
    "database_connection_timeout": {
        "patterns": ["connection timeout", "database unreachable"],
        "actions": ["restart_database_proxy", "scale_database_pool"]
    }
}
```

### Action Prioritization

```python
# Configure action execution order
ACTION_PRIORITY = {
    "identify_error_pods": 1,
    "restart_error_pods": 2, 
    "increase_memory_limits": 3,
    "scale_deployment": 4
}
```

### Conditional Execution

```python
# Execute actions based on conditions
async def should_execute_action(action: ResolutionAction, context: Dict) -> bool:
    if action.action_type == "increase_memory_limits":
        current_memory = context.get("current_memory_usage", 0)
        return current_memory > 0.8  # Only if >80% memory usage
    return True
``` 