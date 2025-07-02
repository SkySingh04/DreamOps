# Enhanced Kubernetes Integration

The DreamOps platform now includes an enhanced Kubernetes integration with auto-discovery, multi-cluster support, and a user-friendly frontend configuration interface.

## Features

### Backend Enhancements

1. **Auto-Discovery**: Automatically discovers all available Kubernetes contexts from:
   - `~/.kube/config` (default location)
   - `$KUBECONFIG` environment variable
   - Custom kubeconfig paths
   - In-cluster service account (when running inside K8s)

2. **Multi-Context Support**: Connect to and manage multiple Kubernetes clusters
   - Switch between contexts dynamically
   - Per-context namespace configuration
   - Context-specific permission verification

3. **Enhanced Connection Testing**:
   - Test connectivity before saving configurations
   - Verify namespace existence
   - Check RBAC permissions
   - Get cluster version and node count

4. **Permission Verification**:
   - Check read permissions (pods, services, deployments, etc.)
   - Verify write permissions (with dry-run)
   - Identify missing RBAC permissions

5. **Cluster Information**:
   - Node details (count, status, version, OS)
   - Resource counts (pods, services, deployments)
   - Total CPU and memory capacity
   - Namespace listing

### Frontend Configuration UI

Located at `/integrations/kubernetes`, the new UI provides:

1. **Context Discovery Tab**:
   - Lists all discovered Kubernetes contexts
   - Shows current context indicator
   - One-click connection testing
   - Easy context selection for configuration

2. **Saved Configurations Tab**:
   - Manage multiple cluster configurations
   - Enable/disable configurations
   - Test connectivity
   - View cluster details

3. **Cluster Details Tab**:
   - Real-time cluster overview
   - Node information
   - Resource statistics
   - Capacity metrics

4. **Configuration Options**:
   - Custom configuration names
   - Namespace selection
   - Destructive operations toggle
   - Custom kubeconfig path support

## API Endpoints

New Kubernetes-specific endpoints:

- `GET /api/v1/integrations/kubernetes/discover` - Discover available contexts
- `POST /api/v1/integrations/kubernetes/test` - Test cluster connection
- `GET /api/v1/integrations/kubernetes/configs` - List saved configurations
- `POST /api/v1/integrations/kubernetes/configs` - Save new configuration
- `PUT /api/v1/integrations/kubernetes/configs/{id}` - Update configuration
- `DELETE /api/v1/integrations/kubernetes/configs/{id}` - Delete configuration
- `GET /api/v1/integrations/kubernetes/health` - Get integration health
- `POST /api/v1/integrations/kubernetes/verify-permissions` - Verify RBAC permissions
- `GET /api/v1/integrations/kubernetes/cluster-info` - Get cluster details

## Usage

### Backend Setup

1. The enhanced integration is automatically used when available:
   ```python
   # In agent.py, it tries enhanced integration first
   from .mcp_integrations.kubernetes_enhanced import EnhancedKubernetesMCPIntegration
   ```

2. Fallback to basic integration if enhanced is not available

3. Test the integration:
   ```bash
   cd backend
   uv run python test_k8s_enhanced.py
   ```

### Frontend Usage

1. Navigate to `/integrations` in the DreamOps dashboard
2. Click on the Kubernetes card or click "Configure"
3. You'll be redirected to `/integrations/kubernetes`
4. Use the interface to:
   - Discover available contexts
   - Test connections
   - Save configurations
   - Monitor cluster health

### Configuration

Environment variables (`.env`):
```env
# Kubernetes settings
K8S_ENABLED=true
K8S_CONFIG_PATH=~/.kube/config
K8S_CONTEXT=default  # Optional, will auto-discover
K8S_NAMESPACE=default
K8S_ENABLE_DESTRUCTIVE_OPERATIONS=false
```

## Security Considerations

1. **RBAC Verification**: The integration verifies permissions before attempting operations
2. **Destructive Operations**: Disabled by default, requires explicit enablement
3. **Audit Logging**: All actions are logged for security audit
4. **Secure Configuration**: Sensitive data (kubeconfig paths) are not exposed in the UI

## Troubleshooting

### No Contexts Found
- Ensure you have a valid kubeconfig file at `~/.kube/config`
- Check if `KUBECONFIG` environment variable is set correctly
- Verify kubectl works: `kubectl config get-contexts`

### Connection Failed
- Check if the cluster is accessible
- Verify your credentials are not expired
- Ensure the cluster endpoint is reachable from your network

### Permission Errors
- The integration will show which permissions are missing
- Work with your cluster admin to grant necessary RBAC permissions
- For read-only access, only basic view permissions are needed

## Future Enhancements

1. **Persistent Configuration Storage**: Currently uses in-memory storage, will add database persistence
2. **Multi-Cluster Monitoring**: Dashboard showing all connected clusters
3. **Advanced Filtering**: Filter resources by labels, annotations, etc.
4. **Resource Editing**: Direct YAML editing capabilities
5. **Webhook Integration**: Real-time cluster event streaming