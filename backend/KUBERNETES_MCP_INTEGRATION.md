# Kubernetes MCP Integration

This project integrates with Kubernetes using the official [kubernetes-mcp-server](https://github.com/manusa/kubernetes-mcp-server) by manusa.

## Current Status

The integration has been updated to use the official MCP server instead of custom kubectl implementations. All kubectl subprocess calls have been removed and replaced with MCP protocol communication.

## Architecture

1. **MCP Server**: The kubernetes-mcp-server runs as a separate process
2. **Integration Class**: `KubernetesManusaMCPIntegration` handles communication with the MCP server
3. **MCP Client**: A simple HTTP client that communicates with the MCP server

## Available Operations

The kubernetes-mcp-server provides these tools:
- `pods_list` - List all pods
- `pods_list_in_namespace` - List pods in a namespace  
- `pods_get` - Get pod details
- `pods_log` - Get pod logs
- `pods_delete` - Delete a pod (when destructive operations enabled)
- `pods_exec` - Execute commands in pods
- `pods_run` - Run new pods
- `pods_top` - Get pod resource usage
- `resources_list` - List Kubernetes resources
- `resources_get` - Get resource details
- `resources_create_or_update` - Create/update resources
- `resources_delete` - Delete resources
- `events_list` - List events
- `namespaces_list` - List namespaces
- `configuration_view` - View kubeconfig
- `helm_install`, `helm_list`, `helm_uninstall` - Helm operations

## Configuration

Set these environment variables:
- `K8S_MCP_SERVER_URL` - MCP server URL (default: http://localhost:8080)
- `K8S_ENABLE_DESTRUCTIVE_OPERATIONS` - Enable delete/modify operations (default: false)
- `K8S_ENABLED` - Enable Kubernetes integration (default: true)

## Running the MCP Server

The MCP server can be run in different modes:

### HTTP Streaming Mode (Used by API Server)
```bash
pnpm exec kubernetes-mcp-server --http-port 8080
```

### SSE Mode
```bash
pnpm exec kubernetes-mcp-server --sse-port 8080
```

### STDIO Mode (Default)
```bash
pnpm exec kubernetes-mcp-server
```

## Integration Details

The `KubernetesManusaMCPIntegration` class:
1. Connects to the MCP server via HTTP
2. Maps high-level agent actions to MCP tools
3. Handles responses and errors
4. Provides compatibility with the existing agent interface

## Testing

Run the test script to verify the integration:
```bash
uv run python test_mcp_integration.py
```

## Known Issues

1. The kubernetes-mcp-server uses a streaming protocol that's different from traditional REST APIs
2. Tool discovery is not automatic - we hardcode the known tools
3. Some operations like rollback are not directly supported and need workarounds

## Future Improvements

1. Better protocol handling for the MCP streaming format
2. Automatic tool discovery from the server
3. Support for more complex Kubernetes operations
4. Better error handling and retry logic