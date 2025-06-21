"""Main agent logic using AGNO framework for oncall incident response."""

import logging
import re
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from .config import get_config
from .mcp_integrations.base import MCPIntegration
from .mcp_integrations.kubernetes import KubernetesMCPIntegration


class PagerAlert(BaseModel):
    """Model for incoming pager alerts."""
    alert_id: str
    severity: str
    service_name: str
    description: str
    timestamp: str
    metadata: dict[str, Any] = {}


class OncallAgent:
    """AI agent for handling oncall incidents using AGNO framework."""

    def __init__(self):
        """Initialize the oncall agent with configuration."""
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.mcp_integrations: dict[str, MCPIntegration] = {}

        # Initialize Anthropic client
        self.anthropic_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)

        # Define Kubernetes alert patterns
        self.k8s_alert_patterns = {
            "pod_crash": re.compile(r"(Pod|pod).*(?:CrashLoopBackOff|crash|restarting)", re.IGNORECASE),
            "image_pull": re.compile(r"(ImagePullBackOff|ErrImagePull|Failed to pull image)", re.IGNORECASE),
            "high_memory": re.compile(r"(memory|Memory).*(?:high|above threshold|exceeded)", re.IGNORECASE),
            "high_cpu": re.compile(r"(cpu|CPU).*(?:high|above threshold|exceeded)", re.IGNORECASE),
            "service_down": re.compile(r"(Service|service).*(?:down|unavailable|not responding)", re.IGNORECASE),
            "deployment_failed": re.compile(r"(Deployment|deployment).*(?:failed|failing|error)", re.IGNORECASE),
            "node_issue": re.compile(r"(Node|node).*(?:NotReady|unreachable|down)", re.IGNORECASE),
        }

        # Initialize Kubernetes integration if enabled
        if self.config.k8s_enabled:
            self.k8s_integration = KubernetesMCPIntegration()
            self.register_mcp_integration("kubernetes", self.k8s_integration)

    def register_mcp_integration(self, name: str, integration: MCPIntegration) -> None:
        """Register an MCP integration with the agent."""
        self.logger.info(f"Registering MCP integration: {name}")
        self.mcp_integrations[name] = integration

    async def connect_integrations(self) -> None:
        """Connect all registered MCP integrations."""
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.connect()
                self.logger.info(f"Connected to MCP integration: {name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to {name}: {e}")

    async def handle_pager_alert(self, alert: PagerAlert) -> dict[str, Any]:
        """Handle an incoming pager alert."""
        self.logger.info(f"Handling pager alert: {alert.alert_id} for service: {alert.service_name}")

        try:
            # Detect if this is a Kubernetes-related alert
            k8s_alert_type = self._detect_k8s_alert_type(alert.description)
            k8s_context = {}

            if k8s_alert_type and "kubernetes" in self.mcp_integrations:
                self.logger.info(f"Detected Kubernetes alert type: {k8s_alert_type}")

                # Gather Kubernetes-specific context based on alert type
                k8s_context = await self._gather_k8s_context(alert, k8s_alert_type)

            # Create a prompt for Claude to analyze the alert
            prompt = f"""
            Analyze this oncall alert and provide a response plan:
            
            Alert ID: {alert.alert_id}
            Service: {alert.service_name}
            Severity: {alert.severity}
            Description: {alert.description}
            Timestamp: {alert.timestamp}
            Metadata: {alert.metadata}
            
            {f"Kubernetes Alert Type: {k8s_alert_type}" if k8s_alert_type else ""}
            {f"Kubernetes Context: {k8s_context}" if k8s_context else ""}
            
            Please provide:
            1. Initial assessment of the issue
            2. Recommended immediate actions
            3. Data to collect from monitoring systems
            4. Potential root causes
            5. Escalation criteria
            
            {"For this Kubernetes issue, also suggest specific kubectl commands or automated fixes." if k8s_alert_type else ""}
            """

            # Use Claude for analysis
            response = await self.anthropic_client.messages.create(
                model=self.config.claude_model,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract the response
            analysis = response.content[0].text if response.content else "No analysis available"

            # Create response structure
            result = {
                "alert_id": alert.alert_id,
                "status": "analyzed",
                "analysis": analysis,
                "timestamp": alert.timestamp,
                "available_integrations": list(self.mcp_integrations.keys()),
                "k8s_alert_type": k8s_alert_type,
                "k8s_context": k8s_context
            }

            # If it's a Kubernetes alert and we have confidence, suggest automated actions
            if k8s_alert_type and k8s_context.get("automated_actions"):
                result["suggested_actions"] = k8s_context["automated_actions"]

            # Log the handling
            self.logger.info(f"Alert {alert.alert_id} analyzed successfully")

            return result

        except Exception as e:
            self.logger.error(f"Error handling alert {alert.alert_id}: {e}")
            return {
                "alert_id": alert.alert_id,
                "status": "error",
                "error": str(e)
            }

    def _detect_k8s_alert_type(self, description: str) -> str | None:
        """Detect if an alert is Kubernetes-related and return the type."""
        for alert_type, pattern in self.k8s_alert_patterns.items():
            if pattern.search(description):
                return alert_type
        return None

    async def _gather_k8s_context(self, alert: PagerAlert, alert_type: str) -> dict[str, Any]:
        """Gather Kubernetes-specific context based on alert type."""
        k8s = self.mcp_integrations.get("kubernetes")
        if not k8s:
            return {}

        context = {"alert_type": alert_type}
        metadata = alert.metadata
        namespace = metadata.get("namespace", "default")

        try:
            if alert_type == "pod_crash":
                pod_name = metadata.get("pod_name")
                if pod_name:
                    # Get pod logs
                    logs = await k8s.get_pod_logs(pod_name, namespace, tail_lines=100)
                    context["pod_logs"] = logs

                    # Get pod events
                    events = await k8s.get_pod_events(pod_name, namespace)
                    context["pod_events"] = events

                    # Get pod description
                    description = await k8s.describe_pod(pod_name, namespace)
                    context["pod_description"] = description

                    # Suggest automated actions
                    context["automated_actions"] = [
                        {
                            "action": "restart_pod",
                            "confidence": 0.7,
                            "params": {"pod_name": pod_name, "namespace": namespace},
                            "reason": "Pod is in CrashLoopBackOff, restart may resolve transient issues"
                        }
                    ]
                else:
                    # List all problematic pods
                    pods = await k8s.list_pods(namespace)
                    context["problematic_pods"] = [
                        p for p in pods.get("pods", [])
                        if p.get("status") in ["CrashLoopBackOff", "Error"]
                    ]

            elif alert_type == "image_pull":
                pod_name = metadata.get("pod_name")
                if pod_name:
                    events = await k8s.get_pod_events(pod_name, namespace)
                    context["pod_events"] = events
                    context["recommendation"] = "Check image name, registry credentials, and network connectivity"

            elif alert_type in ["high_memory", "high_cpu"]:
                # Get resource usage
                deployment_name = metadata.get("deployment_name")
                if deployment_name:
                    deployment_status = await k8s.get_deployment_status(deployment_name, namespace)
                    context["deployment_status"] = deployment_status

                    # Suggest scaling
                    current_replicas = deployment_status.get("deployment", {}).get("replicas", {}).get("desired", 1)
                    context["automated_actions"] = [
                        {
                            "action": "scale_deployment",
                            "confidence": 0.6,
                            "params": {
                                "deployment_name": deployment_name,
                                "namespace": namespace,
                                "replicas": current_replicas + 1
                            },
                            "reason": f"High {alert_type.split('_')[1]} usage, scaling up may help"
                        }
                    ]

            elif alert_type == "service_down":
                service_name = metadata.get("service_name", alert.service_name)
                service_status = await k8s.get_service_status(service_name, namespace)
                context["service_status"] = service_status

                # Check if pods are running
                if service_status.get("service", {}).get("endpoint_count", 0) == 0:
                    context["issue"] = "No endpoints available for service"
                    # Get pods matching service selector
                    selector = service_status.get("service", {}).get("selector", {})
                    if selector:
                        pods = await k8s.list_pods(namespace)
                        matching_pods = [
                            p for p in pods.get("pods", [])
                            if all(p.get("labels", {}).get(k) == v for k, v in selector.items())
                        ]
                        context["matching_pods"] = matching_pods

            elif alert_type == "deployment_failed":
                deployment_name = metadata.get("deployment_name")
                if deployment_name:
                    deployment_status = await k8s.get_deployment_status(deployment_name, namespace)
                    context["deployment_status"] = deployment_status

                    # Check if rollback is needed
                    if not deployment_status.get("deployment", {}).get("healthy", True):
                        context["automated_actions"] = [
                            {
                                "action": "rollback_deployment",
                                "confidence": 0.8,
                                "params": {
                                    "deployment_name": deployment_name,
                                    "namespace": namespace
                                },
                                "reason": "Deployment is unhealthy, rolling back to previous version"
                            }
                        ]

        except Exception as e:
            self.logger.error(f"Error gathering Kubernetes context: {e}")
            context["error"] = str(e)

        return context

    async def shutdown(self) -> None:
        """Shutdown the agent and disconnect integrations."""
        self.logger.info("Shutting down oncall agent")
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.disconnect()
                self.logger.info(f"Disconnected from {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")
