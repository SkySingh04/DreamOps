"""Enhanced oncall agent with command execution capabilities."""

import logging
import re
from collections.abc import Callable
from typing import Any

from anthropic import AsyncAnthropic

from .agent import PagerAlert
from .agent_executor import AgentExecutor
from .api.schemas import AIMode
from .approval_manager import approval_manager
from .config import get_config
from .frontend_integration import (
    send_ai_action_to_dashboard,
)
from .mcp_integrations.base import MCPIntegration
from .mcp_integrations.kubernetes_mcp_only import KubernetesMCPOnlyIntegration
from .pagerduty_client import (
    acknowledge_pagerduty_incident,
    resolve_pagerduty_incident,
)
from .strategies.deterministic_k8s_resolver import DeterministicK8sResolver
from .strategies.kubernetes_resolver import KubernetesResolver


class EnhancedOncallAgent:
    """Enhanced AI agent with actual command execution capabilities."""

    def __init__(self, ai_mode: AIMode = AIMode.YOLO):
        """Initialize the enhanced oncall agent.
        
        Args:
            ai_mode: AI operation mode (YOLO, APPROVAL, PLAN)
        """
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.ai_mode = ai_mode
        self.mcp_integrations: dict[str, MCPIntegration] = {}

        # Initialize Anthropic client
        self.anthropic_client = AsyncAnthropic(api_key=self.config.anthropic_api_key)

        # Initialize Kubernetes MCP integration
        self.k8s_mcp = None
        self.k8s_resolver = None
        self.deterministic_resolver = None
        self.agent_executor = None

        if self.config.k8s_enabled:
            # Initialize agent executor without MCP integration - uses direct kubectl
            self.agent_executor = AgentExecutor(None)

            # Still keep k8s_mcp for context gathering if needed
            self.k8s_mcp = KubernetesMCPOnlyIntegration()
            self.register_mcp_integration("kubernetes_mcp", self.k8s_mcp)

            # Initialize resolvers
            self.k8s_resolver = KubernetesResolver(self.k8s_mcp)
            self.deterministic_resolver = DeterministicK8sResolver()

        # Alert patterns (from original agent)
        self.k8s_alert_patterns = {
            "pod_crash": re.compile(r"(Pod|pod).*(?:CrashLoopBackOff|crash|restarting)", re.IGNORECASE),
            "image_pull": re.compile(r"(ImagePullBackOff|ErrImagePull|Failed to pull image)", re.IGNORECASE),
            "high_memory": re.compile(r"(memory|Memory).*(?:high|above threshold|exceeded)", re.IGNORECASE),
            "high_cpu": re.compile(r"(cpu|CPU).*(?:high|above threshold|exceeded)", re.IGNORECASE),
            "service_down": re.compile(r"(Service|service).*(?:down|unavailable|not responding)", re.IGNORECASE),
            "deployment_failed": re.compile(r"(Deployment|deployment).*(?:failed|failing|error)", re.IGNORECASE),
            "node_issue": re.compile(r"(Node|node).*(?:NotReady|unreachable|down)", re.IGNORECASE),
            # CloudWatch/metrics-based alerts
            "pod_errors": re.compile(r"(PodErrors|ProblemPods|pod.*error)", re.IGNORECASE),
            "oom_kill": re.compile(r"(OOMKill|OOM Kill|Out of Memory|memory.*kill)", re.IGNORECASE),
        }

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

    async def handle_pager_alert(self, alert: PagerAlert, auto_remediate: bool = None) -> dict[str, Any]:
        """Handle an incoming pager alert with optional auto-remediation.
        
        Args:
            alert: The pager alert to handle
            auto_remediate: Override for auto-remediation (None uses mode default)
            
        Returns:
            Complete incident response with analysis and execution results
        """
        self.logger.info("=" * 80)
        self.logger.info(f"🚨 ENHANCED ONCALL AGENT TRIGGERED (Mode: {self.ai_mode.value}) 🚨")
        self.logger.info("=" * 80)
        self.logger.info(f"Alert ID: {alert.alert_id}")
        self.logger.info(f"Service: {alert.service_name}")
        self.logger.info(f"Severity: {alert.severity}")
        self.logger.info(f"Description: {alert.description[:200]}...")

        try:
            # Detect alert type
            k8s_alert_type = self._detect_k8s_alert_type(alert.description)

            # Gather context
            context = {}
            if k8s_alert_type and self.k8s_mcp:
                context = await self._gather_k8s_context(alert, k8s_alert_type)

            # Generate resolution actions BEFORE AI analysis so we can inform Claude
            resolution_actions = []
            if k8s_alert_type and self.k8s_resolver:
                resolution_actions = await self._generate_resolution_actions(
                    alert, k8s_alert_type, context
                )
            elif self.ai_mode == AIMode.YOLO and self.k8s_resolver:
                # In YOLO mode, even without specific alert type, try generic pod error resolution
                self.logger.info("🎲 YOLO MODE: No specific alert pattern matched, trying generic pod error resolution")
                k8s_alert_type = "pod_errors"  # Default to pod_errors
                resolution_actions = await self._generate_resolution_actions(
                    alert, k8s_alert_type, context
                )

            # Add resolution actions to context for Claude
            if resolution_actions:
                context["PROVEN_RESOLUTION_ACTIONS"] = []
                for action in resolution_actions:
                    action_info = {
                        "action": action.action_type,
                        "description": action.description,
                        "confidence": action.confidence,
                        "command": self._get_kubectl_command_for_action(action)
                    }
                    if action.confidence == 1.0:
                        action_info["note"] = "This is a PROVEN FIX that will definitely resolve this issue"
                    context["PROVEN_RESOLUTION_ACTIONS"].append(action_info)

                if any(action.confidence == 1.0 for action in resolution_actions):
                    context["IMPORTANT_NOTE"] = (
                        "The resolution actions above with confidence 1.0 are GUARANTEED FIXES. "
                        "These have been tested and will definitely resolve this specific issue. "
                        "In YOLO mode, these should be executed immediately with full confidence."
                    )

            # Get AI analysis (from Claude) - now with resolution actions in context
            analysis = await self._get_ai_analysis(alert, context)

            # Decide on auto-remediation
            should_remediate = self._should_auto_remediate(
                alert, resolution_actions, auto_remediate
            )

            # Execute remediation if appropriate
            execution_results = None
            if should_remediate and resolution_actions and self.agent_executor:
                self.logger.info(f"🤖 AUTO-REMEDIATION ENABLED (Mode: {self.ai_mode.value})")

                # Store current incident ID for approval callback
                self._current_incident_id = alert.alert_id

                # Acknowledge the PagerDuty incident (ignore errors in YOLO mode)
                try:
                    await acknowledge_pagerduty_incident(alert.alert_id)
                except Exception as e:
                    if self.ai_mode == AIMode.YOLO:
                        self.logger.warning(f"⚠️ YOLO MODE: Ignoring PagerDuty acknowledge error: {e}")
                    else:
                        raise

                # Send action to dashboard without incident_id (will be handled by frontend webhook)
                await send_ai_action_to_dashboard(
                    action="auto_remediation_started",
                    description=f"Starting auto-remediation with {len(resolution_actions)} actions",
                    incident_id=None  # Don't pass PagerDuty ID - frontend handles this via webhook
                )

                # Execute the remediation plan
                execution_results = await self.agent_executor.execute_remediation_plan(
                    actions=resolution_actions,
                    incident_id=alert.alert_id,
                    ai_mode=self.ai_mode,
                    confidence_threshold=0.7,
                    approval_callback=self._get_approval_callback()
                )

                self.logger.info(f"✅ Execution complete: {execution_results['actions_successful']}/{execution_results['actions_executed']} successful")

                # Send completion to dashboard
                await send_ai_action_to_dashboard(
                    action="auto_remediation_completed",
                    description=f"Completed {execution_results['actions_successful']} actions successfully",
                    incident_id=None  # Don't pass PagerDuty ID - frontend handles this via webhook
                )

                # Resolve PagerDuty incident
                # In YOLO mode, always try to resolve even with some failures
                if self.ai_mode == AIMode.YOLO or (execution_results['actions_failed'] == 0 and execution_results['actions_successful'] > 0):
                    if self.ai_mode == AIMode.YOLO and execution_results['actions_failed'] > 0:
                        resolution_note = (
                            f"[YOLO MODE] Automatically resolved by Oncall Agent. "
                            f"Executed {execution_results['actions_successful']}/{execution_results['actions_executed']} actions successfully. "
                            f"Some actions failed but forcing resolution in YOLO mode. "
                            f"Alert type: {k8s_alert_type or 'general'}"
                        )
                    else:
                        resolution_note = (
                            f"Automatically resolved by Oncall Agent. "
                            f"Executed {execution_results['actions_successful']} remediation actions successfully. "
                            f"Alert type: {k8s_alert_type or 'general'}"
                        )

                    try:
                        if await resolve_pagerduty_incident(alert.alert_id, resolution_note):
                            self.logger.info(f"✅ PagerDuty incident {alert.alert_id} resolved automatically")
                        else:
                            if self.ai_mode == AIMode.YOLO:
                                self.logger.warning("⚠️ YOLO MODE: PagerDuty resolution failed but treating as resolved")
                            else:
                                self.logger.warning(f"⚠️  Could not resolve PagerDuty incident {alert.alert_id} - manual resolution required")
                    except Exception as e:
                        if self.ai_mode == AIMode.YOLO:
                            self.logger.warning(f"⚠️ YOLO MODE: Ignoring PagerDuty resolution error: {e} - treating as resolved")
                            # Send resolution log to frontend even if PagerDuty API fails
                            from .api.log_streaming import log_stream_manager
                            await log_stream_manager.log_success(
                                f"✅ [YOLO] Incident resolved: {alert.description[:50]}... (PagerDuty API error ignored)",
                                incident_id=alert.alert_id,
                                stage="incident_resolved",
                                progress=1.0,
                                metadata={
                                    "forced_resolution": True,
                                    "pagerduty_error": str(e),
                                    "mode": "YOLO"
                                }
                            )
                        else:
                            self.logger.error(f"❌ Error resolving PagerDuty incident: {e}")
            else:
                self.logger.info("📋 No auto-remediation - providing analysis and recommendations only")

            # Prepare response
            result = {
                "alert_id": alert.alert_id,
                "status": "analyzed_and_executed" if execution_results else "analyzed",
                "ai_mode": self.ai_mode.value,
                "analysis": analysis,
                "k8s_alert_type": k8s_alert_type,
                "context": context,
                "resolution_actions": [
                    {
                        "action_type": action.action_type,
                        "description": action.description,
                        "confidence": action.confidence,
                        "risk_level": action.risk_level,
                        "params": action.params
                    }
                    for action in resolution_actions
                ],
                "auto_remediation_enabled": should_remediate,
                "execution_results": execution_results,
            }

            # Show command previews if in PLAN mode
            if self.ai_mode == AIMode.PLAN and resolution_actions:
                result["command_preview"] = await self._generate_command_preview(resolution_actions)

            return result

        except Exception as e:
            self.logger.error(f"Error handling alert {alert.alert_id}: {e}")
            return {
                "alert_id": alert.alert_id,
                "status": "error",
                "error": str(e),
                "ai_mode": self.ai_mode.value
            }

    def _detect_k8s_alert_type(self, description: str) -> str | None:
        """Detect if an alert is Kubernetes-related and return the type."""
        for alert_type, pattern in self.k8s_alert_patterns.items():
            if pattern.search(description):
                return alert_type
        return None

    async def _gather_k8s_context(self, alert: PagerAlert, alert_type: str) -> dict[str, Any]:
        """Gather Kubernetes-specific context."""
        context = {"alert_type": alert_type}
        metadata = alert.metadata
        namespace = metadata.get("namespace", "default")

        try:
            # Use enhanced MCP to gather context
            if alert_type == "pod_crash":
                pod_name = metadata.get("pod_name")
                if pod_name:
                    # Get pod logs
                    logs_result = await self.k8s_mcp.execute_action(
                        "get_pod_logs",
                        {"pod_name": pod_name, "namespace": namespace, "lines": 100}
                    )
                    context["pod_logs"] = logs_result

                    # Get pod status
                    status_result = await self.k8s_mcp.execute_action(
                        "check_pod_status",
                        {"pod_name": pod_name, "namespace": namespace}
                    )
                    context["pod_status"] = status_result

            elif alert_type == "service_down":
                service_name = metadata.get("service_name", alert.service_name)
                # Check service endpoints
                cmd = ["get", "endpoints", service_name, "-n", namespace, "-o", "json"]
                ep_result = await self.k8s_mcp.execute_kubectl_command(cmd, auto_approve=True)
                context["service_endpoints"] = ep_result

            # Add more context gathering as needed

        except Exception as e:
            self.logger.error(f"Error gathering K8s context: {e}")
            context["error"] = str(e)

        return context

    async def _get_ai_analysis(self, alert: PagerAlert, context: dict[str, Any]) -> str:
        """Get AI analysis from Claude."""
        prompt = f"""
        Analyze this production incident and provide actionable insights.
        
        Alert Details:
        - Service: {alert.service_name}
        - Severity: {alert.severity}
        - Description: {alert.description}
        - Metadata: {alert.metadata}
        
        Context Gathered:
        {self._format_context_for_prompt(context)}
        
        Provide:
        1. Root cause analysis
        2. Impact assessment
        3. Immediate remediation steps (be specific with commands)
        4. Long-term recommendations
        
        Current AI Mode: {self.ai_mode.value}
        """

        response = await self.anthropic_client.messages.create(
            model=self.config.claude_model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text if response.content else "No analysis available"

    def _format_context_for_prompt(self, context: dict[str, Any]) -> str:
        """Format context for Claude prompt."""
        if not context:
            return "No additional context available"

        formatted = []
        for key, value in context.items():
            if isinstance(value, dict) and "output" in value:
                formatted.append(f"{key}: {value.get('output', '')[:500]}...")
            else:
                formatted.append(f"{key}: {value}")

        return "\n".join(formatted)

    async def _generate_resolution_actions(
        self,
        alert: PagerAlert,
        alert_type: str,
        context: dict[str, Any]
    ) -> list:
        """Generate resolution actions using the Kubernetes resolver."""
        if not self.k8s_resolver:
            return []

        # First check for deterministic fixes
        if self.deterministic_resolver:
            deterministic_fixes = self.deterministic_resolver.get_deterministic_fixes(
                alert.description, alert.metadata
            )
            if deterministic_fixes:
                self.logger.info(f"Found {len(deterministic_fixes)} deterministic fixes!")
                return deterministic_fixes

        # Use the resolver to generate actions based on alert type
        if alert_type == "pod_crash":
            pod_name = alert.metadata.get("pod_name")
            namespace = alert.metadata.get("namespace", "default")
            if pod_name:
                return await self.k8s_resolver.resolve_pod_crash(pod_name, namespace, context)

        elif alert_type == "image_pull":
            pod_name = alert.metadata.get("pod_name")
            namespace = alert.metadata.get("namespace", "default")
            if pod_name:
                return await self.k8s_resolver.resolve_image_pull_error(pod_name, namespace, context)

        elif alert_type in ["high_memory", "high_cpu"]:
            deployment_name = alert.metadata.get("deployment_name")
            namespace = alert.metadata.get("namespace", "default")
            if deployment_name:
                resource_type = "memory" if alert_type == "high_memory" else "cpu"
                return await self.k8s_resolver.resolve_high_resource_usage(
                    resource_type, deployment_name, namespace, context
                )

        elif alert_type == "service_down":
            service_name = alert.metadata.get("service_name", alert.service_name)
            namespace = alert.metadata.get("namespace", "default")
            return await self.k8s_resolver.resolve_service_down(service_name, namespace, context)

        elif alert_type == "deployment_failed":
            deployment_name = alert.metadata.get("deployment_name")
            namespace = alert.metadata.get("namespace", "default")
            if deployment_name:
                return await self.k8s_resolver.resolve_deployment_failure(
                    deployment_name, namespace, context
                )

        elif alert_type == "pod_errors":
            # For generic pod errors, we need to find problematic pods first
            namespace = alert.metadata.get("namespace", "default")
            # Use a generic pod crash resolution approach
            return await self.k8s_resolver.resolve_generic_pod_errors(namespace, context)

        elif alert_type == "oom_kill":
            # For OOM kills, increase memory limits
            namespace = alert.metadata.get("namespace", "default")
            return await self.k8s_resolver.resolve_oom_kills(namespace, context)

        return []

    def _get_kubectl_command_for_action(self, action) -> str:
        """Generate the kubectl command that will be executed for this action."""
        params = action.params

        command_map = {
            "restart_pod": f"kubectl delete pod {params.get('pod_name', '<pod>')} -n {params.get('namespace', 'default')}",
            "scale_deployment": f"kubectl scale deployment {params.get('deployment_name', '<deployment>')} -n {params.get('namespace', 'default')} --replicas={params.get('replicas', 3)}",
            "rollback_deployment": f"kubectl rollout undo deployment {params.get('deployment_name', '<deployment>')} -n {params.get('namespace', 'default')}",
            "update_image": f"kubectl set image deployment/{params.get('deployment_name', '<deployment>')} {params.get('container_name', '<container>')}={params.get('new_image', '<image>')} -n {params.get('namespace', 'default')}",
            "delete_pods_by_label": f"kubectl delete pods -l {params.get('label_selector', '<selector>')} -n {params.get('namespace', 'default')}",
            "patch_memory_limit": f"kubectl patch deployment {params.get('deployment_name', '<deployment>')} -n {params.get('namespace', 'default')} --type json -p '[{{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"{params.get('memory_limit', '256Mi')}\"}}]'",
            "identify_error_pods": f"kubectl get pods -n {params.get('namespace', 'default')} | grep -E 'Error|CrashLoopBackOff|ImagePullBackOff'",
            "restart_error_pods": f"kubectl delete pods -n {params.get('namespace', 'default')} --field-selector=status.phase!=Running",
            "increase_memory_limits": f"kubectl patch deployment <deployment> -n {params.get('namespace', 'default')} --type json -p '[{{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"1Gi\"}}]'"
        }

        return command_map.get(action.action_type, f"kubectl {action.action_type} # Custom action")

    def _should_auto_remediate(
        self,
        alert: PagerAlert,
        resolution_actions: list,
        override: bool | None = None
    ) -> bool:
        """Determine if auto-remediation should be attempted."""
        if override is not None:
            return override

        # Check AI mode
        if self.ai_mode == AIMode.PLAN:
            return False  # Plan mode never executes

        if self.ai_mode == AIMode.YOLO:
            # YOLO mode ALWAYS executes if we have ANY actions
            # All simulated errors are fixable, so we trust our remediation
            if resolution_actions:
                self.logger.info(f"🚀 YOLO MODE: Found {len(resolution_actions)} actions - EXECUTING ALL!")
                return True
            else:
                self.logger.warning("⚠️  YOLO MODE: No resolution actions generated")

        if self.ai_mode == AIMode.APPROVAL:
            # Approval mode needs explicit approval (handled in executor)
            return True  # Let executor handle approval flow

        return False

    def _get_approval_callback(self) -> Callable | None:
        """Get approval callback for APPROVAL mode."""
        if self.ai_mode != AIMode.APPROVAL:
            return None

        # Create approval callback that uses the approval manager
        async def approval_callback(action):
            # Get the incident ID from the current context
            incident_id = getattr(self, '_current_incident_id', None)

            # Request approval through the approval manager
            approved = await approval_manager.request_approval(action, incident_id)

            return approved

        return approval_callback

    async def _generate_command_preview(self, resolution_actions: list) -> list[dict[str, Any]]:
        """Generate preview of commands that would be executed."""
        previews = []

        for action in resolution_actions:
            # Generate the kubectl command
            result = await self.k8s_mcp.execute_action(
                action.action_type,
                {**action.params, "dry_run": True}
            )

            if result.get("command"):
                previews.append({
                    "action": action.action_type,
                    "command": f"kubectl {' '.join(result['command'])}",
                    "risk_level": result.get("risk_assessment", {}).get("risk_level", "unknown"),
                    "confidence": action.confidence,
                    "would_execute": result.get("would_execute", False)
                })

        return previews

    async def set_ai_mode(self, mode: AIMode) -> None:
        """Change the AI operation mode."""
        self.logger.info(f"Changing AI mode from {self.ai_mode.value} to {mode.value}")
        self.ai_mode = mode

    async def shutdown(self) -> None:
        """Shutdown the agent and disconnect integrations."""
        self.logger.info("Shutting down enhanced oncall agent")
        for name, integration in self.mcp_integrations.items():
            try:
                await integration.disconnect()
                self.logger.info(f"Disconnected from {name}")
            except Exception as e:
                self.logger.error(f"Error disconnecting from {name}: {e}")
