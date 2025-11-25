# Kubernetes Integration Guide

Complete guide for Kubernetes integration with DreamOps, including MCP server setup, auto-discovery, remote cluster connections, and kubectl-to-MCP migration.

## Table of Contents

- [Overview](#overview)
- [Integration Options](#integration-options)
- [MCP Server Setup](#mcp-server-setup)
- [Enhanced Integration (Auto-Discovery)](#enhanced-integration-auto-discovery)
- [Agno Framework Integration](#agno-framework-integration)
- [kubectl to MCP Migration](#kubectl-to-mcp-migration)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Overview

DreamOps integrates with Kubernetes using the Model Context Protocol (MCP) for secure, type-safe cluster operations. The integration supports:

- **Local Cluster**: Connect using local kubeconfig
- **Remote Clusters**: Connect to any K8s cluster without local kubeconfig
- **Multi-Cluster Support**: Manage multiple clusters from a single interface
- **YOLO Mode**: Fully autonomous remediation when enabled
- **Auto-Discovery**: Automatic context discovery from kubeconfig

## Integration Options

### 1. Standard Kubernetes Integration

Basic integration using local kubeconfig:

```env
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false
```

### 2. Enhanced Integration with Auto-Discovery

Intelligent cluster discovery with multi-context support:

```env
K8S_ENHANCED_ENABLED=true
K8S_ENHANCED_MULTI_CONTEXT=true
K8S_ENHANCED_AUTO_DISCOVER=true
K8S_ENHANCED_PERMISSION_CHECK=true
```

### 3. MCP Server Integration

Direct communication with Kubernetes MCP server:

```env
K8S_MCP_SERVER_URL=http://localhost:8080
K8S_MCP_COMMAND=npx -y kubernetes-mcp-server@latest
```

### 4. Agno Framework (Remote Clusters)

For remote Kubernetes management without local kubeconfig:

```env
AGNO_ENABLED=true
AGNO_GITHUB_TOKEN=ghp_your_github_token
```

## MCP Server Setup

### Installation

```bash
# Install via npm
npm install -g @modelcontextprotocol/server-kubernetes

# Or using pnpm
pnpm install kubernetes-mcp-server

# Or use the setup script
./setup-kubernetes-mcp.sh
```

### Starting the MCP Server

```bash
# HTTP Streaming Mode (recommended for API server)
pnpm exec kubernetes-mcp-server --http-port 8080

# SSE Mode
pnpm exec kubernetes-mcp-server --sse-port 8080

# STDIO Mode (default)
pnpm exec kubernetes-mcp-server
```

### Available MCP Tools

**Read Operations:**
- `pods_list` - List all pods
- `pods_list_in_namespace` - List pods in a namespace
- `pods_get` - Get pod details
- `pods_log` - Get pod logs
- `pods_top` - Get pod resource usage
- `resources_list` - List Kubernetes resources
- `resources_get` - Get resource details
- `events_list` - List events
- `namespaces_list` - List namespaces
- `configuration_view` - View kubeconfig

**Write Operations (when enabled):**
- `pods_delete` - Delete a pod
- `pods_exec` - Execute commands in pods
- `pods_run` - Run new pods
- `resources_create_or_update` - Create/update resources
- `resources_delete` - Delete resources
- `helm_install`, `helm_list`, `helm_uninstall` - Helm operations

## Enhanced Integration (Auto-Discovery)

### Features

1. **Auto-Discovery**: Discovers all available contexts from:
   - `~/.kube/config` (default location)
   - `$KUBECONFIG` environment variable
   - Custom kubeconfig paths
   - In-cluster service account (when running inside K8s)

2. **Multi-Context Support**:
   - Switch between contexts dynamically
   - Per-context namespace configuration
   - Context-specific permission verification

3. **Permission Verification**:
   - Check read permissions (pods, services, deployments, etc.)
   - Verify write permissions (with dry-run)
   - Identify missing RBAC permissions

4. **Cluster Information**:
   - Node details (count, status, version, OS)
   - Resource counts (pods, services, deployments)
   - Total CPU and memory capacity
   - Namespace listing

### Frontend Configuration UI

Located at `/integrations/kubernetes`:

1. **Context Discovery Tab**: Lists all discovered contexts with one-click testing
2. **Saved Configurations Tab**: Manage multiple cluster configurations
3. **Cluster Details Tab**: Real-time cluster overview and metrics

## Agno Framework Integration

For connecting to remote clusters without local kubeconfig.

### Architecture

```
PagerDuty Alert → DreamOps Agent → Agno Agent with MCP → K8s Cluster
```

### Authentication Methods

**Service Account:**
```python
credentials = K8sCredentials(
    auth_method=AuthMethod.SERVICE_ACCOUNT,
    cluster_endpoint="https://k8s-cluster.example.com:6443",
    cluster_name="production",
    service_account_token="your-sa-token",
    ca_certificate="base64-encoded-ca-cert",
    namespace="default"
)
```

**Kubeconfig Upload:**
```python
credentials = K8sCredentials(
    auth_method=AuthMethod.KUBECONFIG,
    cluster_endpoint="https://k8s-cluster.example.com:6443",
    cluster_name="staging",
    kubeconfig_data="<full kubeconfig yaml content>",
    namespace="default"
)
```

**Client Certificate:**
```python
credentials = K8sCredentials(
    auth_method=AuthMethod.CLIENT_CERT,
    cluster_endpoint="https://k8s-cluster.example.com:6443",
    cluster_name="dev",
    client_certificate="base64-encoded-client-cert",
    client_key="base64-encoded-client-key",
    ca_certificate="base64-encoded-ca-cert",
    namespace="default"
)
```

### Automated Incident Response

The agent handles common Kubernetes incidents:

- **Pod CrashLoopBackOff**: Analyzes logs, identifies root cause, restarts pods
- **ImagePullBackOff**: Checks image availability, updates credentials
- **OOMKilled**: Analyzes memory usage, increases limits
- **Service Down**: Checks endpoints, restarts pods
- **High Resource Usage**: Identifies culprits, scales or restarts

## kubectl to MCP Migration

### Command Mappings

| kubectl Command | MCP Tool | Parameters |
|----------------|----------|------------|
| `kubectl get pods` | `kubernetes_get_pods` | `namespace`, `output` |
| `kubectl get pod NAME` | `kubernetes_get_pod` | `name`, `namespace` |
| `kubectl describe pod` | `kubernetes_describe_resource` | `kind`, `name`, `namespace` |
| `kubectl logs` | `kubernetes_get_logs` | `pod`, `namespace`, `tail` |
| `kubectl get deployments` | `kubernetes_get_deployments` | `namespace` |
| `kubectl scale` | `kubernetes_scale_deployment` | `name`, `namespace`, `replicas` |
| `kubectl rollout restart` | `kubernetes_rollout_restart` | `kind`, `name`, `namespace` |
| `kubectl delete` | `kubernetes_delete_resource` | `kind`, `name`, `namespace` |
| `kubectl apply -f` | `kubernetes_apply_manifest` | `manifest`, `namespace` |
| `kubectl exec` | `kubernetes_exec_command` | `pod`, `namespace`, `command` |

### Before (Direct kubectl):
```python
result = subprocess.run(["kubectl", "get", "pods", "-n", "default"], capture_output=True)
```

### After (MCP):
```python
result = await mcp_client.call_tool('kubernetes_get_pods', {
    'namespace': 'default',
    'output': 'json'
})
```

### Benefits of MCP Approach

1. **Type Safety**: Structured parameters instead of string parsing
2. **Better Error Handling**: Specific error codes and messages
3. **No Shell Injection**: Parameters are properly escaped
4. **Performance**: Connection pooling and caching
5. **Observability**: Built-in metrics and tracing
6. **Multi-cluster Support**: Easy context switching

## API Endpoints

### Discovery and Configuration

- `GET /api/v1/integrations/kubernetes/discover` - Discover available contexts
- `POST /api/v1/integrations/kubernetes/test` - Test cluster connection
- `GET /api/v1/integrations/kubernetes/configs` - List saved configurations
- `POST /api/v1/integrations/kubernetes/configs` - Save new configuration
- `PUT /api/v1/integrations/kubernetes/configs/{id}` - Update configuration
- `DELETE /api/v1/integrations/kubernetes/configs/{id}` - Delete configuration
- `GET /api/v1/integrations/kubernetes/health` - Get integration health
- `POST /api/v1/integrations/kubernetes/verify-permissions` - Verify RBAC permissions
- `GET /api/v1/integrations/kubernetes/cluster-info` - Get cluster details

### Agno Framework Endpoints

- `POST /api/v1/kubernetes/agno/test-connection` - Test Agno connection
- `POST /api/v1/kubernetes/agno/connect-cluster` - Connect remote cluster
- `POST /api/v1/kubernetes/agno/process-incident` - Process incident
- `GET /api/v1/kubernetes/agno/clusters` - List connected clusters
- `POST /api/v1/kubernetes/agno/test-remediation` - Test remediation scenario

## Configuration

### Environment Variables

```bash
# Basic Kubernetes Integration
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false  # Enable for YOLO mode

# MCP Server
K8S_MCP_SERVER_URL=http://localhost:8080
K8S_MCP_SERVER_PATH=kubernetes-mcp-server

# Agno Framework
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
```

### YOLO Mode

When enabled, the agent executes remediation automatically without human approval:

```bash
export K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
```

In YOLO mode:
- No human approval required
- Executes fixes immediately
- Logs all actions for audit
- Provides rollback capability

## Security Considerations

### RBAC Verification
- The integration verifies permissions before attempting operations
- Check read permissions (pods, services, deployments, etc.)
- Verify write permissions (with dry-run)

### Credential Storage
- All credentials are encrypted using Fernet encryption
- Stored in PostgreSQL with user isolation
- Automatic credential rotation support

### Best Practices
1. **Use Service Accounts**: Prefer service account authentication over kubeconfig
2. **Limit Permissions**: Grant minimal required RBAC permissions
3. **Test in Staging**: Always test remediation in non-production first
4. **Monitor Actions**: Review agent action logs regularly
5. **Set Confidence Thresholds**: Adjust based on your risk tolerance

## Troubleshooting

### No Contexts Found
- Ensure you have a valid kubeconfig file at `~/.kube/config`
- Check if `KUBECONFIG` environment variable is set correctly
- Verify kubectl works: `kubectl config get-contexts`

### Connection Failed
- Check if the cluster is accessible
- Verify your credentials are not expired
- Ensure the cluster endpoint is reachable from your network

### MCP Server Connection Issues
```bash
# Check if MCP server is running
curl http://localhost:8080/mcp

# View MCP server logs
docker logs kubernetes-mcp-server
```

### Permission Errors
- The integration will show which permissions are missing
- Work with your cluster admin to grant necessary RBAC permissions
- For read-only access, only basic view permissions are needed

### Authentication Failures
- Verify service account has correct permissions
- Check certificate expiration
- Ensure cluster endpoint is reachable

## Testing

### Run Integration Tests
```bash
cd backend
uv run python test_k8s_enhanced.py
uv run python test_agno_k8s_integration.py
```

### Test Scenarios
1. Basic MCP connection
2. Remote cluster connection
3. Incident response workflow
4. YOLO mode remediation
5. Multi-cluster support
