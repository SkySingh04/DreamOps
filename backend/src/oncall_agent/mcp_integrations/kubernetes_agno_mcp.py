"""Kubernetes MCP Integration using Agno's MCPTools.

This is the correct way to integrate with MCP servers - using Agno's built-in
MCPTools wrapper instead of manually handling HTTP/SSE protocols.
"""

import logging
from datetime import datetime
from typing import Any

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.base import MCPIntegration


class KubernetesAgnoMCPIntegration(MCPIntegration):
    """Kubernetes integration using Agno's MCPTools wrapper."""

    def __init__(self, namespace: str = "default",
                 enable_destructive_operations: bool = False):
        """Initialize Kubernetes MCP integration with Agno.

        Args:
            namespace: Default Kubernetes namespace to operate in
            enable_destructive_operations: Whether to allow destructive operations
        """
        super().__init__(name="kubernetes_agno_mcp")
        self.config = get_config()
        self.logger = logging.getLogger(__name__)

        self.namespace = namespace
        self.enable_destructive_operations = enable_destructive_operations

        # Use Agno's MCPTools instead of custom client!
        self.mcp_tools: MCPTools | None = None
        self.agent: Agent | None = None
        self.connected = False
        self.connection_time: datetime | None = None

    async def connect(self) -> bool:
        """Connect to Kubernetes MCP server using Agno."""
        try:
            self.logger.info("Connecting to Kubernetes MCP server via Agno...")

            # Get the MCP server command from config
            mcp_command = self.config.k8s_mcp_command or "npx -y kubernetes-mcp-server@latest"

            self.logger.info(f"Starting MCP server with command: {mcp_command}")

            # Initialize MCPTools with the kubernetes-mcp-server command
            # Agno handles all protocol details (stdio/HTTP/SSE)
            self.mcp_tools = MCPTools(command=mcp_command)

            # Connect - Agno handles everything!
            await self.mcp_tools.connect()

            self.logger.info("MCP tools connected, creating agent...")

            # Choose model based on LiteLLM configuration
            if self.config.use_litellm and self.config.litellm_api_key:
                self.logger.info(f"Using LiteLLM for Agno agent at {self.config.litellm_api_base}")
                model = OpenAIChat(
                    id=self.config.claude_model,
                    api_key=self.config.litellm_api_key,
                    base_url=self.config.litellm_api_base
                )
            else:
                self.logger.info("Using direct Anthropic API for Agno agent")
                model = Claude(id=self.config.claude_model)

            # Create Agno agent with MCP tools
            self.agent = Agent(
                name="KubernetesAgent",
                model=model,
                tools=[self.mcp_tools],
                instructions=f"""
You are a Kubernetes operations assistant with access to MCP tools for managing Kubernetes resources.

Current Configuration:
- Default namespace: {self.namespace}
- Destructive operations: {'ENABLED ⚠️' if self.enable_destructive_operations else 'DISABLED ✅'}

Available Operations:
- List pods, deployments, services, and other resources
- Describe resources to get detailed information
- Get pod logs for debugging
- View cluster events
{'''- Delete pods to force restarts
- Scale deployments up or down
- Apply manifests to create/update resources''' if self.enable_destructive_operations else '- (Destructive operations disabled)'}

When executing operations:
1. Always specify the namespace explicitly if different from default
2. Provide clear, actionable information in responses
3. Format output in a structured, readable way
4. For errors, explain what went wrong and suggest fixes

Safety Guidelines:
{'- You CAN perform destructive operations as they are enabled' if self.enable_destructive_operations else '- You CANNOT perform destructive operations - they are disabled'}
- Always verify resource names before operations
- Prefer read-only operations when possible
- Log all operations clearly
                """,
                markdown=True,
                debug_mode=False
            )

            self.connected = True
            self.connection_time = datetime.utcnow()
            self.logger.info("✅ Kubernetes MCP integration connected via Agno!")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Kubernetes MCP server: {e}")
            self.connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        try:
            if self.mcp_tools:
                await self.mcp_tools.close()
                self.mcp_tools = None

            self.agent = None
            self.connected = False
            self.connection_time = None
            self.logger.info("Disconnected from Kubernetes MCP server")

        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")

    async def fetch_context(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch Kubernetes context using the Agno agent.

        Args:
            params: Parameters including:
                - type: Context type (pods, deployments, services, events, etc.)
                - namespace: Kubernetes namespace (optional)

        Returns:
            Dictionary with context data or error
        """
        if not self.agent:
            return {"error": "Not connected to MCP server"}

        try:
            context_type = params.get("type", "pods")
            namespace = params.get("namespace", self.namespace)

            # Construct natural language query for the agent
            if context_type == "pods":
                query = f"List all pods in namespace {namespace} with their status"
            elif context_type == "deployments":
                query = f"List all deployments in namespace {namespace}"
            elif context_type == "services":
                query = f"List all services in namespace {namespace}"
            elif context_type == "events":
                query = f"Get recent events in namespace {namespace}"
            elif context_type == "namespaces":
                query = "List all namespaces in the cluster"
            elif context_type == "metrics":
                query = f"Get resource usage metrics for pods in namespace {namespace}"
            else:
                query = f"Get information about {context_type} in namespace {namespace}"

            self.logger.info(f"Fetching context: {query}")

            # Let the agent execute using MCP tools
            response = await self.agent.arun(query)

            return {
                "success": True,
                context_type: response.content if hasattr(response, 'content') else str(response)
            }

        except Exception as e:
            self.logger.error(f"Error fetching context: {e}")
            return {"error": str(e)}

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a Kubernetes action using the Agno agent.

        Args:
            action: Action to execute (restart_pod, scale_deployment, etc.)
            params: Action parameters

        Returns:
            Dictionary with execution result
        """
        if not self.agent:
            return {"success": False, "error": "Not connected to MCP server"}

        try:
            # Check if destructive operations are allowed
            destructive_actions = {
                'restart_pod', 'delete_resource', 'scale_deployment',
                'apply_manifest', 'patch_resource', 'set_image',
                'delete_pod', 'rollback_deployment'
            }

            if action in destructive_actions and not self.enable_destructive_operations:
                return {
                    "success": False,
                    "error": f"Destructive operation '{action}' not enabled. Set K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true to enable."
                }

            # Construct natural language query for the agent
            query = self._action_to_query(action, params)

            self.logger.info(f"Executing action: {action}")
            self.logger.info(f"Query: {query}")

            # Let the agent execute using MCP tools
            response = await self.agent.arun(query)

            result_content = response.content if hasattr(response, 'content') else str(response)

            return {
                "success": True,
                "message": result_content,
                "action": action,
                "params": params
            }

        except Exception as e:
            self.logger.error(f"Error executing action {action}: {e}")
            return {"success": False, "error": str(e)}

    def _action_to_query(self, action: str, params: dict[str, Any]) -> str:
        """Convert action and params to natural language query.

        This translates high-level actions into natural language that the
        Agno agent can understand and execute using MCP tools.
        """
        namespace = params.get('namespace', self.namespace)

        if action == "restart_pod":
            pod_name = params.get('pod_name')
            return f"Delete pod {pod_name} in namespace {namespace} to force a restart. Confirm the pod is deleted."

        elif action == "scale_deployment":
            deployment = params.get('deployment_name')
            replicas = params.get('replicas')
            return f"Scale deployment {deployment} in namespace {namespace} to {replicas} replicas. Show the current and desired replica counts."

        elif action == "check_pod_logs" or action == "get_logs":
            pod_name = params.get('pod_name')
            tail_lines = params.get('tail_lines', 100)
            container = params.get('container')
            if container:
                return f"Get the last {tail_lines} lines of logs from container {container} in pod {pod_name} in namespace {namespace}"
            return f"Get the last {tail_lines} lines of logs from pod {pod_name} in namespace {namespace}"

        elif action == "describe_resource":
            kind = params.get('kind')
            name = params.get('name')
            return f"Describe {kind} named {name} in namespace {namespace}. Include status, conditions, and recent events."

        elif action == "delete_resource":
            kind = params.get('kind')
            name = params.get('name')
            return f"Delete {kind} named {name} in namespace {namespace}. Confirm when deleted."

        elif action == "apply_manifest":
            manifest = params.get('manifest')
            return f"Apply the following Kubernetes manifest:\n\n{manifest}\n\nConfirm what resources were created or updated."

        elif action == "patch_resource":
            kind = params.get('kind')
            name = params.get('name')
            patch = params.get('patch')
            return f"Patch {kind} named {name} in namespace {namespace} with the following changes: {patch}"

        elif action == "set_image":
            deployment = params.get('name') or params.get('deployment_name')
            container = params.get('container')
            image = params.get('image')
            return f"Update the image for container {container} in deployment {deployment} in namespace {namespace} to {image}"

        elif action == "rollback_deployment":
            deployment = params.get('deployment_name')
            return f"Rollback deployment {deployment} in namespace {namespace} to the previous revision"

        else:
            # Generic fallback
            return f"Execute Kubernetes operation: {action} with parameters: {params}"

    def get_capabilities(self) -> list[str]:
        """Get list of available capabilities."""
        capabilities = [
            "get_pods",
            "get_deployments",
            "get_services",
            "get_logs",
            "describe_resource",
            "get_events",
            "get_namespaces",
            "get_metrics"
        ]

        if self.enable_destructive_operations:
            capabilities.extend([
                "restart_pod",
                "scale_deployment",
                "delete_resource",
                "apply_manifest",
                "patch_resource",
                "set_image",
                "rollback_deployment"
            ])

        return capabilities

    async def health_check(self) -> bool:
        """Check if the MCP connection is healthy."""
        if not self.connected or not self.mcp_tools:
            return False

        try:
            # Try a simple operation to verify connectivity
            result = await self.fetch_context({"type": "namespaces"})
            return "error" not in result
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information for diagnostics."""
        return {
            "namespace": self.namespace,
            "destructive_operations_enabled": self.enable_destructive_operations,
            "connected": self.connected,
            "connection_time": self.connection_time.isoformat() if self.connection_time else None,
            "mcp_mode": "agno",
            "mcp_command": self.config.k8s_mcp_command,
            "integration_type": "Agno MCPTools"
        }

    # Compatibility methods for existing code

    async def test_connection(self, context_name: str = None, namespace: str = None) -> dict[str, Any]:
        """Test connection to the Kubernetes cluster."""
        try:
            if not self.connected:
                connected = await self.connect()
                if not connected:
                    return {"connected": False, "error": "Failed to connect to MCP server"}

            # Try to list namespaces as a connection test
            result = await self.fetch_context({"type": "namespaces"})

            if "error" not in result:
                return {
                    "connected": True,
                    "context": context_name or "current",
                    "namespace": namespace or self.namespace,
                    "integration": "Agno MCP"
                }
            else:
                return {"connected": False, "error": result.get("error", "Connection test failed")}

        except Exception as e:
            return {"connected": False, "error": str(e)}

    async def discover_contexts(self) -> list[dict[str, Any]]:
        """Discover available Kubernetes contexts."""
        # With MCP, we use the current kubectl context
        return [{
            "name": "current",
            "cluster": "current-cluster",
            "namespace": self.namespace,
            "via": "MCP"
        }]

    async def get_cluster_info(self, context_name: str = None) -> dict[str, Any]:
        """Get cluster information."""
        try:
            namespaces_result = await self.fetch_context({"type": "namespaces"})

            return {
                "context": context_name or "current",
                "connected": "error" not in namespaces_result,
                "integration": "Agno MCP",
                "namespace": self.namespace
            }

        except Exception as e:
            return {"error": str(e)}
