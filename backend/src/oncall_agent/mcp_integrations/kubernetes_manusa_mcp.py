"""
Kubernetes MCP Integration for manusa/kubernetes-mcp-server

This integration is specifically designed to work with the kubernetes-mcp-server
by manusa, mapping its MCP tools to our agent's operations.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp import MCPClient
from src.oncall_agent.mcp_integrations.base import MCPIntegration
from src.oncall_agent.utils.logger import get_logger


@dataclass
class MCPToolCall:
    """Represents an MCP tool call"""
    tool: str
    params: dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class KubernetesManusaMCPIntegration(MCPIntegration):
    """Kubernetes integration for manusa/kubernetes-mcp-server."""

    def __init__(self, namespace: str = "default",
                 enable_destructive_operations: bool = False):
        """Initialize Kubernetes MCP integration."""
        super().__init__(name="kubernetes_manusa_mcp")
        self.config = get_config()
        self.logger = get_logger(f"{__name__}.ManusaMCP")

        # Configuration
        self.namespace = namespace
        self.enable_destructive_operations = enable_destructive_operations

        # MCP client state
        self.mcp_server_url = self.config.k8s_mcp_server_url or "http://localhost:8080"
        self.mcp_client = None
        self._connected = False
        self.connected = False  # Public attribute for API compatibility
        self.connection_time = None
        self._available_tools: set[str] = set()
        self._audit_log: list[MCPToolCall] = []

        # Tool mapping from our actions to manusa MCP tools
        self.tool_mapping = {
            # Read operations
            'get_pods': 'pods_list',
            'get_pod': 'pods_get',
            'get_deployments': 'resources_list',
            'get_services': 'resources_list',
            'get_logs': 'pods_log',
            'describe_resource': 'resources_get',
            'get_events': 'events_list',
            'get_namespaces': 'namespaces_list',
            'top_pods': 'pods_top',
            
            # Write operations
            'delete_pod': 'pods_delete',
            'delete_resource': 'resources_delete',
            'apply_manifest': 'resources_create_or_update',
            'exec_command': 'pods_exec',
            'run_pod': 'pods_run',
            
            # Helm operations
            'helm_install': 'helm_install',
            'helm_list': 'helm_list',
            'helm_uninstall': 'helm_uninstall',
        }

        # Tools that require destructive permissions
        self.destructive_tools = {
            'pods_delete',
            'resources_delete',
            'resources_create_or_update',
            'pods_exec',
            'pods_run',
            'helm_install',
            'helm_uninstall'
        }

    async def connect(self) -> bool:
        """Connect to the Kubernetes MCP server."""
        try:
            self.logger.info(f"Connecting to Kubernetes MCP server at {self.mcp_server_url}...")

            # Initialize MCP client
            self.mcp_client = MCPClient(self.mcp_server_url, self.logger)
            connected = await self.mcp_client.connect()
            
            if not connected:
                raise Exception("Failed to connect to MCP server")

            # Get available tools
            self._available_tools = set(self.mcp_client.available_tools)
            self.logger.info(f"Connected to MCP server at {self.mcp_server_url}. Available tools: {len(self._available_tools)}")

            self._connected = True
            self.connected = True
            self.connection_time = datetime.utcnow()
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            self._connected = False
            self.connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        try:
            if self.mcp_client:
                await self.mcp_client.disconnect()
                self.mcp_client = None

            self._connected = False
            self.connected = False
            self._available_tools.clear()
            self.logger.info("Disconnected from Kubernetes MCP server")

        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")

    async def fetch_context(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch Kubernetes context information."""
        context_type = params.get("type", "pods")
        namespace = params.get("namespace", self.namespace)

        try:
            if context_type == "pods":
                return await self._get_pods(namespace)
            elif context_type == "deployments":
                return await self._get_deployments(namespace)
            elif context_type == "services":
                return await self._get_services(namespace)
            elif context_type == "events":
                return await self._get_events()
            elif context_type == "namespaces":
                return await self._get_namespaces()
            elif context_type == "metrics":
                return await self._get_pod_metrics(namespace)
            else:
                return {"error": f"Unknown context type: {context_type}"}

        except Exception as e:
            self.logger.error(f"Error fetching context: {e}")
            return {"error": str(e)}

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a Kubernetes action via MCP server."""
        try:
            # Log the action attempt
            self._log_action(action, params)

            # Map high-level actions to MCP tools
            if action == "restart_pod":
                return await self._restart_pod(params)
            elif action == "scale_deployment":
                return await self._scale_deployment(params)
            elif action == "rollback_deployment":
                return await self._rollback_deployment(params)
            elif action == "check_pod_logs":
                return await self._get_pod_logs(params)
            elif action == "describe_resource":
                return await self._describe_resource(params)
            elif action == "apply_manifest":
                return await self._apply_manifest(params)
            elif action == "delete_resource":
                return await self._delete_resource(params)
            elif action == "patch_resource":
                return await self._patch_resource(params)
            elif action == "set_image":
                return await self._set_image(params)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            self.logger.error(f"Error executing action {action}: {e}")
            return {"success": False, "error": str(e)}

    def get_capabilities(self) -> list[str]:
        """Get list of available capabilities."""
        capabilities = [
            "get_pods",
            "get_deployments",
            "get_services",
            "get_logs",
            "describe_resource",
            "get_events",
            "get_metrics",
            "get_namespaces"
        ]

        if self.enable_destructive_operations:
            capabilities.extend([
                "restart_pod",
                "scale_deployment",
                "rollback_deployment",
                "delete_resource",
                "apply_manifest",
                "patch_resource",
                "set_image"
            ])

        return capabilities

    async def health_check(self) -> bool:
        """Check if the MCP server connection is healthy."""
        return self._connected

    # Private methods for MCP operations

    async def _call_mcp_tool(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool with parameters."""
        if not self.mcp_client:
            return {
                "success": False,
                "error": "MCP client not initialized"
            }

        # Check permissions for destructive operations
        if tool in self.destructive_tools and not self.enable_destructive_operations:
            return {
                "success": False,
                "error": f"Destructive operation '{tool}' not enabled"
            }

        # Log the tool call
        tool_call = MCPToolCall(
            tool=tool,
            params=params,
            timestamp=datetime.utcnow()
        )
        self._audit_log.append(tool_call)

        try:
            # Make the actual MCP call
            self.logger.info(f"MCP tool call: {tool} with params: {params}")
            result = await self.mcp_client.call_tool(tool, params)
            
            return {
                "success": result.success,
                "content": result.content,
                "error": result.error
            }

        except Exception as e:
            self.logger.error(f"MCP tool call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Kubernetes operations via MCP

    async def _get_pods(self, namespace: str) -> dict[str, Any]:
        """Get pods in a namespace."""
        if namespace == "all" or namespace == "*":
            # List pods from all namespaces
            result = await self._call_mcp_tool('pods_list', {})
        else:
            # List pods in specific namespace
            result = await self._call_mcp_tool('pods_list_in_namespace', {
                'namespace': namespace
            })

        if result.get('success'):
            return {"pods": result.get('content', [])}
        else:
            return {"error": result.get('error', 'Failed to get pods')}

    async def _get_deployments(self, namespace: str) -> dict[str, Any]:
        """Get deployments in a namespace."""
        params = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment'
        }
        if namespace != "all" and namespace != "*":
            params['namespace'] = namespace

        result = await self._call_mcp_tool('resources_list', params)

        if result.get('success'):
            return {"deployments": result.get('content', [])}
        else:
            return {"error": result.get('error', 'Failed to get deployments')}

    async def _get_services(self, namespace: str) -> dict[str, Any]:
        """Get services in a namespace."""
        params = {
            'apiVersion': 'v1',
            'kind': 'Service'
        }
        if namespace != "all" and namespace != "*":
            params['namespace'] = namespace

        result = await self._call_mcp_tool('resources_list', params)

        if result.get('success'):
            return {"services": result.get('content', [])}
        else:
            return {"error": result.get('error', 'Failed to get services')}

    async def _get_events(self) -> dict[str, Any]:
        """Get events from all namespaces."""
        result = await self._call_mcp_tool('events_list', {})

        if result.get('success'):
            return {"events": result.get('content', [])}
        else:
            return {"error": result.get('error', 'Failed to get events')}

    async def _get_namespaces(self) -> dict[str, Any]:
        """Get all namespaces."""
        result = await self._call_mcp_tool('namespaces_list', {})

        if result.get('success'):
            return {"namespaces": result.get('content', [])}
        else:
            return {"error": result.get('error', 'Failed to get namespaces')}

    async def _get_pod_metrics(self, namespace: str) -> dict[str, Any]:
        """Get pod metrics."""
        params = {}
        if namespace != "all" and namespace != "*":
            params['namespace'] = namespace

        result = await self._call_mcp_tool('pods_top', params)

        if result.get('success'):
            return {"pod_metrics": result.get('content', [])}
        else:
            return {"error": result.get('error', 'Failed to get pod metrics')}

    async def _restart_pod(self, params: dict[str, Any]) -> dict[str, Any]:
        """Restart a pod by deleting it."""
        pod_name = params.get('pod_name')
        namespace = params.get('namespace', self.namespace)

        if not pod_name:
            return {"success": False, "error": "pod_name is required"}

        result = await self._call_mcp_tool('pods_delete', {
            'name': pod_name,
            'namespace': namespace
        })

        return {
            "success": result.get('success', False),
            "message": f"Pod {pod_name} deleted for restart" if result.get('success') else result.get('error'),
            "action": "restart_pod",
            "params": params
        }

    async def _scale_deployment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Scale a deployment."""
        deployment_name = params.get('deployment_name')
        replicas = params.get('replicas')
        namespace = params.get('namespace', self.namespace)

        if not deployment_name or replicas is None:
            return {"success": False, "error": "deployment_name and replicas are required"}

        # First get the deployment
        get_result = await self._call_mcp_tool('resources_get', {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'name': deployment_name,
            'namespace': namespace
        })

        if not get_result.get('success'):
            return {"success": False, "error": f"Failed to get deployment: {get_result.get('error')}"}

        # Parse the deployment and update replicas
        try:
            deployment_content = get_result.get('content', [])
            if deployment_content and len(deployment_content) > 0:
                deployment_text = deployment_content[0].get('text', '')
                deployment = json.loads(deployment_text) if deployment_text else {}
                
                # Update replicas
                deployment['spec']['replicas'] = int(replicas)
                
                # Apply the updated deployment
                update_result = await self._call_mcp_tool('resources_create_or_update', {
                    'resource': json.dumps(deployment)
                })
                
                return {
                    "success": update_result.get('success', False),
                    "message": f"Deployment {deployment_name} scaled to {replicas} replicas" if update_result.get('success') else update_result.get('error'),
                    "action": "scale_deployment",
                    "params": params
                }
            else:
                return {"success": False, "error": "Deployment not found"}
                
        except Exception as e:
            return {"success": False, "error": f"Failed to scale deployment: {str(e)}"}

    async def _get_pod_logs(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get pod logs."""
        pod_name = params.get('pod_name')
        namespace = params.get('namespace', self.namespace)
        tail_lines = params.get('tail_lines', 100)
        container = params.get('container')

        if not pod_name:
            return {"success": False, "error": "pod_name is required"}

        tool_params = {
            'name': pod_name,
            'namespace': namespace,
            'tailLines': tail_lines
        }

        if container:
            tool_params['container'] = container

        result = await self._call_mcp_tool('pods_log', tool_params)

        return {
            "success": result.get('success', False),
            "logs": result.get('content', [{}])[0].get('text', '') if result.get('success') else None,
            "error": result.get('error') if not result.get('success') else None,
            "action": "check_pod_logs",
            "params": params
        }

    async def _describe_resource(self, params: dict[str, Any]) -> dict[str, Any]:
        """Describe a Kubernetes resource."""
        kind = params.get('kind')
        name = params.get('name')
        namespace = params.get('namespace', self.namespace)

        if not kind or not name:
            return {"success": False, "error": "kind and name are required"}

        # Map common resource types to API versions
        api_version_map = {
            'pod': 'v1',
            'pods': 'v1',
            'service': 'v1',
            'services': 'v1',
            'deployment': 'apps/v1',
            'deployments': 'apps/v1',
            'configmap': 'v1',
            'configmaps': 'v1',
            'secret': 'v1',
            'secrets': 'v1',
            'ingress': 'networking.k8s.io/v1',
            'ingresses': 'networking.k8s.io/v1',
        }

        api_version = api_version_map.get(kind.lower(), params.get('apiVersion', 'v1'))

        result = await self._call_mcp_tool('resources_get', {
            'apiVersion': api_version,
            'kind': kind.capitalize() if kind.lower() in api_version_map else kind,
            'name': name,
            'namespace': namespace
        })

        return {
            "success": result.get('success', False),
            "description": result.get('content', [{}])[0].get('text', '') if result.get('success') else None,
            "error": result.get('error') if not result.get('success') else None,
            "action": "describe_resource",
            "params": params
        }

    async def _apply_manifest(self, params: dict[str, Any]) -> dict[str, Any]:
        """Apply a Kubernetes manifest."""
        manifest = params.get('manifest')

        if not manifest:
            return {"success": False, "error": "manifest is required"}

        result = await self._call_mcp_tool('resources_create_or_update', {
            'resource': manifest
        })

        return {
            "success": result.get('success', False),
            "message": "Manifest applied successfully" if result.get('success') else result.get('error'),
            "action": "apply_manifest",
            "params": params
        }

    async def _delete_resource(self, params: dict[str, Any]) -> dict[str, Any]:
        """Delete a Kubernetes resource."""
        kind = params.get('kind')
        name = params.get('name')
        namespace = params.get('namespace', self.namespace)

        if not kind:
            return {"success": False, "error": "kind is required"}

        # For pods, use the specific pods_delete tool
        if kind.lower() in ['pod', 'pods'] and name:
            return await self._restart_pod({'pod_name': name, 'namespace': namespace})

        # For other resources, use resources_delete
        if not name:
            return {"success": False, "error": "name is required for resource deletion"}

        # Map common resource types to API versions
        api_version_map = {
            'service': 'v1',
            'services': 'v1',
            'deployment': 'apps/v1',
            'deployments': 'apps/v1',
            'configmap': 'v1',
            'configmaps': 'v1',
            'secret': 'v1',
            'secrets': 'v1',
        }

        api_version = api_version_map.get(kind.lower(), params.get('apiVersion', 'v1'))

        result = await self._call_mcp_tool('resources_delete', {
            'apiVersion': api_version,
            'kind': kind.capitalize() if kind.lower() in api_version_map else kind,
            'name': name,
            'namespace': namespace
        })

        return {
            "success": result.get('success', False),
            "message": f"Resource {kind}/{name} deleted" if result.get('success') else result.get('error'),
            "action": "delete_resource",
            "params": params
        }

    async def _rollback_deployment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Rollback a deployment - Note: kubernetes-mcp-server doesn't have direct rollback."""
        # This would need to be implemented by getting the deployment history
        # and applying a previous version
        return {
            "success": False,
            "error": "Rollback not directly supported by kubernetes-mcp-server. Use kubectl rollout undo manually.",
            "action": "rollback_deployment",
            "params": params
        }

    async def _patch_resource(self, params: dict[str, Any]) -> dict[str, Any]:
        """Patch a resource - implemented via get and update."""
        kind = params.get('kind')
        name = params.get('name')
        namespace = params.get('namespace', self.namespace)
        patch = params.get('patch')

        if not all([kind, name, patch]):
            return {"success": False, "error": "kind, name, and patch are required"}

        # This would need to get the resource, apply the patch, and update
        # For now, return not implemented
        return {
            "success": False,
            "error": "Patch operations need to be implemented via get/modify/update pattern",
            "action": "patch_resource",
            "params": params
        }

    async def _set_image(self, params: dict[str, Any]) -> dict[str, Any]:
        """Set container image in a deployment."""
        deployment_name = params.get('name') or params.get('deployment_name')
        namespace = params.get('namespace', self.namespace)
        container = params.get('container')
        image = params.get('image')

        if not all([deployment_name, container, image]):
            return {"success": False, "error": "deployment_name, container, and image are required"}

        # Get the deployment, update the image, and apply
        # This is similar to scale but updates container image
        return {
            "success": False,
            "error": "Set image needs to be implemented via get/modify/update pattern",
            "action": "set_image",
            "params": params
        }

    def _log_action(self, action: str, params: dict[str, Any]):
        """Log an action attempt."""
        self.logger.info(f"Executing action: {action} with params: {params}")

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log of all MCP tool calls."""
        return [call.to_dict() for call in self._audit_log]
    
    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information for health check."""
        return {
            "namespace": self.namespace,
            "destructive_operations_enabled": self.enable_destructive_operations,
            "mcp_mode": True,
            "mcp_server": "kubernetes-mcp-server (manusa)",
            "available_tools": len(self._available_tools),
            "tools": list(self._available_tools)
        }
    
    # Compatibility methods for the old interface
    
    async def test_connection(self, context_name: str = None, namespace: str = None) -> dict[str, Any]:
        """Test connection to a Kubernetes cluster."""
        # For kubernetes-mcp-server, we just check if we can connect and list namespaces
        try:
            if not self._connected:
                connected = await self.connect()
                if not connected:
                    return {"connected": False, "error": "Failed to connect to MCP server"}
            
            # Try to list namespaces as a connection test
            result = await self._call_mcp_tool('namespaces_list', {})
            
            if result.get('success'):
                return {
                    "connected": True,
                    "context": context_name or "default",
                    "namespace": namespace or self.namespace,
                    "namespaces_found": len(result.get('content', []))
                }
            else:
                return {"connected": False, "error": result.get('error', 'Connection test failed')}
                
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    async def validate_kubeconfig(self, kubeconfig_data: str) -> dict[str, Any]:
        """Validate kubeconfig data - not directly supported by kubernetes-mcp-server."""
        # This is not directly supported, so we return a basic response
        return {
            "valid": True,
            "contexts": [{"name": "default", "cluster": "default", "server": "default", "is_current": True}],
            "error": None
        }
    
    async def discover_contexts(self) -> list[dict[str, Any]]:
        """Discover available Kubernetes contexts."""
        # kubernetes-mcp-server uses the current kubectl context
        # We can get the configuration view to see what's available
        try:
            if not self._connected:
                await self.connect()
                
            result = await self._call_mcp_tool('configuration_view', {})
            
            if result.get('success'):
                # Parse the kubeconfig to extract contexts
                # For now, return a simple default context
                return [{
                    "name": "current",
                    "cluster": "current-cluster",
                    "namespace": self.namespace
                }]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Error discovering contexts: {e}")
            return []
    
    async def get_cluster_info(self, context_name: str = None) -> dict[str, Any]:
        """Get cluster information."""
        try:
            # Get namespaces as a proxy for cluster info
            namespaces_result = await self._get_namespaces()
            
            return {
                "context": context_name or "current",
                "namespaces": len(namespaces_result.get('namespaces', [])),
                "connected": not namespaces_result.get('error'),
                "server": self.mcp_server_url
            }
            
        except Exception as e:
            return {"error": str(e)}