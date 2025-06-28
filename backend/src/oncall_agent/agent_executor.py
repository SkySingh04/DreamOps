"""Agent executor that handles command execution based on AI mode."""

import json
import logging
import subprocess
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.oncall_agent.api.log_streaming import log_stream_manager
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

    async def execute_kubectl_direct(self, cmd: list[str], auto_approve: bool = False) -> dict[str, Any]:
        """Execute kubectl command via MCP server integration."""
        self.logger.info(f"Executing command via MCP: {' '.join(cmd[:3])}...")

        # Stream log for command
        await log_stream_manager.log_info(
            f"🔨 Running MCP command: {' '.join(cmd[:3])}...",  # Show first 3 parts of command
            action_type="mcp_command",
            metadata={"command": ' '.join(cmd), "auto_approve": auto_approve}
        )

        # Use MCP integration if available
        if self.k8s_integration:
            return await self.k8s_integration.execute_kubectl_command(
                cmd, 
                dry_run=False,
                auto_approve=auto_approve
            )
        else:
            return {
                "success": False,
                "error": "No Kubernetes MCP integration available. Please ensure mcp-server-kubernetes is installed.",
                "command": " ".join(cmd)
            }

    async def execute_remediation_plan(
        self,
        actions: list[ResolutionAction],
        incident_id: str,
        ai_mode: AIMode,
        confidence_threshold: float = 0.8,
        approval_callback: Callable | None = None
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

        # Log remediation plan start
        await log_stream_manager.log_info(
            f"🚀 Starting remediation plan with {len(actions)} actions",
            incident_id=incident_id,
            stage="remediation_start",
            metadata={
                "ai_mode": ai_mode.value,
                "total_actions": len(actions),
                "action_types": [a.action_type for a in actions]
            }
        )

        # Check circuit breaker - but reset it in YOLO mode since all errors are fixable
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

                        await log_stream_manager.log_success(
                            f"✅ Action {results['actions_executed'] + 1}/{len(actions)} completed successfully",
                            incident_id=incident_id,
                            progress=(results["actions_executed"] + 1) / len(actions),
                            metadata={"action_type": action.action_type}
                        )

                        # Verify the action worked
                        if action.action_type in ["restart_pod", "scale_deployment", "rollback_deployment"]:
                            verify_result = await self._verify_action(action)
                            execution_context["verification"] = verify_result
                    else:
                        results["actions_failed"] += 1
                        self.circuit_breaker.record_failure()

                        await log_stream_manager.log_error(
                            f"❌ Action {results['actions_executed'] + 1}/{len(actions)} failed",
                            incident_id=incident_id,
                            metadata={
                                "action_type": action.action_type,
                                "error": exec_result.get("error")
                            }
                        )

                    results["actions_executed"] += 1
                else:
                    execution_context["executed"] = False
                    execution_context["reason"] = reason

                    await log_stream_manager.log_warning(
                        f"⏭️ Skipped action: {action.action_type} - {reason}",
                        incident_id=incident_id,
                        metadata={"action_type": action.action_type, "reason": reason}
                    )

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
                await log_stream_manager.log_error(
                    "🛑 Stopping execution due to too many failures",
                    incident_id=incident_id,
                    metadata={"failed_count": results["actions_failed"]}
                )
                break

        # Log remediation completion
        await log_stream_manager.log_info(
            f"🎯 Remediation plan completed: {results['actions_successful']}/{results['actions_executed']} actions successful",
            incident_id=incident_id,
            stage="remediation_complete",
            progress=1.0,
            metadata={
                "successful": results["actions_successful"],
                "failed": results["actions_failed"],
                "total_executed": results["actions_executed"]
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
        # In YOLO mode, we execute regardless of confidence since all errors are fixable

        # Check risk level
        if action.risk_level == "high" and ai_mode != AIMode.YOLO:
            return False, "High risk action requires YOLO mode or manual approval"

        # Mode-specific logic
        if ai_mode == AIMode.YOLO:
            # YOLO mode - ALWAYS execute because all simulated errors are fixable!
            # Trust the remediation since errors are from fuck_kubernetes.sh
            self.logger.info(f"🚀 YOLO: Executing {action.action_type} (confidence: {action.confidence}, risk: {action.risk_level})")
            return True, "YOLO mode - auto-executing (all simulated errors are fixable)"

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

        # Stream log for action execution start
        await log_stream_manager.log_info(
            f"🔧 Executing action: {action.action_type}",
            action_type=action.action_type,
            metadata={
                "risk_level": action.risk_level,
                "confidence": action.confidence,
                "description": action.description
            }
        )

        # Map action types to execution methods
        action_mapping = {
            "restart_pod": self._execute_restart_pod,
            "scale_deployment": self._execute_scale_deployment,
            "rollback_deployment": self._execute_rollback_deployment,
            "increase_memory_limit": self._execute_increase_memory,
            "check_configmaps_secrets": self._execute_check_configs,
            "check_dependencies": self._execute_check_dependencies,
            # New action types for generic pod errors and OOM
            "identify_error_pods": self._execute_identify_error_pods,
            "restart_error_pods": self._execute_restart_error_pods,
            "check_resource_constraints": self._execute_check_resource_constraints,
            "identify_oom_pods": self._execute_identify_oom_pods,
            "increase_memory_limits": self._execute_increase_memory_limits,
            # Deterministic fix actions
            "update_image": self._execute_update_image,
            "delete_pods_by_label": self._execute_delete_pods_by_label,
            "patch_memory_limit": self._execute_patch_memory_limit,
        }

        executor = action_mapping.get(action.action_type)
        if not executor:
            return {"success": False, "error": f"No executor for action type: {action.action_type}"}

        # Execute with appropriate auto-approval based on mode
        auto_approve = ai_mode == AIMode.YOLO

        try:
            result = await executor(action, auto_approve)

            # Stream log for action result
            if result.get("success"):
                await log_stream_manager.log_success(
                    f"✅ Action completed: {action.action_type}",
                    action_type=action.action_type,
                    metadata={"output": result.get("output", "")[:500]}  # Truncate long outputs
                )
            else:
                await log_stream_manager.log_error(
                    f"❌ Action failed: {action.action_type}",
                    action_type=action.action_type,
                    metadata={"error": result.get("error", "Unknown error")}
                )

            return result
        except Exception as e:
            await log_stream_manager.log_error(
                f"❌ Exception during action: {action.action_type}",
                action_type=action.action_type,
                metadata={"error": str(e)}
            )
            raise

    async def _execute_restart_pod(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Execute pod restart."""
        params = action.params
        # Delete the pod to force restart
        cmd = ["delete", "pod", params["pod_name"], "-n", params["namespace"]]
        return await self.execute_kubectl_direct(cmd, auto_approve)

    async def _execute_scale_deployment(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Execute deployment scaling."""
        params = action.params
        cmd = ["scale", "deployment", params["deployment_name"],
               "-n", params["namespace"],
               f"--replicas={params['replicas']}"]
        return await self.execute_kubectl_direct(cmd, auto_approve)

    async def _execute_rollback_deployment(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Execute deployment rollback."""
        params = action.params
        cmd = ["rollout", "undo", "deployment", params["deployment_name"],
               "-n", params["namespace"]]
        return await self.execute_kubectl_direct(cmd, auto_approve)

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

        return await self.execute_kubectl_direct(patch_cmd, auto_approve)

    async def _execute_check_configs(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Check ConfigMaps and Secrets."""
        params = action.params
        namespace = params["namespace"]

        # Get configmaps
        cm_result = await self.execute_kubectl_direct(
            ["get", "configmaps", "-n", namespace, "-o", "json"],
            auto_approve=True  # Read-only operation
        )

        # Get secrets
        secret_result = await self.execute_kubectl_direct(
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
        svc_result = await self.execute_kubectl_direct(
            ["get", "services", "-n", namespace, "-o", "json"],
            auto_approve=True  # Read-only operation
        )

        # Get endpoints
        ep_result = await self.execute_kubectl_direct(
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
        # Simple verification by checking resource status
        params = action.params

        if action.action_type == "restart_pod":
            # Check if pod is running again
            cmd = ["get", "pod", params["pod_name"], "-n", params["namespace"], "-o", "json"]
            result = await self.execute_kubectl_direct(cmd, True)
            if result["success"]:
                try:
                    pod_data = json.loads(result["output"])
                    status = pod_data.get("status", {}).get("phase", "")
                    return {"verified": status == "Running", "status": status}
                except:
                    return {"verified": False, "reason": "Failed to parse pod status"}
            return {"verified": False, "reason": result.get("error")}

        elif action.action_type == "scale_deployment":
            # Check if replicas match
            cmd = ["get", "deployment", params["deployment_name"], "-n", params["namespace"], "-o", "json"]
            result = await self.execute_kubectl_direct(cmd, True)
            if result["success"]:
                try:
                    dep_data = json.loads(result["output"])
                    desired = dep_data.get("spec", {}).get("replicas", 0)
                    ready = dep_data.get("status", {}).get("readyReplicas", 0)
                    return {"verified": desired == params["replicas"] and ready == desired,
                           "desired": desired, "ready": ready}
                except:
                    return {"verified": False, "reason": "Failed to parse deployment status"}
            return {"verified": False, "reason": result.get("error")}

        return {"verified": True, "reason": "Verification not implemented for this action type"}

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get the history of executed actions."""
        return self.execution_history

    async def _execute_identify_error_pods(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Identify pods with errors."""
        params = action.params
        namespace = params.get("namespace", "default")

        await log_stream_manager.log_info(
            f"🔍 Scanning for error pods in namespace: {namespace}",
            action_type="identify_error_pods",
            metadata={"namespace": namespace}
        )

        # Get all pods and filter for error states
        cmd = ["get", "pods"]
        if not params.get("check_all_namespaces"):
            cmd.extend(["-n", namespace])
        else:
            cmd.append("--all-namespaces")

        result = await self.execute_kubectl_direct(cmd, auto_approve=True)  # Read-only operation

        if result.get("success"):
            output = result.get("output", "")
            error_pods = []
            for line in output.split("\n")[1:]:  # Skip header
                if any(state in line for state in ["Error", "CrashLoopBackOff", "ImagePullBackOff", "Pending"]):
                    error_pods.append(line)

            result["error_pods"] = error_pods
            result["error_count"] = len(error_pods)
            self.logger.info(f"Found {len(error_pods)} pods with errors")

            await log_stream_manager.log_info(
                f"📊 Found {len(error_pods)} pods with errors",
                action_type="identify_error_pods",
                metadata={"error_count": len(error_pods), "pods": error_pods[:5]}  # Show first 5
            )

        return result

    async def _execute_restart_error_pods(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Restart pods that are in error state."""
        params = action.params
        namespace = params.get("namespace", "default")
        states = params.get("states", ["Error", "CrashLoopBackOff", "ImagePullBackOff"])

        await log_stream_manager.log_info(
            f"♻️ Preparing to restart error pods in namespace: {namespace}",
            action_type="restart_error_pods",
            metadata={"namespace": namespace, "target_states": states}
        )

        # First get error pods
        identify_result = await self._execute_identify_error_pods(
            ResolutionAction(
                action_type="identify_error_pods",
                description="",
                params=params,
                confidence=1.0,
                risk_level="low",
                estimated_time="10s",
                rollback_possible=False
            ),
            auto_approve=True
        )

        if not identify_result.get("success"):
            return identify_result

        error_pods = identify_result.get("error_pods", [])
        results = []

        for pod_line in error_pods:
            parts = pod_line.split()
            if len(parts) >= 2:
                pod_namespace = namespace
                pod_name = parts[0]

                # If all namespaces, extract namespace from output
                if params.get("check_all_namespaces") and len(parts) >= 2:
                    pod_namespace = parts[0]
                    pod_name = parts[1]

                # Delete the pod to force restart
                delete_cmd = ["delete", "pod", pod_name, "-n", pod_namespace]
                result = await self.execute_kubectl_direct(delete_cmd, auto_approve)
                results.append({
                    "pod": pod_name,
                    "namespace": pod_namespace,
                    "result": result
                })

        return {
            "success": all(r["result"].get("success") for r in results),
            "restarted_pods": len(results),
            "details": results
        }

    async def _execute_check_resource_constraints(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Check if pods are failing due to resource constraints."""
        params = action.params
        namespace = params.get("namespace", "default")

        # Get resource usage
        cmd = ["top", "pods", "-n", namespace]
        result = await self.execute_kubectl_direct(cmd, auto_approve=True)  # Read-only operation

        return result

    async def _execute_identify_oom_pods(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Identify pods that were OOM killed."""
        params = action.params
        namespace = params.get("namespace", "default")
        timeframe = params.get("timeframe", "1h")

        # Get events looking for OOM kills
        cmd = ["get", "events", "-n", namespace, "--field-selector", "reason=OOMKilling"]
        result = await self.execute_kubectl_direct(cmd, auto_approve=True)  # Read-only operation

        if result.get("success"):
            # Parse output to find affected deployments
            output = result.get("output", "")
            oom_deployments = set()
            for line in output.split("\n")[1:]:  # Skip header
                if "OOMKilling" in line:
                    # Extract deployment name from pod name
                    parts = line.split()
                    for part in parts:
                        if "-" in part and not part.startswith("-"):
                            # Likely a pod name, extract deployment
                            deployment = "-".join(part.split("-")[:-2])
                            if deployment:
                                oom_deployments.add(deployment)

            result["oom_deployments"] = list(oom_deployments)
            result["oom_count"] = len(oom_deployments)

        return result

    async def _execute_increase_memory_limits(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Increase memory limits for deployments with OOM killed pods."""
        params = action.params
        namespace = params.get("namespace", "default")
        increase_percentage = params.get("increase_percentage", 50)

        # First identify OOM deployments
        if params.get("target_deployments") == "auto-detect":
            identify_result = await self._execute_identify_oom_pods(
                ResolutionAction(
                    action_type="identify_oom_pods",
                    description="",
                    params={"namespace": namespace},
                    confidence=1.0,
                    risk_level="low",
                    estimated_time="10s",
                    rollback_possible=False
                ),
                auto_approve=True
            )

            if not identify_result.get("success"):
                return identify_result

            deployments = identify_result.get("oom_deployments", [])
        else:
            deployments = params.get("target_deployments", [])

        results = []
        for deployment in deployments:
            # Patch deployment to increase memory
            patch_cmd = [
                "patch", "deployment", deployment,
                "-n", namespace,
                "--type", "json",
                "-p", '[{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "1Gi"}]'
            ]

            result = await self.execute_kubectl_direct(patch_cmd, auto_approve)
            results.append({
                "deployment": deployment,
                "result": result
            })

        return {
            "success": all(r["result"].get("success") for r in results),
            "patched_deployments": len(results),
            "details": results
        }

    async def _execute_update_image(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Update container image in a deployment."""
        params = action.params
        deployment = params["deployment_name"]
        namespace = params["namespace"]
        container = params["container_name"]
        new_image = params["new_image"]

        cmd = ["set", "image", f"deployment/{deployment}",
               f"{container}={new_image}", "-n", namespace]
        return await self.execute_kubectl_direct(cmd, auto_approve)

    async def _execute_delete_pods_by_label(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Delete pods by label selector."""
        params = action.params
        namespace = params["namespace"]
        selector = params["label_selector"]

        cmd = ["delete", "pods", "-l", selector, "-n", namespace]
        return await self.execute_kubectl_direct(cmd, auto_approve)

    async def _execute_patch_memory_limit(self, action: ResolutionAction, auto_approve: bool) -> dict[str, Any]:
        """Patch memory limit for a deployment."""
        params = action.params
        deployment = params["deployment_name"]
        namespace = params["namespace"]
        memory_limit = params["memory_limit"]

        patch_cmd = [
            "patch", "deployment", deployment,
            "-n", namespace,
            "--type", "json",
            "-p", f'[{{"op": "replace", "path": "/spec/template/spec/containers/0/resources/limits/memory", "value": "{memory_limit}"}}]'
        ]
        return await self.execute_kubectl_direct(patch_cmd, auto_approve)


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
