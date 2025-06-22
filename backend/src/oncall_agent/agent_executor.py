"""Agent executor that handles command execution based on AI mode."""

import logging
from datetime import datetime
from typing import Any

from src.oncall_agent.api.schemas import AIMode
from src.oncall_agent.mcp_integrations.kubernetes_mcp import (
    KubernetesMCPServerIntegration,
)
from src.oncall_agent.strategies.kubernetes_resolver import ResolutionAction


class AgentExecutor:
    """Handles execution of remediation actions based on AI mode and risk assessment."""

    def __init__(self, k8s_integration: KubernetesMCPServerIntegration | None = None):
        """Initialize the agent executor."""
        self.logger = logging.getLogger(__name__)
        self.k8s_integration = k8s_integration
        self.execution_history = []
        self.circuit_breaker = CircuitBreaker()

    async def execute_remediation_plan(
        self,
        actions: list[ResolutionAction],
        incident_id: str,
        ai_mode: AIMode,
        confidence_threshold: float = 0.8,
        approval_callback: callable | None = None
    ) -> dict[str, Any]:
        """Execute a remediation plan based on AI mode and confidence.
        
        Args:
            actions: List of resolution actions to execute
            incident_id: ID of the incident being resolved
            ai_mode: Current AI operation mode (YOLO, APPROVAL, PLAN)
            confidence_threshold: Minimum confidence required for auto-execution
            approval_callback: Async function to get approval (for APPROVAL mode)
            
        Returns:
            Execution results with status and details
        """
        results = {
            "incident_id": incident_id,
            "mode": ai_mode.value,
            "actions_proposed": len(actions),
            "actions_executed": 0,
            "actions_successful": 0,
            "actions_failed": 0,
            "execution_details": []
        }

        # Check circuit breaker
        if self.circuit_breaker.is_open():
            self.logger.warning("Circuit breaker is open - too many failures")
            results["error"] = "Circuit breaker open - automatic execution disabled"
            return results

        for action in actions:
            # Prepare execution context
            execution_context = {
                "action": action,
                "incident_id": incident_id,
                "timestamp": datetime.utcnow().isoformat(),
                "mode": ai_mode.value
            }

            try:
                # Determine if we should execute
                should_execute, reason = await self._should_execute_action(
                    action, ai_mode, confidence_threshold, approval_callback
                )

                if should_execute:
                    # Execute the action
                    exec_result = await self._execute_single_action(action, ai_mode)
                    execution_context["executed"] = True
                    execution_context["result"] = exec_result

                    if exec_result["success"]:
                        results["actions_successful"] += 1
                        self.circuit_breaker.record_success()

                        # Verify the action worked
                        if action.action_type in ["restart_pod", "scale_deployment", "rollback_deployment"]:
                            verify_result = await self._verify_action(action)
                            execution_context["verification"] = verify_result
                    else:
                        results["actions_failed"] += 1
                        self.circuit_breaker.record_failure()

                    results["actions_executed"] += 1
                else:
                    execution_context["executed"] = False
                    execution_context["reason"] = reason

            except Exception as e:
                self.logger.error(f"Error executing action {action.action_type}: {e}")
                execution_context["error"] = str(e)
                results["actions_failed"] += 1
                self.circuit_breaker.record_failure()

            results["execution_details"].append(execution_context)
            self.execution_history.append(execution_context)

            # Stop if we've had too many failures
            if results["actions_failed"] >= 3:
                self.logger.warning("Too many failures - stopping execution")
                break

        return results

    async def _should_execute_action(
        self,
        action: ResolutionAction,
        ai_mode: AIMode,
        confidence_threshold: float,
        approval_callback: callable | None
    ) -> tuple[bool, str]:
        """Determine if an action should be executed based on mode and confidence."""

        # Check confidence threshold
        if action.confidence < confidence_threshold:
            return False, f"Confidence {action.confidence} below threshold {confidence_threshold}"

        # Check risk level
        if action.risk_level == "high" and ai_mode != AIMode.YOLO:
            return False, "High risk action requires YOLO mode or manual approval"

        # Mode-specific logic
        if ai_mode == AIMode.YOLO:
            # YOLO mode - execute if confidence is high enough and not forbidden
            if action.confidence >= 0.8 and action.risk_level in ["low", "medium"]:
                return True, "YOLO mode - auto-executing"
            elif action.risk_level == "high" and action.confidence >= 0.9:
                return True, "YOLO mode - high confidence allows high risk"
            else:
                return False, "YOLO mode - insufficient confidence for risk level"

        elif ai_mode == AIMode.APPROVAL:
            # Approval mode - need explicit approval
            if approval_callback:
                approved = await approval_callback(action)
                if approved:
                    return True, "User approved action"
                else:
                    return False, "User rejected action"
            else:
                return False, "Approval required but no callback provided"

        elif ai_mode == AIMode.PLAN:
            # Plan mode - only show what would be done
            return False, "Plan mode - execution disabled"

        return False, f"Unknown mode: {ai_mode}"

    async def _execute_single_action(self, action: ResolutionAction, ai_mode: AIMode) -> dict[str, Any]:
        """Execute a single remediation action."""
        self.logger.info(f"Executing {action.action_type} action (risk: {action.risk_level})")

        if not self.k8s_integration:
            return {"success": False, "error": "No Kubernetes integration available"}

        # Map action types to execution methods
        action_mapping = {
            "restart_pod": self._execute_restart_pod,
            "scale_deployment": self._execute_scale_deployment,
            "rollback_deployment": self._execute_rollback_deployment,
            "increase_memory_limit": self._execute_increase_memory,
            "check_configmaps_secrets": self._execute_check_configs,
            "check_dependencies": self._execute_check_dependencies,
        }

        executor = action_mapping.get(action.action_type)
        if not executor:
            return {"success": False, "error": f"No executor for action type: {action.action_type}"}

        # Execute with appropriate auto-approval based on mode
        auto_approve = ai_mode == AIMode.YOLO
        return await executor(action, auto_approve)

    async def _execute_restart_pod(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Execute pod restart."""
        params = action.params
        result = await self.k8s_integration.execute_action(
            "restart_pod",
            {
                "pod_name": params["pod_name"],
                "namespace": params["namespace"],
                "auto_approve": auto_approve
            }
        )
        return result

    async def _execute_scale_deployment(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Execute deployment scaling."""
        params = action.params
        result = await self.k8s_integration.execute_action(
            "scale_deployment",
            {
                "deployment_name": params["deployment_name"],
                "namespace": params["namespace"],
                "replicas": params["replicas"],
                "auto_approve": auto_approve
            }
        )
        return result

    async def _execute_rollback_deployment(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Execute deployment rollback."""
        params = action.params
        result = await self.k8s_integration.execute_action(
            "rollback_deployment",
            {
                "deployment_name": params["deployment_name"],
                "namespace": params["namespace"],
                "auto_approve": auto_approve
            }
        )
        return result

    async def _execute_increase_memory(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Execute memory limit increase."""
        params = action.params
        # This would need to patch the deployment/pod spec
        deployment_name = params.get("deployment_name")
        if not deployment_name:
            return {"success": False, "error": "No deployment name provided"}

        # Calculate new memory limit
        increase_pct = params.get("memory_increase", "50%")

        # For now, we'll use kubectl patch command
        patch_cmd = [
            "patch", "deployment", deployment_name,
            "-n", params["namespace"],
            "--type", "json",
            "-p", '[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "512Mi"}]'
        ]

        result = await self.k8s_integration.execute_kubectl_command(
            patch_cmd,
            auto_approve=auto_approve
        )
        return result

    async def _execute_check_configs(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Check ConfigMaps and Secrets."""
        params = action.params
        namespace = params["namespace"]

        # Get configmaps
        cm_result = await self.k8s_integration.execute_kubectl_command(
            ["get", "configmaps", "-n", namespace, "-o", "json"],
            auto_approve=True  # Read-only operation
        )

        # Get secrets
        secret_result = await self.k8s_integration.execute_kubectl_command(
            ["get", "secrets", "-n", namespace, "-o", "json"],
            auto_approve=True  # Read-only operation
        )

        return {
            "success": cm_result["success"] and secret_result["success"],
            "configmaps": cm_result.get("output", ""),
            "secrets": secret_result.get("output", "")
        }

    async def _execute_check_dependencies(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Check service dependencies."""
        params = action.params
        namespace = params["namespace"]

        # Get services in namespace
        svc_result = await self.k8s_integration.execute_kubectl_command(
            ["get", "services", "-n", namespace, "-o", "json"],
            auto_approve=True  # Read-only operation
        )

        # Get endpoints
        ep_result = await self.k8s_integration.execute_kubectl_command(
            ["get", "endpoints", "-n", namespace, "-o", "json"],
            auto_approve=True  # Read-only operation
        )

        return {
            "success": svc_result["success"] and ep_result["success"],
            "services": svc_result.get("output", ""),
            "endpoints": ep_result.get("output", "")
        }

    async def _verify_action(self, action: ResolutionAction) -> dict[str, Any]:
        """Verify that an action was successful."""
        if not self.k8s_integration:
            return {"verified": False, "reason": "No Kubernetes integration"}

        return await self.k8s_integration.verify_action_success(
            action.action_type,
            action.params
        )

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get the history of executed actions."""
        return self.execution_history


class CircuitBreaker:
    """Simple circuit breaker to prevent repeated failures."""

    def __init__(self, failure_threshold: int = 5, success_threshold: int = 2, timeout: int = 300):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            success_threshold: Number of successes needed to close
            timeout: Seconds before attempting to close after opening
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state == "closed":
            return False

        if self.state == "open":
            # Check if we should move to half-open
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = "half-open"
                    return False
            return True

        return False  # half-open allows attempts

    def record_success(self):
        """Record a successful execution."""
        if self.state == "half-open":
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = "closed"
                self.failure_count = 0
                self.success_count = 0
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.success_count = 0
