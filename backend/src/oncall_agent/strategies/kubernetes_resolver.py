"""Kubernetes-specific resolution strategies for common issues."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.oncall_agent.mcp_integrations.kubernetes import KubernetesMCPIntegration


@dataclass
class ResolutionAction:
    """Represents a resolution action with confidence scoring."""
    action_type: str
    description: str
    params: dict[str, Any]
    confidence: float  # 0.0 to 1.0
    risk_level: str  # "low", "medium", "high"
    estimated_time: str  # e.g., "30s", "5m"
    rollback_possible: bool
    prerequisites: list[str] = None


class KubernetesResolver:
    """Implements resolution strategies for Kubernetes issues."""

    def __init__(self, k8s_integration: KubernetesMCPIntegration):
        """Initialize the resolver with a Kubernetes integration."""
        self.k8s = k8s_integration
        self.logger = logging.getLogger(__name__)
        self.resolution_history = []

    async def resolve_pod_crash(self, pod_name: str, namespace: str, context: dict[str, Any]) -> list[ResolutionAction]:
        """Generate resolution actions for a crashing pod."""
        actions = []

        # Analyze the context to determine the cause
        pod_logs = context.get("pod_logs", {}).get("logs", "")
        pod_events = context.get("pod_events", {}).get("events", [])

        # Strategy 1: Check for OOM kills
        if "OOMKilled" in str(pod_events) or "memory" in pod_logs.lower():
            actions.append(ResolutionAction(
                action_type="increase_memory_limit",
                description="Increase pod memory limits to prevent OOM kills",
                params={
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "memory_increase": "50%"
                },
                confidence=0.8,
                risk_level="low",
                estimated_time="2m",
                rollback_possible=True,
                prerequisites=["deployment_exists", "not_statefulset"]
            ))

        # Strategy 2: Check for configuration issues
        if "config" in pod_logs.lower() or "permission" in pod_logs.lower():
            actions.append(ResolutionAction(
                action_type="check_configmaps_secrets",
                description="Verify ConfigMaps and Secrets are properly mounted",
                params={
                    "pod_name": pod_name,
                    "namespace": namespace
                },
                confidence=0.7,
                risk_level="low",
                estimated_time="30s",
                rollback_possible=False
            ))

        # Strategy 3: Simple restart (transient issues)
        restart_count = self._get_restart_count_from_events(pod_events)
        if restart_count < 5:  # Don't suggest restart if it's been restarting too much
            actions.append(ResolutionAction(
                action_type="restart_pod",
                description="Delete pod to trigger a fresh restart",
                params={
                    "pod_name": pod_name,
                    "namespace": namespace
                },
                confidence=0.6,
                risk_level="low",
                estimated_time="1m",
                rollback_possible=False,
                prerequisites=["managed_by_controller"]
            ))
        else:
            # Too many restarts, suggest investigation
            actions.append(ResolutionAction(
                action_type="manual_investigation",
                description="Pod has restarted too many times, manual investigation required",
                params={
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "restart_count": restart_count
                },
                confidence=0.9,
                risk_level="low",
                estimated_time="15m",
                rollback_possible=False
            ))

        # Strategy 4: Check for dependency issues
        if "connection" in pod_logs.lower() or "timeout" in pod_logs.lower():
            actions.append(ResolutionAction(
                action_type="check_dependencies",
                description="Verify dependent services are healthy",
                params={
                    "pod_name": pod_name,
                    "namespace": namespace
                },
                confidence=0.7,
                risk_level="low",
                estimated_time="2m",
                rollback_possible=False
            ))

        return sorted(actions, key=lambda x: x.confidence, reverse=True)

    async def resolve_image_pull_error(self, pod_name: str, namespace: str, context: dict[str, Any]) -> list[ResolutionAction]:
        """Generate resolution actions for image pull errors."""
        actions = []
        pod_events = context.get("pod_events", {}).get("events", [])

        # Extract image name from events
        image_name = self._extract_image_from_events(pod_events)

        # Strategy 1: Check registry credentials
        actions.append(ResolutionAction(
            action_type="verify_image_pull_secret",
            description="Verify image pull secrets are correctly configured",
            params={
                "namespace": namespace,
                "image": image_name
            },
            confidence=0.8,
            risk_level="low",
            estimated_time="1m",
            rollback_possible=False
        ))

        # Strategy 2: Verify image exists
        actions.append(ResolutionAction(
            action_type="verify_image_exists",
            description="Check if the image exists in the registry",
            params={
                "image": image_name
            },
            confidence=0.9,
            risk_level="low",
            estimated_time="30s",
            rollback_possible=False
        ))

        # Strategy 3: Try previous image version
        if image_name and ":" in image_name:
            actions.append(ResolutionAction(
                action_type="rollback_image_version",
                description="Roll back to previous working image version",
                params={
                    "pod_name": pod_name,
                    "namespace": namespace,
                    "current_image": image_name
                },
                confidence=0.7,
                risk_level="medium",
                estimated_time="5m",
                rollback_possible=True
            ))

        return sorted(actions, key=lambda x: x.confidence, reverse=True)

    async def resolve_high_resource_usage(self, resource_type: str, deployment_name: str,
                                        namespace: str, context: dict[str, Any]) -> list[ResolutionAction]:
        """Generate resolution actions for high CPU/memory usage."""
        actions = []
        deployment_status = context.get("deployment_status", {}).get("deployment", {})
        current_replicas = deployment_status.get("replicas", {}).get("desired", 1)

        # Strategy 1: Horizontal scaling
        if current_replicas < 10:  # Arbitrary max limit
            actions.append(ResolutionAction(
                action_type="scale_deployment",
                description=f"Scale deployment to handle high {resource_type} load",
                params={
                    "deployment_name": deployment_name,
                    "namespace": namespace,
                    "replicas": min(current_replicas + 2, 10)
                },
                confidence=0.8,
                risk_level="low",
                estimated_time="2m",
                rollback_possible=True
            ))

        # Strategy 2: Vertical scaling (increase limits)
        actions.append(ResolutionAction(
            action_type=f"increase_{resource_type}_limits",
            description=f"Increase {resource_type} limits for pods",
            params={
                "deployment_name": deployment_name,
                "namespace": namespace,
                "increase_percentage": 50
            },
            confidence=0.7,
            risk_level="medium",
            estimated_time="5m",
            rollback_possible=True
        ))

        # Strategy 3: Check for resource leaks
        if resource_type == "memory":
            actions.append(ResolutionAction(
                action_type="check_memory_leak",
                description="Analyze application for potential memory leaks",
                params={
                    "deployment_name": deployment_name,
                    "namespace": namespace
                },
                confidence=0.6,
                risk_level="low",
                estimated_time="10m",
                rollback_possible=False
            ))

        return sorted(actions, key=lambda x: x.confidence, reverse=True)

    async def resolve_service_down(self, service_name: str, namespace: str, context: dict[str, Any]) -> list[ResolutionAction]:
        """Generate resolution actions for service down issues."""
        actions = []
        service_status = context.get("service_status", {}).get("service", {})
        endpoint_count = service_status.get("endpoint_count", 0)

        if endpoint_count == 0:
            # No endpoints available
            selector = service_status.get("selector", {})
            matching_pods = context.get("matching_pods", [])

            if not matching_pods:
                # No pods match the selector
                actions.append(ResolutionAction(
                    action_type="deploy_missing_pods",
                    description="Deploy pods that match the service selector",
                    params={
                        "service_name": service_name,
                        "namespace": namespace,
                        "selector": selector
                    },
                    confidence=0.9,
                    risk_level="low",
                    estimated_time="3m",
                    rollback_possible=True
                ))
            else:
                # Pods exist but not ready
                for pod in matching_pods:
                    if pod.get("status") != "Running":
                        actions.append(ResolutionAction(
                            action_type="fix_pod_issues",
                            description=f"Fix issues with pod {pod.get('name')}",
                            params={
                                "pod_name": pod.get("name"),
                                "namespace": namespace,
                                "status": pod.get("status")
                            },
                            confidence=0.8,
                            risk_level="low",
                            estimated_time="5m",
                            rollback_possible=False
                        ))

        # Strategy: Check service configuration
        actions.append(ResolutionAction(
            action_type="verify_service_config",
            description="Verify service selector and port configuration",
            params={
                "service_name": service_name,
                "namespace": namespace
            },
            confidence=0.7,
            risk_level="low",
            estimated_time="1m",
            rollback_possible=False
        ))

        return sorted(actions, key=lambda x: x.confidence, reverse=True)

    async def resolve_deployment_failure(self, deployment_name: str, namespace: str, context: dict[str, Any]) -> list[ResolutionAction]:
        """Generate resolution actions for deployment failures."""
        actions = []
        deployment_status = context.get("deployment_status", {}).get("deployment", {})

        # Strategy 1: Rollback to previous version
        if not deployment_status.get("healthy", True):
            actions.append(ResolutionAction(
                action_type="rollback_deployment",
                description="Roll back to previous working version",
                params={
                    "deployment_name": deployment_name,
                    "namespace": namespace
                },
                confidence=0.9,
                risk_level="low",
                estimated_time="3m",
                rollback_possible=False  # This IS the rollback
            ))

        # Strategy 2: Check resource quotas
        actions.append(ResolutionAction(
            action_type="check_resource_quotas",
            description="Verify namespace resource quotas are not exceeded",
            params={
                "namespace": namespace
            },
            confidence=0.7,
            risk_level="low",
            estimated_time="30s",
            rollback_possible=False
        ))

        # Strategy 3: Progressive rollout
        actions.append(ResolutionAction(
            action_type="progressive_rollout",
            description="Deploy with reduced replica count first",
            params={
                "deployment_name": deployment_name,
                "namespace": namespace,
                "initial_replicas": 1
            },
            confidence=0.6,
            risk_level="medium",
            estimated_time="5m",
            rollback_possible=True
        ))

        return sorted(actions, key=lambda x: x.confidence, reverse=True)

    async def execute_resolution(self, action: ResolutionAction) -> tuple[bool, str]:
        """Execute a resolution action and return success status and message."""
        try:
            self.logger.info(f"Executing resolution: {action.action_type}")

            # Check prerequisites
            if action.prerequisites:
                for prereq in action.prerequisites:
                    if not await self._check_prerequisite(prereq, action.params):
                        return False, f"Prerequisite not met: {prereq}"

            # Execute based on action type
            if action.action_type == "restart_pod":
                result = await self.k8s.restart_pod(
                    action.params["pod_name"],
                    action.params["namespace"]
                )
                success = result.get("success", False)
                message = result.get("message", result.get("error", "Unknown error"))

            elif action.action_type == "scale_deployment":
                result = await self.k8s.scale_deployment(
                    action.params["deployment_name"],
                    action.params["namespace"],
                    action.params["replicas"]
                )
                success = result.get("success", False)
                message = result.get("message", result.get("error", "Unknown error"))

            elif action.action_type == "rollback_deployment":
                result = await self.k8s.rollback_deployment(
                    action.params["deployment_name"],
                    action.params["namespace"]
                )
                success = result.get("success", False)
                message = result.get("message", result.get("error", "Unknown error"))

            else:
                # For actions that require manual intervention or additional logic
                success = False
                message = f"Action {action.action_type} requires manual intervention"

            # Log the resolution attempt
            self._log_resolution(action, success, message)

            return success, message

        except Exception as e:
            self.logger.error(f"Error executing resolution: {e}")
            return False, str(e)

    async def _check_prerequisite(self, prereq: str, params: dict[str, Any]) -> bool:
        """Check if a prerequisite is met."""
        if prereq == "managed_by_controller":
            # Check if pod is managed by a deployment/replicaset
            pod_desc = await self.k8s.describe_pod(params["pod_name"], params["namespace"])
            return "Controlled By:" in pod_desc.get("description", "")

        elif prereq == "deployment_exists":
            # Check if it's part of a deployment
            result = await self.k8s.get_deployment_status(params.get("deployment_name", ""), params["namespace"])
            return result.get("success", False)

        elif prereq == "not_statefulset":
            # Ensure it's not a statefulset (different scaling rules)
            pod_desc = await self.k8s.describe_pod(params["pod_name"], params["namespace"])
            return "StatefulSet" not in pod_desc.get("description", "")

        return True

    def _get_restart_count_from_events(self, events: list[dict[str, Any]]) -> int:
        """Extract restart count from pod events."""
        restart_count = 0
        for event in events:
            if "restarted" in event.get("message", "").lower():
                restart_count += event.get("count", 1)
        return restart_count

    def _extract_image_from_events(self, events: list[dict[str, Any]]) -> str | None:
        """Extract image name from pod events."""
        for event in events:
            message = event.get("message", "")
            if "Failed to pull image" in message:
                # Extract image name from message
                parts = message.split('"')
                if len(parts) >= 2:
                    return parts[1]
        return None

    def _log_resolution(self, action: ResolutionAction, success: bool, message: str) -> None:
        """Log a resolution attempt for audit trail."""
        self.resolution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action.action_type,
            "params": action.params,
            "success": success,
            "message": message,
            "confidence": action.confidence,
            "risk_level": action.risk_level
        })

    def get_resolution_history(self) -> list[dict[str, Any]]:
        """Get the history of resolution attempts."""
        return self.resolution_history
