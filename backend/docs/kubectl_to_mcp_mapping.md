# kubectl to MCP Server Mapping Guide

This document provides a comprehensive mapping of kubectl commands to their MCP server tool equivalents for the DreamOps platform migration.

## Overview

The Kubernetes MCP server provides a Model Context Protocol interface to Kubernetes clusters, eliminating the need for direct kubectl subprocess calls. This enables better error handling, type safety, and integration with the AGNO agent.

## Installation

```bash
# Install via npm (recommended)
npm install -g @modelcontextprotocol/server-kubernetes

# Or use Docker
docker run -d --name k8s-mcp-server \
  -v ~/.kube:/home/node/.kube \
  -p 8085:8085 \
  modelcontextprotocol/kubernetes-server
```

## MCP Server Tools Available

The Kubernetes MCP server exposes the following tools:

1. **kubernetes_get_pods** - List pods in a namespace
2. **kubernetes_get_pod** - Get details of a specific pod
3. **kubernetes_get_deployments** - List deployments
4. **kubernetes_get_deployment** - Get specific deployment details
5. **kubernetes_get_services** - List services
6. **kubernetes_get_logs** - Get pod logs
7. **kubernetes_describe_resource** - Describe any resource
8. **kubernetes_apply_manifest** - Apply YAML manifests
9. **kubernetes_delete_resource** - Delete resources
10. **kubernetes_scale_deployment** - Scale deployments
11. **kubernetes_rollout_restart** - Restart deployments
12. **kubernetes_exec_command** - Execute commands in pods
13. **kubernetes_port_forward** - Port forwarding
14. **kubernetes_get_events** - Get cluster events
15. **kubernetes_top_nodes** - Get node metrics
16. **kubernetes_top_pods** - Get pod metrics

## Command Mappings

### Read Operations (Low Risk)

#### Get Pods
```python
# OLD: kubectl command
subprocess.run(["kubectl", "get", "pods", "-n", namespace, "-o", "json"])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_get_pods', {
    'namespace': namespace,
    'output': 'json'
})
```

#### Get Specific Pod
```python
# OLD: kubectl command
subprocess.run(["kubectl", "get", "pod", pod_name, "-n", namespace, "-o", "json"])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_get_pod', {
    'name': pod_name,
    'namespace': namespace,
    'output': 'json'
})
```

#### Get Pod Logs
```python
# OLD: kubectl command
subprocess.run(["kubectl", "logs", pod_name, "-n", namespace, "--tail=100"])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_get_logs', {
    'pod': pod_name,
    'namespace': namespace,
    'tail': 100
})
```

#### Describe Pod
```python
# OLD: kubectl command
subprocess.run(["kubectl", "describe", "pod", pod_name, "-n", namespace])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_describe_resource', {
    'kind': 'pod',
    'name': pod_name,
    'namespace': namespace
})
```

#### Get Deployments
```python
# OLD: kubectl command
subprocess.run(["kubectl", "get", "deployments", "-n", namespace, "-o", "json"])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_get_deployments', {
    'namespace': namespace,
    'output': 'json'
})
```

#### Get Events
```python
# OLD: kubectl command
subprocess.run(["kubectl", "get", "events", "--field-selector", "reason=OOMKilling"])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_get_events', {
    'field_selector': 'reason=OOMKilling',
    'namespace': namespace  # optional, omit for all namespaces
})
```

#### Top Pods (Metrics)
```python
# OLD: kubectl command
subprocess.run(["kubectl", "top", "pods", "-n", namespace])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_top_pods', {
    'namespace': namespace
})
```

### Write Operations (Medium/High Risk)

#### Delete Pod
```python
# OLD: kubectl command
subprocess.run(["kubectl", "delete", "pod", pod_name, "-n", namespace])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_delete_resource', {
    'kind': 'pod',
    'name': pod_name,
    'namespace': namespace,
    'grace_period': 30  # optional
})
```

#### Scale Deployment
```python
# OLD: kubectl command
subprocess.run(["kubectl", "scale", "deployment", deployment_name, "--replicas=3", "-n", namespace])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_scale_deployment', {
    'name': deployment_name,
    'namespace': namespace,
    'replicas': 3
})
```

#### Rollout Restart
```python
# OLD: kubectl command
subprocess.run(["kubectl", "rollout", "restart", "deployment", deployment_name, "-n", namespace])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_rollout_restart', {
    'kind': 'deployment',
    'name': deployment_name,
    'namespace': namespace
})
```

#### Rollout Undo
```python
# OLD: kubectl command
subprocess.run(["kubectl", "rollout", "undo", "deployment", deployment_name, "-n", namespace])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_rollout_undo', {
    'kind': 'deployment',
    'name': deployment_name,
    'namespace': namespace,
    'to_revision': 0  # optional, 0 means previous revision
})
```

#### Apply Manifest
```python
# OLD: kubectl command
subprocess.run(["kubectl", "apply", "-f", "-"], input=yaml_content)

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_apply_manifest', {
    'manifest': yaml_content,
    'namespace': namespace  # optional, uses manifest namespace if specified
})
```

#### Patch Deployment
```python
# OLD: kubectl command
subprocess.run(["kubectl", "patch", "deployment", name, "--type", "json", "-p", json_patch])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_patch_resource', {
    'kind': 'deployment',
    'name': name,
    'namespace': namespace,
    'patch': json_patch,
    'patch_type': 'json'  # or 'merge' or 'strategic'
})
```

#### Set Image
```python
# OLD: kubectl command
subprocess.run(["kubectl", "set", "image", "deployment/name", "container=image:tag"])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_set_image', {
    'kind': 'deployment',
    'name': name,
    'namespace': namespace,
    'container': 'container',
    'image': 'image:tag'
})
```

### Complex Operations

#### Delete Pods by Label Selector
```python
# OLD: kubectl command
subprocess.run(["kubectl", "delete", "pods", "-l", "app=myapp", "-n", namespace])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_delete_resource', {
    'kind': 'pod',
    'namespace': namespace,
    'label_selector': 'app=myapp'
})
```

#### Execute Command in Pod
```python
# OLD: kubectl command
subprocess.run(["kubectl", "exec", pod_name, "-n", namespace, "--", "command", "args"])

# NEW: MCP tool call
await mcp_client.call_tool('kubernetes_exec_command', {
    'pod': pod_name,
    'namespace': namespace,
    'command': ['command', 'args'],
    'container': container_name  # optional
})
```

## Implementation Pattern

### Before (Direct kubectl)
```python
async def _execute_k8s_command(self, args: list[str]) -> dict[str, Any]:
    cmd = ["kubectl"]
    if self.context:
        cmd.extend(["--context", self.context])
    cmd.extend(args)
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    return {
        "success": process.returncode == 0,
        "output": stdout.decode() if process.returncode == 0 else stderr.decode()
    }
```

### After (MCP Server)
```python
async def _execute_k8s_command(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    # Add context if configured
    if self.context and 'context' not in params:
        params['context'] = self.context
    
    try:
        result = await self.mcp_client.call_tool(tool_name, params)
        return {
            "success": True,
            "output": result.get('content', [{}])[0].get('text', ''),
            "tool": tool_name,
            "params": params
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "tool": tool_name,
            "params": params
        }
```

## Error Handling

The MCP server provides structured error responses:

```python
try:
    result = await mcp_client.call_tool('kubernetes_delete_resource', {
        'kind': 'pod',
        'name': 'nonexistent-pod',
        'namespace': 'default'
    })
except MCPError as e:
    # Handle specific MCP errors
    if e.code == 'RESOURCE_NOT_FOUND':
        logger.warning(f"Pod not found: {e.message}")
    elif e.code == 'PERMISSION_DENIED':
        logger.error(f"No permission to delete pod: {e.message}")
    else:
        logger.error(f"MCP error: {e}")
```

## Context Management

The MCP server supports multiple Kubernetes contexts:

```python
# List available contexts
contexts = await mcp_client.call_tool('kubernetes_list_contexts', {})

# Switch context
await mcp_client.call_tool('kubernetes_use_context', {
    'context': 'production-cluster'
})

# Execute with specific context
await mcp_client.call_tool('kubernetes_get_pods', {
    'namespace': 'default',
    'context': 'staging-cluster'  # Override default context
})
```

## Migration Checklist

- [ ] Replace all `subprocess.run(['kubectl', ...])` calls
- [ ] Replace all `asyncio.create_subprocess_exec('kubectl', ...)` calls
- [ ] Replace all `os.system('kubectl ...')` calls
- [ ] Update error handling to use MCP error types
- [ ] Add proper parameter validation before MCP calls
- [ ] Test all operations with MCP server
- [ ] Update documentation and examples
- [ ] Remove kubectl binary dependency

## Benefits of MCP Server Approach

1. **Type Safety**: Structured parameters instead of string parsing
2. **Better Error Handling**: Specific error codes and messages
3. **No Shell Injection**: Parameters are properly escaped
4. **Performance**: Connection pooling and caching
5. **Observability**: Built-in metrics and tracing
6. **Multi-cluster Support**: Easy context switching
7. **Streaming Support**: Real-time log and event streaming
8. **Validation**: Client-side parameter validation

## Testing the Migration

1. **Unit Tests**: Mock MCP client responses
2. **Integration Tests**: Test against real MCP server
3. **End-to-End Tests**: Full incident response scenarios
4. **Performance Tests**: Ensure latency is acceptable
5. **Error Scenarios**: Test all failure modes

## Troubleshooting

### MCP Server Not Available
```python
# Fallback mechanism (temporary during migration)
if not self.mcp_client.is_connected():
    logger.warning("MCP server not available, falling back to kubectl")
    # Use legacy kubectl method
```

### Performance Issues
- Enable MCP server caching
- Use batch operations where possible
- Monitor MCP server metrics

### Authentication Issues
- Ensure kubeconfig is accessible to MCP server
- Check service account permissions
- Verify context configuration