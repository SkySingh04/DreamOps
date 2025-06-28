"""
Kubernetes MCP-Only Integration

This integration exclusively uses the MCP server for all Kubernetes operations,
completely eliminating direct kubectl subprocess calls.
"""

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from src.oncall_agent.config import get_config
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


class KubernetesMCPOnlyIntegration(MCPIntegration):
    """Kubernetes integration using only MCP server - no kubectl subprocess calls."""

    def __init__(self, contexts: list[str] = None, namespace: str = "default",
                 enable_destructive_operations: bool = False):
        """Initialize Kubernetes MCP-only integration."""
        super().__init__(name="kubernetes_mcp_only")
        self.config = get_config()
        self.logger = get_logger(f"{__name__}.MCPOnly")

        # Configuration
        self.contexts = contexts or []
        self.current_context = self.contexts[0] if self.contexts else None
        self.namespace = namespace
        self.enable_destructive_operations = enable_destructive_operations

        # MCP client state
        self.mcp_client = None
        self._connected = False
        self._available_tools: set[str] = set()
        self._audit_log: list[MCPToolCall] = []

        # Tool categories
        self.read_tools = {
            'kubernetes_get_pods',
            'kubernetes_get_pod',
            'kubernetes_get_deployments',
            'kubernetes_get_deployment',
            'kubernetes_get_services',
            'kubernetes_get_logs',
            'kubernetes_describe_resource',
            'kubernetes_get_events',
            'kubernetes_top_nodes',
            'kubernetes_top_pods',
            'kubernetes_list_contexts',
            'kubernetes_get_namespaces'
        }

        self.write_tools = {
            'kubernetes_delete_resource',
            'kubernetes_scale_deployment',
            'kubernetes_rollout_restart',
            'kubernetes_rollout_undo',
            'kubernetes_apply_manifest',
            'kubernetes_patch_resource',
            'kubernetes_set_image',
            'kubernetes_exec_command',
            'kubernetes_port_forward',
            'kubernetes_use_context'
        }

    async def connect(self) -> bool:
        """Connect to the Kubernetes MCP server."""
        try:
            self.logger.info("Connecting to Kubernetes MCP server...")

            # Initialize MCP client
            # In production, this would use the actual MCP client library
            # For now, we'll simulate the connection
            await self._initialize_mcp_client()

            # Verify connection by listing available tools
            tools = await self._list_available_tools()
            self._available_tools = set(tools)

            self.logger.info(f"Connected to MCP server. Available tools: {len(self._available_tools)}")

            # Set current context if available
            if self.current_context:
                await self._set_context(self.current_context)

            self._connected = True
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        try:
            if self.mcp_client:
                # Close MCP connection
                await self._close_mcp_client()

            self._connected = False
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
                return await self._get_events(namespace)
            elif context_type == "metrics":
                return await self._get_metrics(namespace)
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
            "get_metrics"
        ]

        if self.enable_destructive_operations:
            capabilities.extend([
                "restart_pod",
                "scale_deployment",
                "rollback_deployment",
                "delete_resource",
                "apply_manifest",
                "patch_resource"
            ])

        return capabilities

    async def health_check(self) -> bool:
        """Check if the MCP server connection is healthy."""
        if not self._connected:
            return False

        try:
            # Test connection with a simple operation
            result = await self._call_mcp_tool('kubernetes_list_contexts', {})
            return result.get('success', False)
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    # Private methods for MCP operations

    async def _initialize_mcp_client(self):
        """Initialize the MCP client connection."""
        # In production, this would initialize the actual MCP client
        # For now, we simulate it
        self.mcp_client = {
            "connected": True,
            "server_url": "mcp://localhost:8085",
            "protocol_version": "1.0"
        }
        await asyncio.sleep(0.1)  # Simulate connection delay

    async def _close_mcp_client(self):
        """Close the MCP client connection."""
        if self.mcp_client:
            self.mcp_client["connected"] = False
            self.mcp_client = None

    async def _list_available_tools(self) -> list[str]:
        """List available tools from the MCP server."""
        # In production, this would query the MCP server
        # For now, return expected Kubernetes tools
        return list(self.read_tools | self.write_tools)

    async def _call_mcp_tool(self, tool: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool with parameters."""
        # Validate tool availability
        if tool not in self._available_tools:
            return {
                "success": False,
                "error": f"Tool '{tool}' not available on MCP server"
            }

        # Check permissions for write operations
        if tool in self.write_tools and not self.enable_destructive_operations:
            return {
                "success": False,
                "error": f"Destructive operation '{tool}' not enabled"
            }

        # Add default parameters
        if 'namespace' not in params and self.namespace:
            params['namespace'] = self.namespace
        if 'context' not in params and self.current_context:
            params['context'] = self.current_context

        # Log the tool call
        tool_call = MCPToolCall(
            tool=tool,
            params=params,
            timestamp=datetime.utcnow()
        )
        self._audit_log.append(tool_call)

        try:
            # In production, this would make actual MCP call
            # For now, simulate successful response
            self.logger.info(f"MCP tool call: {tool} with params: {params}")

            # Simulate response based on tool
            if tool == 'kubernetes_get_pods':
                return {
                    "success": True,
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "items": [
                                {
                                    "metadata": {"name": "test-pod-1", "namespace": params.get('namespace', 'default')},
                                    "status": {"phase": "Running"}
                                }
                            ]
                        })
                    }]
                }
            else:
                return {
                    "success": True,
                    "content": [{"type": "text", "text": f"Executed {tool} successfully"}]
                }

        except Exception as e:
            self.logger.error(f"MCP tool call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _set_context(self, context: str):
        """Set the current Kubernetes context."""
        result = await self._call_mcp_tool('kubernetes_use_context', {'context': context})
        if result.get('success'):
            self.current_context = context
            self.logger.info(f"Switched to context: {context}")

    # Kubernetes operations via MCP

    async def _get_pods(self, namespace: str) -> dict[str, Any]:
        """Get pods in a namespace."""
        result = await self._call_mcp_tool('kubernetes_get_pods', {
            'namespace': namespace,
            'output': 'json'
        })

        if result.get('success'):
            content = result.get('content', [{}])[0].get('text', '{}')
            return json.loads(content)
        else:
            return {"error": result.get('error', 'Failed to get pods')}

    async def _get_deployments(self, namespace: str) -> dict[str, Any]:
        """Get deployments in a namespace."""
        result = await self._call_mcp_tool('kubernetes_get_deployments', {
            'namespace': namespace,
            'output': 'json'
        })

        if result.get('success'):
            content = result.get('content', [{}])[0].get('text', '{}')
            return json.loads(content)
        else:
            return {"error": result.get('error', 'Failed to get deployments')}

    async def _get_services(self, namespace: str) -> dict[str, Any]:
        """Get services in a namespace."""
        result = await self._call_mcp_tool('kubernetes_get_services', {
            'namespace': namespace,
            'output': 'json'
        })

        if result.get('success'):
            content = result.get('content', [{}])[0].get('text', '{}')
            return json.loads(content)
        else:
            return {"error": result.get('error', 'Failed to get services')}

    async def _get_events(self, namespace: str) -> dict[str, Any]:
        """Get events in a namespace."""
        result = await self._call_mcp_tool('kubernetes_get_events', {
            'namespace': namespace,
            'sort_by': '.lastTimestamp'
        })

        if result.get('success'):
            content = result.get('content', [{}])[0].get('text', '{}')
            return {"events": content}
        else:
            return {"error": result.get('error', 'Failed to get events')}

    async def _get_metrics(self, namespace: str) -> dict[str, Any]:
        """Get resource metrics."""
        pod_metrics = await self._call_mcp_tool('kubernetes_top_pods', {
            'namespace': namespace
        })

        node_metrics = await self._call_mcp_tool('kubernetes_top_nodes', {})

        return {
            "pod_metrics": pod_metrics.get('content', [{}])[0].get('text', '') if pod_metrics.get('success') else None,
            "node_metrics": node_metrics.get('content', [{}])[0].get('text', '') if node_metrics.get('success') else None
        }

    async def _restart_pod(self, params: dict[str, Any]) -> dict[str, Any]:
        """Restart a pod by deleting it."""
        pod_name = params.get('pod_name')
        namespace = params.get('namespace', self.namespace)

        if not pod_name:
            return {"success": False, "error": "pod_name is required"}

        result = await self._call_mcp_tool('kubernetes_delete_resource', {
            'kind': 'pod',
            'name': pod_name,
            'namespace': namespace,
            'grace_period': 30
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

        result = await self._call_mcp_tool('kubernetes_scale_deployment', {
            'name': deployment_name,
            'namespace': namespace,
            'replicas': int(replicas)
        })

        return {
            "success": result.get('success', False),
            "message": f"Deployment {deployment_name} scaled to {replicas} replicas" if result.get('success') else result.get('error'),
            "action": "scale_deployment",
            "params": params
        }

    async def _rollback_deployment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Rollback a deployment."""
        deployment_name = params.get('deployment_name')
        namespace = params.get('namespace', self.namespace)
        to_revision = params.get('to_revision', 0)

        if not deployment_name:
            return {"success": False, "error": "deployment_name is required"}

        result = await self._call_mcp_tool('kubernetes_rollout_undo', {
            'kind': 'deployment',
            'name': deployment_name,
            'namespace': namespace,
            'to_revision': to_revision
        })

        return {
            "success": result.get('success', False),
            "message": f"Deployment {deployment_name} rolled back" if result.get('success') else result.get('error'),
            "action": "rollback_deployment",
            "params": params
        }

    async def _get_pod_logs(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get pod logs."""
        pod_name = params.get('pod_name')
        namespace = params.get('namespace', self.namespace)
        tail_lines = params.get('tail_lines', 100)
        container = params.get('container')

        if not pod_name:
            return {"success": False, "error": "pod_name is required"}

        tool_params = {
            'pod': pod_name,
            'namespace': namespace,
            'tail': tail_lines
        }

        if container:
            tool_params['container'] = container

        result = await self._call_mcp_tool('kubernetes_get_logs', tool_params)

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

        result = await self._call_mcp_tool('kubernetes_describe_resource', {
            'kind': kind,
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
        namespace = params.get('namespace')

        if not manifest:
            return {"success": False, "error": "manifest is required"}

        tool_params = {'manifest': manifest}
        if namespace:
            tool_params['namespace'] = namespace

        result = await self._call_mcp_tool('kubernetes_apply_manifest', tool_params)

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
        label_selector = params.get('label_selector')

        if not kind:
            return {"success": False, "error": "kind is required"}

        if not name and not label_selector:
            return {"success": False, "error": "Either name or label_selector is required"}

        tool_params = {
            'kind': kind,
            'namespace': namespace
        }

        if name:
            tool_params['name'] = name
        if label_selector:
            tool_params['label_selector'] = label_selector

        result = await self._call_mcp_tool('kubernetes_delete_resource', tool_params)

        return {
            "success": result.get('success', False),
            "message": f"Resource {kind}/{name or label_selector} deleted" if result.get('success') else result.get('error'),
            "action": "delete_resource",
            "params": params
        }

    async def _patch_resource(self, params: dict[str, Any]) -> dict[str, Any]:
        """Patch a Kubernetes resource."""
        kind = params.get('kind')
        name = params.get('name')
        namespace = params.get('namespace', self.namespace)
        patch = params.get('patch')
        patch_type = params.get('patch_type', 'strategic')

        if not all([kind, name, patch]):
            return {"success": False, "error": "kind, name, and patch are required"}

        result = await self._call_mcp_tool('kubernetes_patch_resource', {
            'kind': kind,
            'name': name,
            'namespace': namespace,
            'patch': patch,
            'patch_type': patch_type
        })

        return {
            "success": result.get('success', False),
            "message": f"Resource {kind}/{name} patched" if result.get('success') else result.get('error'),
            "action": "patch_resource",
            "params": params
        }

    def _log_action(self, action: str, params: dict[str, Any]):
        """Log an action attempt."""
        self.logger.info(f"Executing action: {action} with params: {params}")

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log of all MCP tool calls."""
        return [call.to_dict() for call in self._audit_log]

    async def discover_contexts(self) -> list[str]:
        """Discover available Kubernetes contexts using MCP server."""
        try:
            self.logger.info("Discovering Kubernetes contexts via MCP...")
            
            # Use the kubernetes_list_contexts tool
            result = await self._call_mcp_tool('kubernetes_list_contexts', {})
            
            if result.get('success'):
                contexts = result.get('contexts', [])
                self.logger.info(f"Discovered {len(contexts)} Kubernetes contexts")
                return contexts
            else:
                self.logger.error(f"Failed to discover contexts: {result.get('error')}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error discovering contexts: {e}")
            return []
