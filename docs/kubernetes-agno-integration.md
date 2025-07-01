# Kubernetes Agno MCP Integration Guide

## Overview

The DreamOps platform now supports Kubernetes incident response using the Agno framework with MCP (Model Context Protocol) integration. This allows for:

- **Remote Kubernetes Connections**: Connect to any K8s cluster without local kubeconfig
- **Automated Incident Response**: AI-powered remediation using Claude/GPT-4
- **Multi-Cluster Support**: Manage multiple clusters from a single interface
- **YOLO Mode**: Fully autonomous remediation when enabled

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   PagerDuty     │────▶│  DreamOps Agent  │────▶│   Agno Agent    │
│   Alert         │     │                  │     │   with MCP      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                 │                         │
                                 ▼                         ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  K8s Credentials │     │  K8s MCP Server │
                        │     Service      │     │  (manusa/k8s)   │
                        └──────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │   Kubernetes    │
                                                 │    Cluster      │
                                                 └─────────────────┘
```

## Features

### 1. Remote Kubernetes Connection

Connect to any Kubernetes cluster without requiring local kubeconfig:

```python
# Service Account Authentication
credentials = K8sCredentials(
    auth_method=AuthMethod.SERVICE_ACCOUNT,
    cluster_endpoint="https://k8s-cluster.example.com:6443",
    cluster_name="production",
    service_account_token="your-sa-token",
    ca_certificate="base64-encoded-ca-cert",
    namespace="default"
)

# Kubeconfig Upload
credentials = K8sCredentials(
    auth_method=AuthMethod.KUBECONFIG,
    cluster_endpoint="https://k8s-cluster.example.com:6443",
    cluster_name="staging",
    kubeconfig_data="<full kubeconfig yaml content>",
    namespace="default"
)

# Client Certificate
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

### 2. Agno Agent Integration

The integration uses Agno's MCPTools for seamless K8s operations:

```python
from agno.tools.mcp import MCPTools
from agno.agent import Agent

# Initialize with MCP tools
async with MCPTools(command="kubernetes-mcp-server") as k8s_tools:
    agent = Agent(
        name="K8sIncidentResponseAgent",
        model=OpenAIChat(id="gpt-4"),
        tools=[k8s_tools],
        instructions=k8s_instructions
    )
    
    # Process incident
    result = await agent.run(incident_query)
```

### 3. Automated Incident Response

The agent handles common Kubernetes incidents:

- **Pod CrashLoopBackOff**: Analyzes logs, identifies root cause, restarts pods
- **ImagePullBackOff**: Checks image availability, updates credentials
- **OOMKilled**: Analyzes memory usage, increases limits
- **Service Down**: Checks endpoints, restarts pods
- **High Resource Usage**: Identifies culprits, scales or restarts

### 4. YOLO Mode

When enabled, the agent executes remediation automatically:

```bash
# Enable YOLO mode
export K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true
```

In YOLO mode:
- No human approval required
- Executes fixes immediately
- Logs all actions for audit
- Provides rollback capability

## API Endpoints

### Test Agno Connection
```http
POST /api/v1/kubernetes/agno/test-connection
{
  "use_remote_cluster": false,
  "test_query": "List all pods in default namespace"
}
```

### Connect Remote Cluster
```http
POST /api/v1/kubernetes/agno/connect-cluster
{
  "auth_method": "service_account",
  "cluster_name": "production",
  "cluster_endpoint": "https://k8s.example.com:6443",
  "service_account_token": "...",
  "ca_certificate": "...",
  "namespace": "default"
}
```

### Process Incident
```http
POST /api/v1/kubernetes/agno/process-incident
{
  "alert_id": "inc-123",
  "title": "Pod CrashLoopBackOff",
  "description": "Pod app-123 is crashing",
  "severity": "high",
  "metadata": {
    "cluster": "production",
    "namespace": "default",
    "pod": "app-123"
  }
}
```

### List Clusters
```http
GET /api/v1/kubernetes/agno/clusters
```

### Test Remediation
```http
POST /api/v1/kubernetes/agno/test-remediation
{
  "scenario": "pod_crash",
  "cluster_name": "staging",
  "namespace": "test"
}
```

## Configuration

### Environment Variables

```bash
# Kubernetes Integration
K8S_ENABLED=true
K8S_MCP_SERVER_URL=http://localhost:8080  # Optional, for remote MCP server
K8S_MCP_SERVER_PATH=kubernetes-mcp-server  # Path to local MCP server binary
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false    # Enable YOLO mode

# API Keys (for Agno)
ANTHROPIC_API_KEY=your-anthropic-key       # For Claude models
OPENAI_API_KEY=your-openai-key            # For GPT models
```

### MCP Server Setup

1. **Local MCP Server** (Default):
```bash
# Install kubernetes-mcp-server
npm install -g @modelcontextprotocol/server-kubernetes

# Or use the manusa implementation
git clone https://github.com/manusa/kubernetes-mcp-server
cd kubernetes-mcp-server
./gradlew build
```

2. **Remote MCP Server**:
```bash
# Run MCP server on a dedicated host
docker run -d \
  -p 8080:8080 \
  -v ~/.kube:/home/node/.kube \
  manusa/kubernetes-mcp-server
```

## Testing

### Run Integration Tests
```bash
cd backend
python test_agno_k8s_integration.py
```

### Test Scenarios
1. Basic MCP connection
2. Remote cluster connection
3. Incident response workflow
4. YOLO mode remediation
5. Multi-cluster support

## Security Considerations

### Credential Storage
- All credentials are encrypted using Fernet encryption
- Stored in PostgreSQL with user isolation
- Automatic credential rotation support

### Access Control
- Service accounts should have minimal required permissions
- Use RBAC to limit MCP server access
- Enable audit logging for all operations

### Network Security
- Always use TLS for cluster connections
- Support for proxy configurations
- Certificate validation enabled by default

## Troubleshooting

### MCP Server Connection Issues
```bash
# Check if MCP server is running
curl http://localhost:8080/mcp

# View MCP server logs
docker logs kubernetes-mcp-server
```

### Authentication Failures
- Verify service account has correct permissions
- Check certificate expiration
- Ensure cluster endpoint is reachable

### Agent Not Responding
- Check API key configuration
- Verify MCP tools are available
- Review agent logs for errors

## Best Practices

1. **Use Service Accounts**: Prefer service account authentication over kubeconfig
2. **Limit Permissions**: Grant minimal required RBAC permissions
3. **Test in Staging**: Always test remediation in non-production first
4. **Monitor Actions**: Review agent action logs regularly
5. **Set Confidence Thresholds**: Adjust based on your risk tolerance

## Future Enhancements

- Cloud provider authentication (EKS, GKE, AKS)
- Helm chart management via MCP
- Custom resource support
- Prometheus metrics integration
- GitOps workflow integration