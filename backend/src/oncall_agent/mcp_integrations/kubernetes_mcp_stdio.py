"""
Kubernetes MCP Integration using STDIO mode for kubernetes-mcp-server.

This integration runs the kubernetes-mcp-server as a subprocess and communicates
via stdin/stdout using the MCP protocol. This approach works better than HTTP
for the manusa kubernetes-mcp-server.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.base import MCPIntegration
from src.oncall_agent.utils.logger import get_logger


@dataclass
class K8sContext:
    """Kubernetes context information."""
    name: str
    cluster: str
    namespace: str
    is_current: bool = False


class KubernetesMCPStdioIntegration(MCPIntegration):
    """Kubernetes integration using kubernetes-mcp-server in STDIO mode."""

    def __init__(self,
                 namespace: str = "default",
                 context: str | None = None,
                 enable_destructive_operations: bool = False):
        """Initialize Kubernetes MCP integration."""
        super().__init__(name="kubernetes_mcp_stdio")
        self.config = get_config()
        self.logger = get_logger(f"{__name__}.StdioMCP")

        # Configuration
        self.namespace = namespace
        self.context = context
        self.enable_destructive_operations = enable_destructive_operations

        # MCP server process
        self.process: asyncio.subprocess.Process | None = None
        self._connected = False
        self.connected = False
        self.connection_time = None
        self._message_id = 0
        self._pending_responses = {}

        # Available tools from kubernetes-mcp-server
        self._available_tools = [
            'pods_list', 'pods_list_in_namespace', 'pods_get', 'pods_log',
            'pods_delete', 'pods_exec', 'pods_run', 'pods_top',
            'resources_list', 'resources_get', 'resources_create_or_update',
            'resources_delete', 'events_list', 'namespaces_list',
            'configuration_view', 'helm_install', 'helm_list', 'helm_uninstall'
        ]

    async def connect(self) -> bool:
        """Connect to the Kubernetes MCP server via STDIO."""
        try:
            # Build command to start kubernetes-mcp-server
            cmd = self._build_server_command()

            self.logger.info(f"Starting kubernetes-mcp-server: {' '.join(cmd)}")

            # Start the MCP server process
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_server_env()
            )

            # Test connection by listing namespaces
            test_result = await self._send_request("namespaces_list", {})

            if test_result and test_result.get("result"):
                self._connected = True
                self.connected = True
                self.connection_time = datetime.now(UTC)
                self.logger.info(f"Connected to kubernetes-mcp-server (context: {self.context or 'current'})")
                return True
            else:
                self.logger.error("Failed to verify connection to kubernetes-mcp-server")
                await self.disconnect()
                return False

        except Exception as e:
            self.logger.error(f"Failed to start kubernetes-mcp-server: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        try:
            if self.process:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except TimeoutError:
            if self.process:
                self.process.kill()
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
        finally:
            self.process = None
            self._connected = False
            self.connected = False
            self.logger.info("Disconnected from kubernetes-mcp-server")

    def _build_server_command(self) -> list[str]:
        """Build command to start kubernetes-mcp-server."""
        # Check if kubernetes-mcp-server is available
        server_path = self.config.k8s_mcp_server_path or "kubernetes-mcp-server"

        # For manusa's kubernetes-mcp-server, we need to use the JAR
        if os.path.exists("/usr/local/bin/kubernetes-mcp-server"):
            cmd = ["/usr/local/bin/kubernetes-mcp-server"]
        elif os.path.exists("kubernetes-mcp-server.jar"):
            cmd = ["java", "-jar", "kubernetes-mcp-server.jar"]
        else:
            # Try npx as fallback
            cmd = ["npx", "@modelcontextprotocol/server-kubernetes"]

        # Add stdio mode flag if supported
        cmd.append("stdio")

        return cmd

    def _get_server_env(self) -> dict[str, str]:
        """Get environment variables for the MCP server."""
        env = os.environ.copy()

        # Set Kubernetes context if specified
        if self.context:
            env["KUBECONFIG_CONTEXT"] = self.context

        # Set namespace
        env["K8S_NAMESPACE"] = self.namespace

        return env

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Send a request to the MCP server and wait for response."""
        if not self.process or not self.process.stdin:
            return None

        # Create request message
        self._message_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._message_id,
            "method": method,
            "params": params
        }

        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()

            # Read response
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=30.0
            )

            if response_line:
                response = json.loads(response_line.decode())
                if response.get("id") == self._message_id:
                    return response

            return None

        except TimeoutError:
            self.logger.error(f"Timeout waiting for response to {method}")
            return None
        except Exception as e:
            self.logger.error(f"Error sending request: {e}")
            return None

    async def fetch_context(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch Kubernetes context information."""
        context_type = params.get("type", "pods")
        namespace = params.get("namespace", self.namespace)

        try:
            if context_type == "pods":
                result = await self._send_request("pods_list_in_namespace", {"namespace": namespace})
                if result and "result" in result:
                    return {"pods": result["result"]}

            elif context_type == "deployments":
                result = await self._send_request("resources_list", {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "namespace": namespace
                })
                if result and "result" in result:
                    return {"deployments": result["result"]}

            elif context_type == "events":
                result = await self._send_request("events_list", {})
                if result and "result" in result:
                    return {"events": result["result"]}

            elif context_type == "namespaces":
                result = await self._send_request("namespaces_list", {})
                if result and "result" in result:
                    return {"namespaces": result["result"]}

            return {"error": f"Unknown context type: {context_type}"}

        except Exception as e:
            self.logger.error(f"Error fetching context: {e}")
            return {"error": str(e)}

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a Kubernetes action via MCP server."""
        try:
            # Check if destructive operations are allowed
            destructive_actions = ["restart_pod", "delete_resource", "scale_deployment"]
            if action in destructive_actions and not self.enable_destructive_operations:
                return {
                    "success": False,
                    "error": f"Destructive operation '{action}' not enabled"
                }

            # Map actions to MCP methods
            if action == "restart_pod":
                pod_name = params.get("pod_name")
                namespace = params.get("namespace", self.namespace)
                result = await self._send_request("pods_delete", {
                    "name": pod_name,
                    "namespace": namespace
                })

            elif action == "check_pod_logs":
                pod_name = params.get("pod_name")
                namespace = params.get("namespace", self.namespace)
                result = await self._send_request("pods_log", {
                    "name": pod_name,
                    "namespace": namespace,
                    "tailLines": params.get("tail_lines", 100)
                })

            elif action == "scale_deployment":
                # This requires getting and updating the deployment
                # For now, return not implemented
                return {
                    "success": False,
                    "error": "Scale deployment not yet implemented in STDIO mode"
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }

            # Process result
            if result and "result" in result:
                return {
                    "success": True,
                    "result": result["result"],
                    "action": action,
                    "params": params
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", {}).get("message", "Unknown error"),
                    "action": action,
                    "params": params
                }

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
            "get_namespaces"
        ]

        if self.enable_destructive_operations:
            capabilities.extend([
                "restart_pod",
                "scale_deployment",
                "delete_resource"
            ])

        return capabilities

    async def health_check(self) -> bool:
        """Check if the MCP server connection is healthy."""
        if not self._connected or not self.process:
            return False

        # Test with a simple request
        result = await self._send_request("namespaces_list", {})
        return result is not None

    async def discover_contexts(self) -> list[K8sContext]:
        """Discover available Kubernetes contexts."""
        try:
            # Run kubectl to get contexts
            result = await asyncio.create_subprocess_exec(
                "kubectl", "config", "get-contexts", "-o", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                contexts_data = json.loads(stdout.decode())
                contexts = []

                for ctx in contexts_data.get("contexts", []):
                    contexts.append(K8sContext(
                        name=ctx["name"],
                        cluster=ctx["context"]["cluster"],
                        namespace=ctx["context"].get("namespace", "default"),
                        is_current=ctx["name"] == contexts_data.get("current-context")
                    ))

                return contexts
            else:
                self.logger.error(f"Failed to get contexts: {stderr.decode()}")
                return []

        except Exception as e:
            self.logger.error(f"Error discovering contexts: {e}")
            return []

    async def test_connection(self, context_name: str | None = None) -> dict[str, Any]:
        """Test connection to a specific Kubernetes context."""
        # If different context requested, reconnect
        if context_name and context_name != self.context:
            await self.disconnect()
            self.context = context_name
            connected = await self.connect()

            if not connected:
                return {
                    "connected": False,
                    "error": "Failed to connect to Kubernetes cluster",
                    "context": context_name
                }

        # Test basic operations
        try:
            # Get cluster version
            version_result = await self._send_request("resources_get", {
                "apiVersion": "v1",
                "kind": "ComponentStatus",
                "name": "controller-manager"
            })

            # Get namespaces
            ns_result = await self._send_request("namespaces_list", {})

            return {
                "connected": True,
                "context": self.context or "current",
                "namespace": self.namespace,
                "namespaces_count": len(ns_result.get("result", [])) if ns_result else 0,
                "server_responsive": True
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "context": self.context or "current"
            }

    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information for health check."""
        return {
            "mode": "stdio",
            "context": self.context or "current",
            "namespace": self.namespace,
            "destructive_operations_enabled": self.enable_destructive_operations,
            "mcp_server": "kubernetes-mcp-server",
            "connected": self._connected,
            "process_running": self.process is not None and self.process.returncode is None
        }
