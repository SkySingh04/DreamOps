# Kubernetes MCP Server Integration Guide

This guide explains how to use the enhanced Kubernetes MCP integration that enables actual command execution in YOLO and Approval modes.

## Overview

The enhanced Kubernetes integration now supports:
- **Actual command execution** via kubectl or Kubernetes MCP server
- **Risk assessment** for all kubectl commands
- **YOLO mode** - Auto-executes low/medium risk commands with high confidence
- **Approval mode** - Requests approval before executing commands
- **Plan mode** - Shows what commands would be executed without running them
- **Command verification** - Verifies actions were successful after execution
- **Circuit breaker** - Prevents repeated failures from causing more damage

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  PagerDuty Alert│────▶│ Enhanced Agent   │────▶│ Claude AI       │
└─────────────────┘     │                  │     │ (Analysis)      │
                        └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │   K8s MCP Integration    │
                    ├──────────────────────────┤
                    │ • Risk Assessment        │
                    │ • Command Generation     │
                    │ • Execution (kubectl)    │
                    │ • Verification          │
                    └──────────────────────────┘
```

## Configuration

### 1. Enable Destructive Operations (Required for YOLO Mode)

```env
# In your .env file
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true  # Allow pod restarts, scaling, etc.
```

### 2. Optional: Use Kubernetes MCP Server

If you have the Kubernetes MCP server installed:

```env
K8S_USE_MCP_SERVER=true
K8S_MCP_SERVER_PATH=/path/to/kubernetes-mcp-server
K8S_MCP_SERVER_HOST=localhost
K8S_MCP_SERVER_PORT=8085
```

### 3. Configure Kubernetes Context

```env
K8S_CONFIG_PATH=/path/to/kubeconfig
K8S_CONTEXT=your-cluster-context
```

## AI Modes

### YOLO Mode 🚀

In YOLO mode, the agent will:
1. Analyze the incident with Claude AI
2. Generate resolution actions
3. **Automatically execute** actions if:
   - Confidence score ≥ 0.8 for low/medium risk commands
   - Confidence score ≥ 0.9 for high risk commands
4. Verify the actions worked
5. Report results

Example:
```python
from src.oncall_agent.agent_enhanced import EnhancedOncallAgent
from src.oncall_agent.api.schemas import AIMode

agent = EnhancedOncallAgent(ai_mode=AIMode.YOLO)
result = await agent.handle_pager_alert(alert, auto_remediate=True)
```

### Approval Mode ✅

In Approval mode:
1. Analyze the incident
2. Generate resolution actions
3. **Show exact kubectl commands** that would be executed
4. Wait for approval (currently auto-approves low risk)
5. Execute approved commands
6. Verify and report

### Plan Mode 📋

In Plan mode:
1. Analyze the incident
2. Generate resolution actions
3. **Show command preview** without executing
4. Display risk assessment for each command

## Risk Assessment

Commands are classified into three risk levels:

### Low Risk (Auto-executed in YOLO mode)
- `kubectl get`, `describe`, `logs`
- Read-only operations
- No data modification

### Medium Risk (Auto-executed with high confidence)
- `kubectl scale`, `rollout`, `restart`
- `kubectl label`, `annotate`
- Modifies resources but reversible

### High Risk (Requires very high confidence or manual approval)
- `kubectl delete`, `apply`, `create`
- `kubectl exec`, `port-forward`
- Any operation on system namespaces (kube-*)
- Any operation with `--all` or `--all-namespaces`

## Command Execution Flow

1. **Risk Assessment**
   ```python
   risk_assessment = {
       "risk_level": "medium",
       "command_type": "scale",
       "affects_all": False,
       "forbidden": False,
       "reason": "Modifies resource capacity"
   }
   ```

2. **Confidence Check**
   - Actions with confidence < 0.7 are skipped
   - Higher risk requires higher confidence

3. **Mode-Based Decision**
   - YOLO: Execute if confidence meets threshold
   - Approval: Request approval via callback
   - Plan: Never execute, only preview

4. **Execution**
   - Commands are logged for audit trail
   - Output captured for analysis
   - Errors handled gracefully

5. **Verification**
   - Pod restarts: Check new pod is running
   - Scaling: Verify replica count matches
   - Rollback: Check deployment status

## Usage Examples

### 1. Test with Sample Alerts

```bash
cd backend
python test_yolo_mode.py
```

This will simulate various Kubernetes issues and show how the agent handles them.

### 2. Test with Real Kubernetes Issues

```bash
# Create some broken pods
./fuck_kubernetes.sh 1  # Create CrashLoopBackOff

# Run the agent to auto-fix
python test_yolo_mode.py --fuck-kubernetes
```

### 3. Integration with API

```python
# In your alert handler
from src.oncall_agent.agent_enhanced import EnhancedOncallAgent
from src.oncall_agent.api.schemas import AIMode

# Create agent with desired mode
agent = EnhancedOncallAgent(ai_mode=AIMode.YOLO)
await agent.connect_integrations()

# Handle alert
result = await agent.handle_pager_alert(
    alert,
    auto_remediate=True  # Enable auto-remediation
)

# Check results
if result['execution_results']:
    print(f"Executed {result['execution_results']['actions_successful']} actions successfully")
```

## Resolution Actions

The agent can perform these automated resolutions:

### Pod Issues
- **restart_pod**: Delete pod to trigger fresh start
- **check_configmaps_secrets**: Verify configs are mounted
- **check_dependencies**: Check dependent services

### Resource Issues
- **scale_deployment**: Add more replicas
- **increase_memory_limit**: Patch memory limits
- **increase_cpu_limits**: Patch CPU limits

### Deployment Issues
- **rollback_deployment**: Undo to previous version
- **check_resource_quotas**: Verify quotas not exceeded

### Service Issues
- **deploy_missing_pods**: Create pods for service
- **fix_pod_issues**: Resolve pod problems
- **verify_service_config**: Check selectors

## Safety Features

### Circuit Breaker
- Opens after 5 consecutive failures
- Prevents further auto-execution
- Resets after 5 minutes or 2 successes

### Audit Logging
All commands are logged with:
- Timestamp
- Command executed
- Risk assessment
- Success/failure status
- User/system that triggered

### Forbidden Commands
These commands are never auto-executed:
- `kubectl delete namespace`
- `kubectl delete node`
- `kubectl delete pv/pvc`

## Monitoring

### Execution History
```python
history = agent.agent_executor.get_execution_history()
for entry in history:
    print(f"{entry['timestamp']}: {entry['action']['action_type']} - {entry.get('result', {}).get('success')}")
```

### Audit Log
```python
audit_log = agent.k8s_mcp.get_audit_log()
for entry in audit_log:
    print(f"{entry['timestamp']}: {' '.join(entry['command'])} - {entry['status']}")
```

## Troubleshooting

### Commands Not Executing
1. Check `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true`
2. Verify kubectl context is correct
3. Check agent mode (not in PLAN mode)
4. Review confidence scores in logs

### MCP Server Connection Issues
1. Verify server binary path is correct
2. Check KUBECONFIG environment variable
3. Review MCP server logs
4. Fall back to direct kubectl

### Verification Failures
1. Increase wait time for pod startup
2. Check resource labels match
3. Verify namespace is correct

## Best Practices

1. **Start with Plan Mode** to understand what commands would be executed
2. **Use Approval Mode** for production environments initially
3. **Enable YOLO Mode** only after testing thoroughly
4. **Monitor execution history** regularly
5. **Set up alerts** for circuit breaker trips
6. **Review audit logs** for all executed commands

## Security Considerations

1. **Limit RBAC permissions** for the service account
2. **Use read-only context** for non-production testing
3. **Enable audit logging** in Kubernetes
4. **Restrict namespace access** where possible
5. **Review all high-risk commands** before enabling YOLO mode

## Future Enhancements

- Slack/Teams integration for approval workflows
- Custom risk assessment rules
- Rollback tracking and automated rollback on failure
- Integration with GitOps for configuration changes
- Machine learning for confidence score improvement