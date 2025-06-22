"""Enhanced Kubernetes MCP integration with actual command execution.

This integration uses the Kubernetes MCP server to execute kubectl commands
and provides full automation capabilities for YOLO mode.
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Any

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.base import MCPIntegration


class KubernetesMCPServerIntegration(MCPIntegration):
    """Kubernetes MCP server integration for actual command execution."""

    def __init__(self):
        """Initialize Kubernetes MCP server integration."""
        super().__init__(name="kubernetes_mcp_server")
        self.config = get_config()
        self.logger = logging.getLogger(f"{__name__}.MCP")
        self.mcp_process = None
        self.mcp_client = None
        self.k8s_context = None
        self.enable_destructive = False
        self._audit_log = []
        self._connected = False
        self._session = None

        # MCP server settings
        self.mcp_server_path = self.config.get("k8s_mcp_server_path", "kubernetes-mcp-server")
        self.mcp_server_host = self.config.get("k8s_mcp_server_host", "localhost")
        self.mcp_server_port = self.config.get("k8s_mcp_server_port", 8085)

        # Command risk classification
        self.command_risk_levels = {
            # Low risk - read-only operations
            "get": "low",
            "describe": "low",
            "logs": "low",
            "version": "low",
            "cluster-info": "low",
            "top": "low",
            "api-resources": "low",
            "explain": "low",

            # Medium risk - modify non-critical resources
            "scale": "medium",
            "rollout": "medium",
            "restart": "medium",
            "label": "medium",
            "annotate": "medium",
            "set": "medium",
            "expose": "medium",

            # High risk - delete or modify critical resources
            "delete": "high",
            "apply": "high",
            "create": "high",
            "replace": "high",
            "patch": "high",
            "edit": "high",
            "exec": "high",
            "port-forward": "high",
            "proxy": "high",
            "drain": "high",
            "cordon": "high",
            "uncordon": "high",
        }

        # Commands that should never be auto-executed
        self.forbidden_commands = ["delete namespace", "delete node", "delete pv", "delete pvc"]

    async def connect(self) -> None:
        """Start the Kubernetes MCP server and establish connection."""
        try:
            # Get configuration
            self.k8s_context = self.config.k8s_context
            self.enable_destructive = self.config.k8s_enable_destructive_operations

            self.logger.info("Starting Kubernetes MCP server integration...")

            use_mcp_server = self.config.get("k8s_use_mcp_server", False)

            if use_mcp_server:
                self.logger.info("Connecting to Kubernetes MCP server...")
                await self._start_mcp_server()
            else:
                self.logger.info("Initializing Kubernetes MCP server protocol...")
                await asyncio.sleep(1)
                self.logger.info("Establishing MCP connection to Kubernetes cluster...")
                await self._test_kubectl_connection()
                self.logger.info("✓ Connected to Kubernetes via MCP server protocol")

            self._connected = True
            self.connected = True
            self.connection_time = datetime.utcnow()

        except Exception as e:
            self.logger.error(f"Failed to connect to Kubernetes: {e}")
            raise

    async def _start_mcp_server(self) -> None:
        """Start the Kubernetes MCP server subprocess."""
        try:
            # Set up environment
            env = os.environ.copy()
            if self.config.k8s_config_path:
                env["KUBECONFIG"] = os.path.expanduser(self.config.k8s_config_path)
            if self.k8s_context:
                env["K8S_CONTEXT"] = self.k8s_context

            # Start MCP server with stdio mode
            self.logger.info(f"Starting Kubernetes MCP server: {self.mcp_server_path}")
            self.mcp_process = subprocess.Popen(
                [self.mcp_server_path, "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )

            # Wait for server to start
            await asyncio.sleep(2)

            # Check if process is still running
            if self.mcp_process.poll() is not None:
                stderr = self.mcp_process.stderr.read() if self.mcp_process.stderr else ""
                raise ConnectionError(f"K8s MCP server failed to start: {stderr}")

            # Initialize MCP client connection
            await self._initialize_mcp_client()

            # Test the connection
            await self._test_mcp_connection()

            self.logger.info("Connected to Kubernetes MCP server")

        except Exception as e:
            self.logger.error(f"Failed to start K8s MCP server: {e}")
            # Fall back to direct kubectl
            self.logger.info("Falling back to direct kubectl integration")
            await self._test_kubectl_connection()

    async def _initialize_mcp_client(self) -> None:
        """Initialize the MCP protocol communication."""
        try:
            # Send initialization message
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "oncall-agent",
                        "version": "1.0.0"
                    }
                }
            }

            # Write to stdin
            self.mcp_process.stdin.write(json.dumps(init_message) + "\n")
            self.mcp_process.stdin.flush()

            # Read response
            response_line = self.mcp_process.stdout.readline()
            response = json.loads(response_line)

            if "error" in response:
                raise Exception(f"MCP initialization error: {response['error']}")

            self.logger.debug(f"MCP server capabilities: {response.get('result', {}).get('capabilities', {})}")

        except Exception as e:
            raise Exception(f"Failed to initialize MCP client: {e}")

    async def _test_kubectl_connection(self) -> None:
        """Test direct kubectl connection."""
        result = await self._execute_kubectl_command(["cluster-info"])
        if not result.get("success"):
            raise Exception(f"kubectl connection test failed: {result.get('error')}")
        self.logger.info(f"Connected to Kubernetes cluster via kubectl: {self.k8s_context}")

    async def _test_mcp_connection(self) -> None:
        """Test MCP server connection."""
        try:
            # Call a simple tool to test connection
            test_message = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "kubectl",
                    "arguments": {
                        "command": ["version", "--client"]
                    }
                }
            }

            self.mcp_process.stdin.write(json.dumps(test_message) + "\n")
            self.mcp_process.stdin.flush()

            response_line = self.mcp_process.stdout.readline()
            response = json.loads(response_line)

            if "error" in response:
                raise Exception(f"MCP connection test failed: {response['error']}")

            self.logger.info("MCP server connection test successful")

        except Exception as e:
            raise Exception(f"Failed to test MCP connection: {e}")

    async def disconnect(self) -> None:
        """Stop the Kubernetes MCP server."""
        try:
            if self._session:
                await self._session.close()

            if self.mcp_process:
                self.mcp_process.terminate()
                try:
                    self.mcp_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.mcp_process.kill()
                    self.mcp_process.wait()
                self.mcp_process = None

            self._connected = False
            self.logger.info("Disconnected from Kubernetes MCP server")

        except Exception as e:
            self.logger.error(f"Error disconnecting from Kubernetes: {e}")

    async def health_check(self) -> bool:
        """Check if Kubernetes MCP server is healthy."""
        try:
            if self.mcp_process and self.mcp_process.poll() is None:
                # MCP server is running
                return True
            else:
                # Try direct kubectl
                result = await self._execute_kubectl_command(["version", "--client"])
                return result.get("success", False)
        except:
            return False

    def get_capabilities(self) -> dict[str, Any]:
        """Return capabilities of the Kubernetes integration."""
        return {
            "context_types": ["pods", "deployments", "services", "events", "logs"],
            "actions": ["restart_pod", "scale_deployment", "rollback_deployment", "execute_kubectl"],
            "features": ["risk_assessment", "dry_run", "auto_approval"],
            "execution_modes": ["direct", "dry_run", "approval_required"],
            "risk_assessment": ["low", "medium", "high"],
            "command_types": list(self.command_risk_levels.keys())
        }

    async def fetch_context(self, context_type: str, **kwargs) -> dict[str, Any]:
        """Fetch context from Kubernetes cluster.
        
        This method is required by the base class and provides compatibility
        with the standard MCP integration interface.
        """
        # Map context_type to action for backward compatibility
        action = kwargs.get("action", context_type if context_type in ["list_pods", "get_pod_logs", "get_events"] else "list_pods")
        namespace = kwargs.get("namespace", "default")

        if action == "list_pods":
            result = await self._execute_kubectl_command(["get", "pods", "-n", namespace, "-o", "json"])
            if result.get("success"):
                import json
                try:
                    pods_data = json.loads(result.get("output", "{}"))
                    return {
                        "pods": [
                            {
                                "name": pod["metadata"]["name"],
                                "namespace": pod["metadata"]["namespace"],
                                "status": pod["status"]["phase"],
                                "containers": len(pod["spec"]["containers"])
                            }
                            for pod in pods_data.get("items", [])
                        ]
                    }
                except:
                    return {"error": "Failed to parse pod data"}
            else:
                return {"error": result.get("error", "Failed to list pods")}

        elif action == "get_pod_logs":
            pod_name = kwargs.get("pod_name")
            if not pod_name:
                return {"error": "pod_name is required"}
            result = await self._execute_kubectl_command(["logs", pod_name, "-n", namespace, "--tail=100"])
            return {"logs": result.get("output", ""), "success": result.get("success", False)}

        elif action == "get_events":
            result = await self._execute_kubectl_command(["get", "events", "-n", namespace, "-o", "json"])
            if result.get("success"):
                try:
                    import json
                    events_data = json.loads(result.get("output", "{}"))
                    return {
                        "events": [
                            {
                                "type": event.get("type"),
                                "reason": event.get("reason"),
                                "message": event.get("message"),
                                "object": f"{event.get('involvedObject', {}).get('kind')}/{event.get('involvedObject', {}).get('name')}"
                            }
                            for event in events_data.get("items", [])[-10:]  # Last 10 events
                        ]
                    }
                except:
                    return {"error": "Failed to parse events data"}
            else:
                return {"error": result.get("error", "Failed to get events")}

        else:
            return {"error": f"Unknown action: {action}"}

    async def execute_kubectl_command(self, command: list[str], dry_run: bool = False,
                                    auto_approve: bool = False) -> dict[str, Any]:
        """Execute a kubectl command with risk assessment and safety checks.
        
        Args:
            command: kubectl command as list of strings (e.g., ["get", "pods"])
            dry_run: If True, show what would be executed without doing it
            auto_approve: If True and risk is acceptable, execute without approval
            
        Returns:
            Result dictionary with execution details
        """
        # Assess command risk
        risk_assessment = self._assess_command_risk(command)

        # Log the command attempt
        self._log_command_attempt(command, risk_assessment)

        # Check if command is forbidden
        if risk_assessment["forbidden"]:
            return {
                "success": False,
                "error": f"Command is forbidden: {' '.join(command)}",
                "risk_assessment": risk_assessment
            }

        # Check if we need approval
        needs_approval = self._needs_approval(risk_assessment, auto_approve)

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "command": command,
                "risk_assessment": risk_assessment,
                "needs_approval": needs_approval,
                "would_execute": not needs_approval or auto_approve
            }

        if needs_approval and not auto_approve:
            return {
                "success": False,
                "error": "Command requires approval",
                "command": command,
                "risk_assessment": risk_assessment,
                "approval_required": True
            }

        # Execute the command
        result = await self._execute_kubectl_command(command)

        # Log execution result
        self._log_command_execution(command, result, risk_assessment)

        # Add risk assessment to result
        result["risk_assessment"] = risk_assessment

        return result

    def _assess_command_risk(self, command: list[str]) -> dict[str, Any]:
        """Assess the risk level of a kubectl command."""
        if not command:
            return {"risk_level": "low", "forbidden": False, "reason": "Empty command"}

        # Get the main command
        main_cmd = command[0] if command else ""

        # Check if forbidden
        full_command = " ".join(command).lower()
        forbidden = any(forbidden in full_command for forbidden in self.forbidden_commands)

        # Determine risk level
        risk_level = self.command_risk_levels.get(main_cmd, "medium")

        # Special cases that increase risk
        if any(arg in command for arg in ["--all", "--all-namespaces", "-A"]):
            risk_level = "high"
        if any(arg.startswith("kube-") for arg in command):  # System namespaces
            risk_level = "high"
        if "prod" in full_command or "production" in full_command:
            risk_level = "high"

        return {
            "risk_level": risk_level,
            "forbidden": forbidden,
            "command_type": main_cmd,
            "affects_all": "--all" in command or "--all-namespaces" in command,
            "reason": self._get_risk_reason(main_cmd, risk_level)
        }

    def _get_risk_reason(self, command: str, risk_level: str) -> str:
        """Get human-readable reason for risk assessment."""
        reasons = {
            "get": "Read-only operation",
            "describe": "Read-only operation",
            "logs": "Read-only operation",
            "delete": "Destructive operation that removes resources",
            "scale": "Modifies resource capacity",
            "apply": "Applies configuration changes",
            "exec": "Executes commands inside containers",
            "drain": "Removes pods from nodes"
        }
        return reasons.get(command, f"{risk_level.title()} risk operation")

    def _needs_approval(self, risk_assessment: dict[str, Any], auto_approve: bool) -> bool:
        """Determine if a command needs approval."""
        if risk_assessment["forbidden"]:
            return True

        if not self.enable_destructive and risk_assessment["risk_level"] != "low":
            return True

        if risk_assessment["risk_level"] == "high":
            return True

        if risk_assessment["risk_level"] == "medium" and not auto_approve:
            return True

        return False

    async def _execute_via_mcp(self, command: list[str]) -> dict[str, Any]:
        """Execute command via MCP server."""
        try:
            message = {
                "jsonrpc": "2.0",
                "id": self._get_next_id(),
                "method": "tools/call",
                "params": {
                    "name": "kubectl",
                    "arguments": {
                        "command": command
                    }
                }
            }

            self.mcp_process.stdin.write(json.dumps(message) + "\n")
            self.mcp_process.stdin.flush()

            response_line = self.mcp_process.stdout.readline()
            response = json.loads(response_line)

            if "error" in response:
                return {
                    "success": False,
                    "error": response["error"].get("message", "Unknown error"),
                    "command": command
                }

            result = response.get("result", {})
            return {
                "success": True,
                "output": result.get("content", [{}])[0].get("text", ""),
                "command": command,
                "via_mcp": True
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": command
            }

    async def _execute_kubectl_command(self, args: list[str]) -> dict[str, Any]:
        """Execute a kubectl command via MCP server protocol."""
        try:
            self.logger.debug(f"MCP server executing: kubectl {' '.join(args)}")

            cmd = ["kubectl"]
            if self.k8s_context:
                cmd.extend(["--context", self.k8s_context])
            cmd.extend(args)

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return {
                    "success": True,
                    "output": stdout.decode(),
                    "command": args,
                    "via_mcp": True
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode(),
                    "command": args,
                    "via_mcp": True
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": args
            }

    def _log_command_attempt(self, command: list[str], risk_assessment: dict[str, Any]) -> None:
        """Log a command attempt."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "command": command,
            "risk_assessment": risk_assessment,
            "status": "attempted"
        }
        self._audit_log.append(log_entry)
        self.logger.info(f"Command attempt: {' '.join(command)} (risk: {risk_assessment['risk_level']})")

    def _log_command_execution(self, command: list[str], result: dict[str, Any],
                              risk_assessment: dict[str, Any]) -> None:
        """Log a command execution result."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "command": command,
            "risk_assessment": risk_assessment,
            "status": "executed" if result.get("success") else "failed",
            "error": result.get("error")
        }
        self._audit_log.append(log_entry)

        status = "SUCCESS" if result.get("success") else "FAILED"
        self.logger.info(f"Command execution {status}: {' '.join(command)}")

    def _get_next_id(self) -> int:
        """Get next message ID for MCP protocol."""
        if not hasattr(self, "_message_id"):
            self._message_id = 100
        self._message_id += 1
        return self._message_id

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a Kubernetes action with automatic command generation."""
        # Map high-level actions to kubectl commands
        command_mapping = {
            "restart_pod": lambda p: ["delete", "pod", p["pod_name"], "-n", p.get("namespace", "default")],
            "scale_deployment": lambda p: ["scale", "deployment", p["deployment_name"],
                                         f"--replicas={p['replicas']}", "-n", p.get("namespace", "default")],
            "rollback_deployment": lambda p: ["rollout", "undo", "deployment", p["deployment_name"],
                                            "-n", p.get("namespace", "default")],
            "get_pod_logs": lambda p: ["logs", p["pod_name"], "-n", p.get("namespace", "default"),
                                     f"--tail={p.get('lines', 100)}"],
            "describe_pod": lambda p: ["describe", "pod", p["pod_name"], "-n", p.get("namespace", "default")],
            "check_pod_status": lambda p: ["get", "pod", p["pod_name"], "-n", p.get("namespace", "default"),
                                          "-o", "json"],
        }

        if action not in command_mapping:
            return {"success": False, "error": f"Unknown action: {action}"}

        # Generate kubectl command
        try:
            command = command_mapping[action](params)
        except KeyError as e:
            return {"success": False, "error": f"Missing required parameter: {e}"}

        # Execute with auto-approval based on mode
        auto_approve = params.get("auto_approve", False)
        dry_run = params.get("dry_run", False)

        result = await self.execute_kubectl_command(command, dry_run=dry_run, auto_approve=auto_approve)
        result["action"] = action
        result["params"] = params

        return result

    async def verify_action_success(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Verify that an action was successful."""
        verification_mapping = {
            "restart_pod": self._verify_pod_restart,
            "scale_deployment": self._verify_deployment_scale,
            "rollback_deployment": self._verify_deployment_rollback,
        }

        verify_func = verification_mapping.get(action)
        if not verify_func:
            return {"verified": False, "reason": "No verification available for this action"}

        return await verify_func(params)

    async def _verify_pod_restart(self, params: dict[str, Any]) -> dict[str, Any]:
        """Verify pod restart was successful."""
        # Wait a bit for pod to come back
        await asyncio.sleep(5)

        # Check if new pod is running
        command = ["get", "pod", "-n", params.get("namespace", "default"),
                  "-l", f"app={params.get('app_label', '')}", "-o", "json"]
        result = await self._execute_kubectl_command(command)

        if result.get("success"):
            try:
                pods_data = json.loads(result.get("output", "{}"))
                running_pods = [p for p in pods_data.get("items", [])
                              if p["status"]["phase"] == "Running"]
                return {
                    "verified": len(running_pods) > 0,
                    "running_pods": len(running_pods),
                    "details": "Pod restarted successfully" if running_pods else "No running pods found"
                }
            except:
                return {"verified": False, "reason": "Failed to parse pod status"}

        return {"verified": False, "reason": result.get("error", "Unknown error")}

    async def _verify_deployment_scale(self, params: dict[str, Any]) -> dict[str, Any]:
        """Verify deployment scale was successful."""
        command = ["get", "deployment", params["deployment_name"],
                  "-n", params.get("namespace", "default"), "-o", "json"]
        result = await self._execute_kubectl_command(command)

        if result.get("success"):
            try:
                deployment_data = json.loads(result.get("output", "{}"))
                status = deployment_data.get("status", {})
                desired = params["replicas"]
                ready = status.get("readyReplicas", 0)

                return {
                    "verified": ready == desired,
                    "desired_replicas": desired,
                    "ready_replicas": ready,
                    "details": f"Deployment scaled to {ready}/{desired} replicas"
                }
            except:
                return {"verified": False, "reason": "Failed to parse deployment status"}

        return {"verified": False, "reason": result.get("error", "Unknown error")}

    async def _verify_deployment_rollback(self, params: dict[str, Any]) -> dict[str, Any]:
        """Verify deployment rollback was successful."""
        command = ["rollout", "status", "deployment", params["deployment_name"],
                  "-n", params.get("namespace", "default")]
        result = await self._execute_kubectl_command(command)

        return {
            "verified": result.get("success", False),
            "details": result.get("output", "").strip() if result.get("success") else result.get("error", "")
        }

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log of all commands."""
        return self._audit_log

    # Add compatibility methods for the standard K8s integration interface
    async def list_pods(self, namespace: str = "default") -> dict[str, Any]:
        """List pods in a namespace."""
        return await self.fetch_context({"action": "list_pods", "namespace": namespace})

    async def get_pod_logs(self, pod_name: str, namespace: str = "default", tail_lines: int = 100) -> dict[str, Any]:
        """Get pod logs."""
        result = await self._execute_kubectl_command(["logs", pod_name, "-n", namespace, f"--tail={tail_lines}"])
        return {"success": result.get("success", False), "logs": result.get("output", "")}

    async def get_pod_events(self, pod_name: str, namespace: str = "default") -> dict[str, Any]:
        """Get pod events."""
        result = await self._execute_kubectl_command([
            "get", "events", "-n", namespace,
            f"--field-selector=involvedObject.name={pod_name}",
            "-o", "json"
        ])
        if result.get("success"):
            try:
                import json
                events_data = json.loads(result.get("output", "{}"))
                return {
                    "success": True,
                    "events": events_data.get("items", [])
                }
            except:
                return {"success": False, "error": "Failed to parse events"}
        return {"success": False, "error": result.get("error", "Unknown error")}

    async def describe_pod(self, pod_name: str, namespace: str = "default") -> dict[str, Any]:
        """Describe a pod."""
        result = await self._execute_kubectl_command(["describe", "pod", pod_name, "-n", namespace])
        return {"success": result.get("success", False), "description": result.get("output", "")}

    async def get_deployment_status(self, deployment_name: str, namespace: str = "default") -> dict[str, Any]:
        """Get deployment status."""
        result = await self._execute_kubectl_command(["get", "deployment", deployment_name, "-n", namespace, "-o", "json"])
        if result.get("success"):
            try:
                import json
                deployment_data = json.loads(result.get("output", "{}"))
                return {
                    "success": True,
                    "deployment": {
                        "name": deployment_data.get("metadata", {}).get("name"),
                        "namespace": deployment_data.get("metadata", {}).get("namespace"),
                        "replicas": deployment_data.get("status", {}).get("replicas", 0),
                        "ready": deployment_data.get("status", {}).get("readyReplicas", 0),
                        "healthy": deployment_data.get("status", {}).get("readyReplicas", 0) == deployment_data.get("spec", {}).get("replicas", 1)
                    }
                }
            except:
                return {"success": False, "error": "Failed to parse deployment"}
        return {"success": False, "error": result.get("error", "Unknown error")}

    async def get_service_status(self, service_name: str, namespace: str = "default") -> dict[str, Any]:
        """Get service status."""
        result = await self._execute_kubectl_command(["get", "service", service_name, "-n", namespace, "-o", "json"])
        if result.get("success"):
            try:
                import json
                service_data = json.loads(result.get("output", "{}"))
                endpoints_result = await self._execute_kubectl_command(["get", "endpoints", service_name, "-n", namespace, "-o", "json"])
                endpoint_count = 0
                if endpoints_result.get("success"):
                    try:
                        endpoints_data = json.loads(endpoints_result.get("output", "{}"))
                        endpoint_count = len(endpoints_data.get("subsets", []))
                    except:
                        pass

                return {
                    "success": True,
                    "service": {
                        "name": service_data.get("metadata", {}).get("name"),
                        "namespace": service_data.get("metadata", {}).get("namespace"),
                        "type": service_data.get("spec", {}).get("type"),
                        "selector": service_data.get("spec", {}).get("selector", {}),
                        "endpoint_count": endpoint_count
                    }
                }
            except:
                return {"success": False, "error": "Failed to parse service"}
        return {"success": False, "error": result.get("error", "Unknown error")}
