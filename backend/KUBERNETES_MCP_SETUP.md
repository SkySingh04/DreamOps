# Kubernetes MCP Server Setup

This project uses the [kubernetes-mcp-server](https://github.com/manusa/kubernetes-mcp-server) by manusa to provide Kubernetes integration through the Model Context Protocol (MCP).

## Installation

```bash
# Install using pnpm
pnpm install kubernetes-mcp-server

# Or run the setup script
./setup-kubernetes-mcp.sh
```

## Starting the MCP Server

The MCP server is automatically started when you run the API server. You can also start it manually:

```bash
# Using the start script
./start-kubernetes-mcp-server.sh

# Or directly with pnpm
pnpm exec kubernetes-mcp-server --http-port 8080
```

## Configuration

The server will automatically use your current kubectl context. Make sure you have:
- Access to a Kubernetes cluster configured for kubectl
- The appropriate RBAC permissions for the operations you want to perform

## Available Operations

The kubernetes-mcp-server provides the following MCP tools:

### Read Operations
- `pods_list` - List all pods in the cluster
- `pods_list_in_namespace` - List pods in a specific namespace
- `pods_get` - Get a specific pod
- `pods_log` - Get pod logs
- `pods_top` - List resource consumption for pods
- `resources_list` - List any Kubernetes resources
- `resources_get` - Get a specific resource
- `events_list` - List cluster events
- `namespaces_list` - List all namespaces
- `configuration_view` - Get kubeconfig content

### Write Operations (when enabled)
- `pods_delete` - Delete a pod
- `pods_exec` - Execute commands in a pod
- `pods_run` - Run a new pod
- `resources_create_or_update` - Create or update resources
- `resources_delete` - Delete resources
- `helm_install` - Install Helm charts
- `helm_uninstall` - Uninstall Helm releases

## Integration with Oncall Agent

The Oncall Agent uses the `KubernetesManusaMCPIntegration` class to communicate with the kubernetes-mcp-server. This integration:

1. Maps agent actions to appropriate MCP tools
2. Handles authentication and permissions
3. Provides structured responses for the agent to process
4. Supports both read-only and destructive operations (based on configuration)

## Security

- Destructive operations are disabled by default
- Enable them by setting `K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true` in your `.env` file
- The server uses your kubectl credentials, so ensure proper RBAC is configured

## Troubleshooting

If the MCP server fails to start:
1. Check that you have a valid kubeconfig: `kubectl config view`
2. Verify you can connect to your cluster: `kubectl get nodes`
3. Check the server logs for any authentication errors
4. Ensure port 8080 is not already in use

## Alternative Setup (Clone from GitHub)

If you prefer to clone and build from source:

```bash
git clone https://github.com/manusa/kubernetes-mcp-server.git
cd kubernetes-mcp-server
pnpm install
pnpm run build
pnpm start -- --http-port 8080
```