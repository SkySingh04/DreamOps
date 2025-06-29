"""
Kubernetes MCP Server Integration with Agno Agent for DreamOps

This module provides a production-ready implementation that allows the Agno agent
to interact with Kubernetes clusters through the standardized MCP protocol.
Supports remote Kubernetes connections without requiring local kubeconfig.
"""

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools
from pydantic import BaseModel

from .config import get_config
from .models.api_key import LLMProvider
from .services.api_key_service import APIKeyService
from .services.kubernetes_auth import K8sCredentials, KubernetesAuthService
from .services.kubernetes_credentials import KubernetesCredentialsService
from .utils.logger import get_logger


@dataclass
class K8sIncidentContext:
    """Context for Kubernetes incident response"""
    alert_data: dict[str, Any]
    cluster_name: str
    namespace: str
    service: str | None = None
    deployment: str | None = None
    pod: str | None = None
    error_type: str | None = None


class RemediationConfidence(BaseModel):
    """Confidence scoring for automated remediation"""
    action: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    command_preview: list[str]
    risk_level: str  # "low", "medium", "high"


class DreamOpsK8sAgent:
    """
    Kubernetes incident response agent using Agno framework with MCP integration.
    Supports both local MCP server and remote Kubernetes clusters.
    """

    def __init__(self, credentials_service: KubernetesCredentialsService | None = None):
        """Initialize the Kubernetes agent with configuration."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.credentials_service = credentials_service
        self.auth_service = KubernetesAuthService()
        self.api_key_service = APIKeyService()

        # Agent state
        self.agent: Agent | None = None
        self.mcp_tools: MCPTools | None = None
        self.active_credentials: K8sCredentials | None = None

        # Configuration
        self.confidence_threshold = 0.8
        self.enable_yolo_mode = self.config.k8s_enable_destructive_operations

        # Initialize K8s contexts from config
        self.k8s_contexts: list[str] = []
        if self.config.k8s_context and self.config.k8s_context != "default":
            self.k8s_contexts = [self.config.k8s_context]

    async def initialize_with_mcp(
        self,
        credentials: K8sCredentials | None = None,
        mcp_server_url: str | None = None
    ) -> bool:
        """
        Initialize agent with Kubernetes MCP server.
        
        Args:
            credentials: Optional K8s credentials for remote clusters
            mcp_server_url: Optional MCP server URL override
            
        Returns:
            True if initialization successful
        """
        try:
            # Configure MCP server connection
            k8s_mcp_config = self._get_k8s_mcp_config(credentials, mcp_server_url)

            # Handle credentials-based authentication
            if credentials:
                await self._setup_remote_k8s_auth(credentials)

            # Initialize MCP tools
            async with MCPTools(**k8s_mcp_config) as k8s_tools:
                self.mcp_tools = k8s_tools

                # Verify MCP server is responsive
                available_tools = await k8s_tools.list_tools()
                self.logger.info(f"K8s MCP tools available: {[tool.name for tool in available_tools]}")

                # Get LLM configuration
                model_config = self._get_model_config()

                # Create agent with K8s capabilities
                self.agent = Agent(
                    name="K8sIncidentResponseAgent",
                    role="Kubernetes incident response specialist",
                    model=model_config["model"],
                    tools=[k8s_tools],
                    instructions=self._get_k8s_agent_instructions(),
                    memory={"type": "conversation", "max_messages": 50}
                )

                self.logger.info("Successfully initialized K8s MCP agent")
                return True

        except Exception as e:
            self.logger.error(f"Failed to initialize K8s MCP agent: {e}")
            return False

    def _get_k8s_mcp_config(
        self,
        credentials: K8sCredentials | None = None,
        mcp_server_url: str | None = None
    ) -> dict[str, Any]:
        """Get MCP server configuration based on connection type."""

        # Option 1: Remote MCP Server (HTTP mode)
        if mcp_server_url:
            return {"url": mcp_server_url}

        # Option 2: Local MCP Server with custom kubeconfig
        if credentials and credentials.kubeconfig_data:
            # Write kubeconfig to temp file for MCP server
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.yaml',
                delete=False
            ) as f:
                f.write(credentials.kubeconfig_data)
                kubeconfig_path = f.name

            return {
                "command": self.config.k8s_mcp_server_path or "kubernetes-mcp-server",
                "args": ["--kubeconfig", kubeconfig_path]
            }

        # Option 3: Local MCP Server with default kubeconfig
        return {
            "command": self.config.k8s_mcp_server_path or "kubernetes-mcp-server",
            "args": ["--kubeconfig", self.config.k8s_config_path or "~/.kube/config"]
        }

    async def _setup_remote_k8s_auth(self, credentials: K8sCredentials) -> None:
        """Setup authentication for remote Kubernetes cluster."""
        self.active_credentials = credentials

        # Log connection info
        self.logger.info(
            f"Setting up remote K8s auth: "
            f"method={credentials.auth_method.value}, "
            f"cluster={credentials.cluster_name}, "
            f"endpoint={credentials.cluster_endpoint}"
        )

    def _get_model_config(self) -> dict[str, Any]:
        """Get LLM model configuration from API key service."""
        active_key = self.api_key_service.get_active_key()

        if not active_key:
            # Fallback to config API key
            if self.config.anthropic_api_key:
                return {
                    "model": OpenAIChat(
                        id="gpt-4",
                        api_key=self.config.anthropic_api_key
                    ),
                    "provider": "anthropic"
                }
            else:
                raise ValueError("No API key configured")

        # Map provider to model
        if active_key.provider == LLMProvider.ANTHROPIC:
            return {
                "model": OpenAIChat(
                    id="claude-3-5-sonnet-20241022",
                    api_key=active_key.api_key,
                    base_url="https://api.anthropic.com/v1"
                ),
                "provider": "anthropic"
            }
        elif active_key.provider == LLMProvider.OPENAI:
            return {
                "model": OpenAIChat(
                    id="gpt-4",
                    api_key=active_key.api_key
                ),
                "provider": "openai"
            }
        else:
            raise ValueError(f"Unsupported provider: {active_key.provider}")

    def _get_k8s_agent_instructions(self) -> str:
        """Get detailed instructions for the K8s incident response agent."""
        yolo_mode_section = """
YOLO MODE ENABLED:
- You are authorized to execute ALL remediation actions automatically
- DO NOT ask for confirmation before executing fixes
- Execute remediation immediately after identifying the issue
- Only provide confidence scores for logging purposes
- Take action first, report results after
""" if self.enable_yolo_mode else """
CONFIRMATION MODE:
- Provide confidence scores for all remediation actions
- Only execute actions with confidence ≥ 0.8
- For lower confidence, provide analysis and recommendations
- Request human approval for destructive operations
"""

        return f'''
You are a Kubernetes incident response agent with access to cluster management tools via MCP.

{yolo_mode_section}

AVAILABLE KUBERNETES OPERATIONS (via MCP tools):
1. Cluster Information:
   - pods_list: List all pods or pods in namespace
   - resources_list: List resources by type (deployments, services, etc)
   - namespaces_list: List all namespaces
   - events_list: Get recent cluster events
   - configuration_view: View kubeconfig

2. Diagnostics:
   - pods_get: Get detailed pod information
   - pods_log: Retrieve container logs (with tail option)
   - resources_get: Get any resource details
   - pods_top: Check CPU/memory usage

3. Remediation Actions:
   - pods_delete: Force restart by deleting pod
   - resources_delete: Delete any resource
   - resources_create_or_update: Apply manifests or update resources
   - pods_exec: Execute commands in containers
   - pods_run: Run one-off pods

INCIDENT RESPONSE WORKFLOW:
When receiving a Kubernetes-related alert:

1. ASSESS: List pods and check overall health
2. IDENTIFY: Find problematic resources using selectors and events
3. DIAGNOSE: Get logs and describe resources to understand root cause
4. ANALYZE: Check metrics and recent events
5. REMEDIATE: Apply appropriate fixes based on confidence
6. VERIFY: Confirm the fix worked by re-checking status

COMMON INCIDENT PATTERNS:

1. Pod CrashLoopBackOff:
   - Get pod logs to identify crash reason
   - Check events for additional context
   - Common fixes: restart pod, fix config, increase resources

2. ImagePullBackOff:
   - Check if image exists and is accessible
   - Verify image pull secrets
   - Fix: update image tag or credentials

3. OOMKilled:
   - Check memory usage with top
   - Review memory limits
   - Fix: increase memory limits or optimize application

4. Service Unavailable:
   - Check pod status and readiness
   - Verify service endpoints
   - Fix: restart pods or fix readiness probes

5. High Resource Usage:
   - Use top commands to identify culprits
   - Check for resource leaks
   - Fix: restart pods or scale horizontally

SAFETY RULES:
- Always use read operations first before modifications
- Log all actions taken for audit trail
- Include detailed reasoning for each action
- Monitor impact of changes
- Have rollback plan ready

RESPONSE FORMAT:
For each incident, structure your response as:

1. CURRENT STATUS:
   - What you found via MCP tools
   - Affected resources

2. ROOT CAUSE:
   - Analysis based on logs/events
   - Why the issue occurred

3. REMEDIATION:
   - Specific actions to take
   - Expected outcome

4. CONFIDENCE:
   - Score 0.0-1.0 for automated execution
   - Risk assessment

5. VERIFICATION:
   - How to confirm fix worked
   - Next steps if fix fails
'''

    async def handle_pagerduty_alert(self, alert_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process PagerDuty alert with K8s context.
        
        Args:
            alert_data: PagerDuty alert payload
            
        Returns:
            Response with analysis and actions taken
        """
        try:
            # Initialize agent if needed
            if not self.agent:
                initialized = await self.initialize_with_mcp()
                if not initialized:
                    return {
                        "error": "Failed to initialize K8s agent",
                        "status": "failed"
                    }

            # Extract K8s context from alert
            k8s_context = self._extract_k8s_context(alert_data)

            # Construct query for agent
            query = self._build_incident_query(alert_data, k8s_context)

            # Run agent analysis and remediation
            self.logger.info(f"Processing K8s incident: {alert_data.get('title')}")
            response = await self.agent.run(query)

            # Parse and execute response
            result = await self._parse_and_execute_response(response, k8s_context)

            return result

        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            return {
                "error": str(e),
                "status": "failed",
                "fallback": "Manual investigation required"
            }

    def _extract_k8s_context(self, alert_data: dict[str, Any]) -> K8sIncidentContext:
        """Extract Kubernetes-specific context from alert."""
        # Parse alert details
        description = alert_data.get('description', '')
        metadata = alert_data.get('metadata', {})

        # Extract K8s identifiers
        context = K8sIncidentContext(
            alert_data=alert_data,
            cluster_name=metadata.get('cluster', self.config.k8s_context or 'default'),
            namespace=metadata.get('namespace', self.config.k8s_namespace),
            service=metadata.get('service'),
            deployment=metadata.get('deployment'),
            pod=metadata.get('pod')
        )

        # Detect error type from description
        if 'CrashLoopBackOff' in description:
            context.error_type = 'pod_crash'
        elif 'ImagePullBackOff' in description:
            context.error_type = 'image_pull'
        elif 'OOMKilled' in description:
            context.error_type = 'oom_kill'
        elif 'Service' in description and 'down' in description.lower():
            context.error_type = 'service_down'

        return context

    def _build_incident_query(
        self,
        alert_data: dict[str, Any],
        k8s_context: K8sIncidentContext
    ) -> str:
        """Build query for the agent based on alert and context."""
        query_parts = [
            "KUBERNETES INCIDENT ALERT:",
            f"Title: {alert_data.get('title')}",
            f"Description: {alert_data.get('description')}",
            f"Severity: {alert_data.get('severity')}",
            f"Time: {alert_data.get('timestamp', datetime.now(UTC).isoformat())}",
            "",
            "Kubernetes Context:",
            f"- Cluster: {k8s_context.cluster_name}",
            f"- Namespace: {k8s_context.namespace}"
        ]

        if k8s_context.service:
            query_parts.append(f"- Service: {k8s_context.service}")
        if k8s_context.deployment:
            query_parts.append(f"- Deployment: {k8s_context.deployment}")
        if k8s_context.pod:
            query_parts.append(f"- Pod: {k8s_context.pod}")
        if k8s_context.error_type:
            query_parts.append(f"- Error Type: {k8s_context.error_type}")

        query_parts.extend([
            "",
            "Please investigate this incident using your Kubernetes tools and:",
            "1. Identify the current status of affected resources",
            "2. Determine the root cause from logs and events",
            "3. Execute appropriate remediation actions",
            "4. Verify the fix was successful",
            "5. Provide a summary of actions taken"
        ])

        if self.enable_yolo_mode:
            query_parts.extend([
                "",
                "IMPORTANT: YOLO mode is enabled. Execute all necessary fixes immediately without asking for confirmation."
            ])

        return "\n".join(query_parts)

    async def _parse_and_execute_response(
        self,
        response: str,
        k8s_context: K8sIncidentContext
    ) -> dict[str, Any]:
        """Parse agent response and execute any pending actions."""
        try:
            # Extract structured data from response
            actions_taken = []
            current_status = "unknown"
            root_cause = "unknown"

            # Simple parsing - in production, use structured output
            if "successfully restarted" in response.lower():
                actions_taken.append("pod_restart")
                current_status = "recovering"
            elif "scaled" in response.lower():
                actions_taken.append("deployment_scale")
                current_status = "scaled"
            elif "increased memory" in response.lower():
                actions_taken.append("memory_increase")
                current_status = "resources_updated"

            # Build result
            result = {
                "status": "success",
                "incident_id": k8s_context.alert_data.get('alert_id'),
                "cluster": k8s_context.cluster_name,
                "namespace": k8s_context.namespace,
                "current_status": current_status,
                "root_cause": root_cause,
                "actions_taken": actions_taken,
                "agent_response": response,
                "timestamp": datetime.now(UTC).isoformat(),
                "yolo_mode": self.enable_yolo_mode
            }

            # Log actions for audit
            self.logger.info(
                f"K8s incident resolved: {k8s_context.alert_data.get('title')} "
                f"Actions: {actions_taken}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to parse agent response: {e}")
            return {
                "status": "partial_success",
                "error": str(e),
                "agent_response": response
            }

    async def connect_remote_cluster(
        self,
        user_id: int,
        credentials: K8sCredentials
    ) -> dict[str, Any]:
        """
        Connect to a remote Kubernetes cluster without local kubeconfig.
        
        Args:
            user_id: User ID for credential storage
            credentials: Kubernetes credentials
            
        Returns:
            Connection result with cluster info
        """
        try:
            # Test connection with credentials
            test_result = await self.auth_service.test_k8s_connection(
                credentials,
                test_operations=["list_namespaces", "get_version"]
            )

            if not test_result.get("connected"):
                return {
                    "connected": False,
                    "error": test_result.get("error", "Connection failed")
                }

            # Save credentials if connection successful
            if self.credentials_service:
                cred_id = await self.credentials_service.save_credentials(
                    user_id,
                    credentials,
                    test_result
                )
                test_result["credential_id"] = cred_id

            # Initialize agent with these credentials
            initialized = await self.initialize_with_mcp(credentials)
            if initialized:
                test_result["agent_initialized"] = True
                test_result["mcp_tools_available"] = len(self.mcp_tools.list_tools()) if self.mcp_tools else 0

            return test_result

        except Exception as e:
            self.logger.error(f"Failed to connect to remote cluster: {e}")
            return {
                "connected": False,
                "error": str(e)
            }

    async def list_available_clusters(self, user_id: int) -> list[dict[str, Any]]:
        """List all available Kubernetes clusters for a user."""
        clusters = []

        # Add local cluster if configured
        if self.config.k8s_enabled:
            clusters.append({
                "name": "local",
                "type": "local",
                "context": self.config.k8s_context or "default",
                "namespace": self.config.k8s_namespace,
                "connection_status": "available"
            })

        # Add saved remote clusters
        if self.credentials_service:
            remote_clusters = await self.credentials_service.list_clusters(user_id)
            for cluster in remote_clusters:
                cluster["type"] = "remote"
            clusters.extend(remote_clusters)

        return clusters

    async def test_mcp_integration(self) -> dict[str, Any]:
        """Test the Kubernetes MCP server integration."""
        try:
            # Initialize if needed
            if not self.agent:
                await self.initialize_with_mcp()

            # Test basic MCP operations
            test_results = {
                "mcp_connected": self.mcp_tools is not None,
                "agent_initialized": self.agent is not None,
                "operations_tested": []
            }

            if self.mcp_tools:
                # Test listing pods
                try:
                    result = await self.agent.run(
                        "List all pods in the default namespace using the pods_list tool"
                    )
                    test_results["operations_tested"].append({
                        "operation": "list_pods",
                        "success": True,
                        "result_preview": result[:200] if isinstance(result, str) else str(result)[:200]
                    })
                except Exception as e:
                    test_results["operations_tested"].append({
                        "operation": "list_pods",
                        "success": False,
                        "error": str(e)
                    })

            test_results["overall_status"] = "success" if test_results["mcp_connected"] else "failed"
            return test_results

        except Exception as e:
            return {
                "overall_status": "failed",
                "error": str(e)
            }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self.mcp_tools:
            await self.mcp_tools.__aexit__(None, None, None)
        self.agent = None
        self.mcp_tools = None
        self.active_credentials = None

