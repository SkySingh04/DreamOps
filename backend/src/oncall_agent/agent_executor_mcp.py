"""Agent executor that uses MCP server exclusively for Kubernetes operations."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.oncall_agent.api.log_streaming import log_stream_manager
from src.oncall_agent.api.schemas import AIMode
from src.oncall_agent.mcp_integrations.kubernetes_manusa_mcp import (
    KubernetesManusaMCPIntegration,
)
from src.oncall_agent.strategies.kubernetes_resolver import ResolutionAction


class AgentExecutorMCP:
    """Handles execution of remediation actions using MCP server exclusively."""

    def __init__(self, k8s_integration: KubernetesManusaMCPIntegration | None = None):
        """Initialize the agent executor with MCP-only integration."""
        self.logger = logging.getLogger(__name__)
        self.k8s_integration = k8s_integration
        self.execution_history = []
        self.circuit_breaker = CircuitBreaker()

    async def execute_mcp_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an action via MCP server."""
        if not self.k8s_integration:
            return {
                "success": False,
                "error": "Kubernetes MCP integration not initialized"
            }

        self.logger.info(f"Executing MCP action: {action} with params: {params}")

        # Stream log for MCP action
        await log_stream_manager.log_info(
            f"🔨 Running MCP action: {action}",
            action_type="mcp_action",
            metadata={"action": action, "params": params}
        )

        try:
            result = await self.k8s_integration.execute_action(action, params)

            if result.get("success"):
                await log_stream_manager.log_success(
                    f"✅ MCP action completed: {action}",
                    action_type="mcp_action",
                    metadata={"result": result}
                )
            else:
                await log_stream_manager.log_error(
                    f"❌ MCP action failed: {action}",
                    action_type="mcp_action",
                    metadata={"error": result.get("error")}
                )

            return result

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"MCP action failed: {error_msg}")
            await log_stream_manager.log_error(
                f"❌ MCP action exception: {action}",
                action_type="mcp_action",
                metadata={"error": error_msg}
            )
            return {
                "success": False,
                "error": error_msg,
                "action": action
            }

    async def execute_remediation_plan(
        self,
        actions: list[ResolutionAction],
        incident_id: str,
        ai_mode: AIMode,
        confidence_threshold: float = 0.8,
        approval_callback: Callable | None = None
    ) -> dict[str, Any]:
        """Execute a remediation plan using MCP server exclusively.
        
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

        # Log remediation plan start
        await log_stream_manager.log_info(
            f"🚀 Starting MCP-based remediation plan with {len(actions)} actions",
            incident_id=incident_id,
            stage="remediation_start",
            metadata={
                "ai_mode": ai_mode.value,
                "total_actions": len(actions),
                "action_types": [a.action_type for a in actions],
                "mcp_enabled": True
            }
        )

        # Check circuit breaker - but reset it in YOLO mode
        if self.circuit_breaker.is_open():
            if ai_mode == AIMode.YOLO:
                self.logger.warning("Circuit breaker is open but resetting for YOLO mode")
                self.circuit_breaker.reset()
            else:
                self.logger.warning("Circuit breaker is open - too many failures")
                results["error"] = "Circuit breaker open - automatic execution disabled"
                return results

        for action in actions:
            # Prepare execution context
            execution_context = {
                "action": {
                    "action_type": action.action_type,
                    "description": action.description,
                    "params": action.params,
                    "confidence": action.confidence,
                    "risk_level": action.risk_level,
                    "estimated_time": action.estimated_time,
                    "rollback_possible": action.rollback_possible
                },
                "incident_id": incident_id,
                "timestamp": datetime.utcnow().isoformat(),
                "mode": ai_mode.value,
                "mcp_execution": True
            }

            try:
                # Determine if we should execute
                should_execute, reason = await self._should_execute_action(
                    action, ai_mode, confidence_threshold, approval_callback
                )

                if should_execute:
                    # Execute the action via MCP
                    exec_result = await self._execute_single_action(action, ai_mode)
                    execution_context["executed"] = True
                    execution_context["result"] = exec_result

                    if exec_result["success"]:
                        results["actions_successful"] += 1
                        self.circuit_breaker.record_success()

                        await log_stream_manager.log_success(
                            f"✅ MCP Action {results['actions_executed'] + 1}/{len(actions)} completed successfully",
                            incident_id=incident_id,
                            progress=(results["actions_executed"] + 1) / len(actions),
                            metadata={"action_type": action.action_type, "mcp": True}
                        )

                        # Verify the action worked
                        if action.action_type in ["restart_pod", "scale_deployment", "rollback_deployment"]:
                            verify_result = await self._verify_action(action)
                            execution_context["verification"] = verify_result
                    else:
                        results["actions_failed"] += 1
                        self.circuit_breaker.record_failure()

                        await log_stream_manager.log_error(
                            f"❌ MCP Action {results['actions_executed'] + 1}/{len(actions)} failed",
                            incident_id=incident_id,
                            metadata={
                                "action_type": action.action_type,
                                "error": exec_result.get("error"),
                                "mcp": True
                            }
                        )

                    results["actions_executed"] += 1
                else:
                    execution_context["executed"] = False
                    execution_context["reason"] = reason

                    await log_stream_manager.log_warning(
                        f"⏭️ Skipped MCP action: {action.action_type} - {reason}",
                        incident_id=incident_id,
                        metadata={"action_type": action.action_type, "reason": reason}
                    )

            except Exception as e:
                self.logger.error(f"Error executing MCP action {action.action_type}: {e}")
                execution_context["error"] = str(e)
                results["actions_failed"] += 1
                self.circuit_breaker.record_failure()

            results["execution_details"].append(execution_context)
            self.execution_history.append(execution_context)

            # Stop if we've had too many failures
            if results["actions_failed"] >= 3:
                self.logger.warning("Too many failures - stopping execution")
                await log_stream_manager.log_error(
                    "🛑 Stopping MCP execution due to too many failures",
                    incident_id=incident_id,
                    metadata={"failed_count": results["actions_failed"]}
                )
                break

        # Log remediation completion
        await log_stream_manager.log_info(
            f"🎯 MCP remediation plan completed: {results['actions_successful']}/{results['actions_executed']} actions successful",
            incident_id=incident_id,
            stage="remediation_complete",
            progress=1.0,
            metadata={
                "successful": results["actions_successful"],
                "failed": results["actions_failed"],
                "total_executed": results["actions_executed"],
                "mcp_enabled": True
            }
        )

        return results

    async def _should_execute_action(
        self,
        action: ResolutionAction,
        ai_mode: AIMode,
        confidence_threshold: float,
        approval_callback: Callable | None
    ) -> tuple[bool, str]:
        """Determine if an action should be executed based on mode and confidence."""

        # Check confidence threshold
        if ai_mode != AIMode.YOLO and action.confidence < confidence_threshold:
            return False, f"Confidence {action.confidence} below threshold {confidence_threshold}"

        # Check risk level
        if action.risk_level == "high" and ai_mode != AIMode.YOLO:
            return False, "High risk action requires YOLO mode or manual approval"

        # Mode-specific logic
        if ai_mode == AIMode.YOLO:
            self.logger.info(f"🚀 YOLO: Executing {action.action_type} via MCP (confidence: {action.confidence}, risk: {action.risk_level})")
            return True, "YOLO mode - auto-executing via MCP"

        elif ai_mode == AIMode.APPROVAL:
            if approval_callback:
                approved = await approval_callback(action)
                if approved:
                    return True, "User approved MCP action"
                else:
                    return False, "User rejected MCP action"
            else:
                return False, "Approval required but no callback provided"

        elif ai_mode == AIMode.PLAN:
            return False, "Plan mode - MCP execution disabled"

        return False, f"Unknown mode: {ai_mode}"

    async def _execute_single_action(self, action: ResolutionAction, ai_mode: AIMode) -> dict[str, Any]:
        """Execute a single remediation action via MCP server."""
        self.logger.info(f"Executing {action.action_type} action via MCP (risk: {action.risk_level})")

        # Stream log for action execution start
        await log_stream_manager.log_info(
            f"🔧 Executing MCP action: {action.action_type}",
            action_type=action.action_type,
            metadata={
                "risk_level": action.risk_level,
                "confidence": action.confidence,
                "description": action.description,
                "mcp": True
            }
        )

        # Map action types to MCP actions
        action_mapping = {
            "restart_pod": "restart_pod",
            "scale_deployment": "scale_deployment",
            "rollback_deployment": "rollback_deployment",
            "increase_memory_limit": "patch_resource",
            "check_configmaps_secrets": "fetch_context",
            "check_dependencies": "fetch_context",
            "identify_error_pods": "fetch_context",
            "restart_error_pods": "restart_pod",
            "check_resource_constraints": "fetch_context",
            "identify_oom_pods": "fetch_context",
            "increase_memory_limits": "patch_resource",
            "update_image": "patch_resource",
            "delete_pods_by_label": "delete_resource",
            "patch_memory_limit": "patch_resource",
        }

        mcp_action = action_mapping.get(action.action_type)
        if not mcp_action:
            return {"success": False, "error": f"No MCP mapping for action type: {action.action_type}"}

        # Prepare parameters for specific action types
        params = self._prepare_mcp_params(action)

        try:
            result = await self.execute_mcp_action(mcp_action, params)
            result["original_action"] = action.action_type
            return result
        except Exception as e:
            await log_stream_manager.log_error(
                f"❌ MCP exception during action: {action.action_type}",
                action_type=action.action_type,
                metadata={"error": str(e), "mcp": True}
            )
            raise

    def _prepare_mcp_params(self, action: ResolutionAction) -> dict[str, Any]:
        """Prepare parameters for MCP action based on action type."""
        params = action.params.copy()

        # Special handling for different action types
        if action.action_type == "check_configmaps_secrets":
            params["type"] = "configmaps_secrets"
        elif action.action_type == "check_dependencies":
            params["type"] = "services"
        elif action.action_type == "identify_error_pods":
            params["type"] = "pods"
            params["filter"] = "error_states"
        elif action.action_type == "check_resource_constraints":
            params["type"] = "metrics"
        elif action.action_type == "identify_oom_pods":
            params["type"] = "events"
            params["filter"] = "oom_kills"
        elif action.action_type == "increase_memory_limit":
            # Convert to patch parameters
            params["kind"] = "deployment"
            params["name"] = params.get("deployment_name")
            params["patch"] = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": params.get("container_name", "main"),
                                "resources": {
                                    "limits": {
                                        "memory": params.get("memory_limit", "1Gi")
                                    }
                                }
                            }]
                        }
                    }
                }
            }
            params["patch_type"] = "strategic"
        elif action.action_type == "update_image":
            params["kind"] = "deployment"
            params["name"] = params.get("deployment_name")
            params["patch"] = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": params.get("container_name"),
                                "image": params.get("new_image")
                            }]
                        }
                    }
                }
            }
            params["patch_type"] = "strategic"
        elif action.action_type == "delete_pods_by_label":
            params["kind"] = "pod"

        return params

    async def _verify_action(self, action: ResolutionAction) -> dict[str, Any]:
        """Verify that an action was successful via MCP."""
        params = action.params

        if action.action_type == "restart_pod":
            # Check if pod is running again
            result = await self.k8s_integration.fetch_context({
                "type": "pods",
                "namespace": params.get("namespace", "default"),
                "name": params.get("pod_name")
            })

            if result and not result.get("error"):
                pods = result.get("items", [])
                if pods and len(pods) > 0:
                    status = pods[0].get("status", {}).get("phase", "")
                    return {"verified": status == "Running", "status": status}

            return {"verified": False, "reason": "Pod not found or error fetching status"}

        elif action.action_type == "scale_deployment":
            # Check if replicas match
            result = await self.k8s_integration.fetch_context({
                "type": "deployments",
                "namespace": params.get("namespace", "default"),
                "name": params.get("deployment_name")
            })

            if result and not result.get("error"):
                deployments = result.get("items", [])
                if deployments and len(deployments) > 0:
                    spec = deployments[0].get("spec", {})
                    status = deployments[0].get("status", {})
                    desired = spec.get("replicas", 0)
                    ready = status.get("readyReplicas", 0)
                    return {
                        "verified": desired == params["replicas"] and ready == desired,
                        "desired": desired,
                        "ready": ready
                    }

            return {"verified": False, "reason": "Deployment not found or error fetching status"}

        return {"verified": True, "reason": "Verification not implemented for this action type"}

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get the history of executed actions."""
        return self.execution_history


class CircuitBreaker:
    """Simple circuit breaker to prevent repeated failures."""

    def __init__(self, failure_threshold: int = 5, success_threshold: int = 2, timeout: int = 300):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"

    def reset(self):
        """Reset the circuit breaker to closed state."""
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = "closed"

    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        if self.state == "closed":
            return False

        if self.state == "open":
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout:
                    self.state = "half-open"
                    return False
            return True

        return False

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
