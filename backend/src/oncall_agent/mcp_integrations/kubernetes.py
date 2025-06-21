"""Kubernetes MCP integration for debugging oncall issues.

This integration uses manusa/kubernetes-mcp-server due to:
- Native Go implementation with better performance
- More comprehensive k8s operations support
- Direct Kubernetes API interaction without overhead
- Better documentation and active maintenance
- Multiple installation options (npm, Python, binary)
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.oncall_agent.mcp_integrations.base import MCPIntegration
from src.oncall_agent.config import get_config


class KubernetesMCPIntegration(MCPIntegration):
    """Kubernetes MCP integration for cluster operations and debugging."""
    
    def __init__(self):
        """Initialize Kubernetes MCP integration."""
        super().__init__()
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
        self.mcp_server_url = None
        self.mcp_process = None
        self.k8s_context = None
        self.enable_destructive = False
        self._audit_log = []
        
    async def connect(self) -> None:
        """Start the Kubernetes MCP server and establish connection."""
        try:
            # Get configuration
            k8s_config_path = self.config.get("K8S_CONFIG_PATH", "~/.kube/config")
            self.k8s_context = self.config.get("K8S_CONTEXT", "default")
            self.mcp_server_url = self.config.get("K8S_MCP_SERVER_URL", "http://localhost:8080")
            self.enable_destructive = self.config.get("K8S_ENABLE_DESTRUCTIVE_OPERATIONS", "false").lower() == "true"
            
            # Start the MCP server process
            cmd = [
                "npx", "kubernetes-mcp-server@latest",
                "--http-port", "8080",
                "--kubeconfig", k8s_config_path,
            ]
            
            if not self.enable_destructive:
                cmd.append("--read-only")
                
            self.mcp_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for server to start
            await asyncio.sleep(2)
            
            # Test connection
            if await self.health_check():
                self.logger.info(f"Connected to Kubernetes MCP server at {self.mcp_server_url}")
                self._connected = True
            else:
                raise Exception("Failed to connect to Kubernetes MCP server")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Kubernetes: {e}")
            raise
            
    async def disconnect(self) -> None:
        """Stop the Kubernetes MCP server."""
        try:
            if self.mcp_process:
                self.mcp_process.terminate()
                await self.mcp_process.wait()
                self.mcp_process = None
            self._connected = False
            self.logger.info("Disconnected from Kubernetes MCP server")
        except Exception as e:
            self.logger.error(f"Error disconnecting from Kubernetes: {e}")
            
    async def health_check(self) -> bool:
        """Check if Kubernetes MCP server is healthy."""
        try:
            # Try to list namespaces as a health check
            result = await self._execute_k8s_command("get", "namespaces", "--output=json")
            return result.get("success", False)
        except:
            return False
            
    def get_capabilities(self) -> List[str]:
        """Return list of supported Kubernetes operations."""
        capabilities = [
            "list_pods",
            "get_pod_logs", 
            "describe_pod",
            "get_pod_events",
            "get_service_status",
            "get_deployment_status",
            "execute_kubectl_command",
            "list_namespaces",
            "get_resource_usage",
        ]
        
        if self.enable_destructive:
            capabilities.extend([
                "restart_pod",
                "scale_deployment",
                "rollback_deployment"
            ])
            
        return capabilities
        
    async def fetch_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch Kubernetes context for incident analysis."""
        context_type = params.get("type", "general")
        namespace = params.get("namespace", "default")
        
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "context_type": context_type,
            "namespace": namespace
        }
        
        try:
            if context_type == "pod_crash":
                # Get problematic pods
                pods = await self.list_pods(namespace)
                problematic_pods = [
                    p for p in pods.get("pods", []) 
                    if p.get("status") in ["CrashLoopBackOff", "Error", "ImagePullBackOff"]
                ]
                context["problematic_pods"] = problematic_pods
                
                # Get logs for crashed pods
                for pod in problematic_pods[:3]:  # Limit to 3 pods
                    pod_name = pod.get("name")
                    logs = await self.get_pod_logs(pod_name, namespace, tail_lines=50)
                    pod["recent_logs"] = logs
                    
            elif context_type == "service_health":
                # Get services and their endpoints
                services = await self._execute_k8s_command("get", "services", "-n", namespace, "--output=json")
                endpoints = await self._execute_k8s_command("get", "endpoints", "-n", namespace, "--output=json")
                context["services"] = services
                context["endpoints"] = endpoints
                
            elif context_type == "resource_usage":
                # Get node and pod resource usage
                nodes = await self._execute_k8s_command("top", "nodes", "--output=json")
                pods = await self._execute_k8s_command("top", "pods", "-n", namespace, "--output=json")
                context["node_usage"] = nodes
                context["pod_usage"] = pods
                
            else:
                # General cluster overview
                context["namespaces"] = await self._execute_k8s_command("get", "namespaces", "--output=json")
                context["nodes"] = await self._execute_k8s_command("get", "nodes", "--output=json")
                context["events"] = await self._execute_k8s_command("get", "events", "--all-namespaces", "--output=json")
                
        except Exception as e:
            self.logger.error(f"Error fetching Kubernetes context: {e}")
            context["error"] = str(e)
            
        return context
        
    async def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a Kubernetes action."""
        self._log_action(action, params)
        
        try:
            if action == "restart_pod":
                return await self.restart_pod(
                    params.get("pod_name"),
                    params.get("namespace", "default")
                )
            elif action == "scale_deployment":
                return await self.scale_deployment(
                    params.get("deployment_name"),
                    params.get("namespace", "default"),
                    params.get("replicas", 1)
                )
            elif action == "rollback_deployment":
                return await self.rollback_deployment(
                    params.get("deployment_name"),
                    params.get("namespace", "default")
                )
            else:
                return {"error": f"Unsupported action: {action}"}
                
        except Exception as e:
            self.logger.error(f"Error executing action {action}: {e}")
            return {"error": str(e)}
            
    # Kubernetes Operations
    
    async def list_pods(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """List all pods or pods in a specific namespace."""
        cmd_args = ["get", "pods", "--output=json"]
        if namespace:
            cmd_args.extend(["-n", namespace])
        else:
            cmd_args.append("--all-namespaces")
            
        result = await self._execute_k8s_command(*cmd_args)
        
        if result.get("success"):
            pods_data = json.loads(result.get("output", "{}"))
            pods = []
            for item in pods_data.get("items", []):
                pod = {
                    "name": item["metadata"]["name"],
                    "namespace": item["metadata"]["namespace"],
                    "status": item["status"]["phase"],
                    "ready": f"{sum(1 for c in item['status'].get('containerStatuses', []) if c.get('ready'))}/{len(item['spec']['containers'])}",
                    "restarts": sum(c.get("restartCount", 0) for c in item["status"].get("containerStatuses", [])),
                    "age": item["metadata"]["creationTimestamp"]
                }
                
                # Check for specific conditions
                for condition in item["status"].get("conditions", []):
                    if condition["type"] == "Ready" and condition["status"] != "True":
                        pod["status"] = condition.get("reason", "NotReady")
                        
                pods.append(pod)
                
            return {"success": True, "pods": pods}
        else:
            return result
            
    async def get_pod_logs(self, pod_name: str, namespace: str, tail_lines: int = 100) -> Dict[str, Any]:
        """Get logs from a specific pod."""
        cmd_args = ["logs", pod_name, "-n", namespace, f"--tail={tail_lines}"]
        result = await self._execute_k8s_command(*cmd_args)
        
        if result.get("success"):
            return {
                "success": True,
                "pod": pod_name,
                "namespace": namespace,
                "logs": result.get("output", "")
            }
        else:
            return result
            
    async def describe_pod(self, pod_name: str, namespace: str) -> Dict[str, Any]:
        """Get detailed description of a pod."""
        cmd_args = ["describe", "pod", pod_name, "-n", namespace]
        result = await self._execute_k8s_command(*cmd_args)
        
        if result.get("success"):
            return {
                "success": True,
                "pod": pod_name,
                "namespace": namespace,
                "description": result.get("output", "")
            }
        else:
            return result
            
    async def get_pod_events(self, pod_name: str, namespace: str) -> Dict[str, Any]:
        """Get events related to a specific pod."""
        cmd_args = ["get", "events", "-n", namespace, f"--field-selector=involvedObject.name={pod_name}", "--output=json"]
        result = await self._execute_k8s_command(*cmd_args)
        
        if result.get("success"):
            events_data = json.loads(result.get("output", "{}"))
            events = []
            for event in events_data.get("items", []):
                events.append({
                    "type": event.get("type"),
                    "reason": event.get("reason"),
                    "message": event.get("message"),
                    "firstTimestamp": event.get("firstTimestamp"),
                    "lastTimestamp": event.get("lastTimestamp"),
                    "count": event.get("count", 1)
                })
            return {
                "success": True,
                "pod": pod_name,
                "namespace": namespace,
                "events": events
            }
        else:
            return result
            
    async def restart_pod(self, pod_name: str, namespace: str) -> Dict[str, Any]:
        """Restart a pod by deleting it (with safety checks)."""
        if not self.enable_destructive:
            return {
                "success": False,
                "error": "Destructive operations are disabled. Set K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true to enable."
            }
            
        # Safety check: Confirm pod exists and get its controller
        describe_result = await self.describe_pod(pod_name, namespace)
        if not describe_result.get("success"):
            return {"success": False, "error": "Pod not found or cannot be described"}
            
        # Check if pod is managed by a controller (deployment, replicaset, etc)
        description = describe_result.get("description", "")
        if "Controlled By:" not in description:
            return {
                "success": False,
                "error": "Pod is not managed by a controller. Manual restart may cause data loss.",
                "recommendation": "Create a new pod manually instead"
            }
            
        # Proceed with deletion
        self.logger.warning(f"Restarting pod {pod_name} in namespace {namespace}")
        cmd_args = ["delete", "pod", pod_name, "-n", namespace]
        result = await self._execute_k8s_command(*cmd_args)
        
        if result.get("success"):
            return {
                "success": True,
                "message": f"Pod {pod_name} deleted. Controller will create a new pod.",
                "action": "restart_pod",
                "pod": pod_name,
                "namespace": namespace
            }
        else:
            return result
            
    async def get_service_status(self, service_name: str, namespace: str) -> Dict[str, Any]:
        """Get status of a Kubernetes service."""
        # Get service details
        svc_cmd = ["get", "service", service_name, "-n", namespace, "--output=json"]
        svc_result = await self._execute_k8s_command(*svc_cmd)
        
        if not svc_result.get("success"):
            return svc_result
            
        service_data = json.loads(svc_result.get("output", "{}"))
        
        # Get endpoints
        ep_cmd = ["get", "endpoints", service_name, "-n", namespace, "--output=json"]
        ep_result = await self._execute_k8s_command(*ep_cmd)
        
        endpoints_data = {}
        if ep_result.get("success"):
            endpoints_data = json.loads(ep_result.get("output", "{}"))
            
        # Extract relevant information
        status = {
            "name": service_name,
            "namespace": namespace,
            "type": service_data.get("spec", {}).get("type"),
            "cluster_ip": service_data.get("spec", {}).get("clusterIP"),
            "ports": service_data.get("spec", {}).get("ports", []),
            "selector": service_data.get("spec", {}).get("selector", {}),
            "endpoints": []
        }
        
        # Parse endpoints
        for subset in endpoints_data.get("subsets", []):
            for address in subset.get("addresses", []):
                status["endpoints"].append({
                    "ip": address.get("ip"),
                    "target": address.get("targetRef", {}).get("name")
                })
                
        status["endpoint_count"] = len(status["endpoints"])
        status["healthy"] = status["endpoint_count"] > 0
        
        return {"success": True, "service": status}
        
    async def get_deployment_status(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """Get status of a Kubernetes deployment."""
        cmd_args = ["get", "deployment", deployment_name, "-n", namespace, "--output=json"]
        result = await self._execute_k8s_command(*cmd_args)
        
        if not result.get("success"):
            return result
            
        deployment_data = json.loads(result.get("output", "{}"))
        status = deployment_data.get("status", {})
        
        deployment_status = {
            "name": deployment_name,
            "namespace": namespace,
            "replicas": {
                "desired": status.get("replicas", 0),
                "updated": status.get("updatedReplicas", 0),
                "ready": status.get("readyReplicas", 0),
                "available": status.get("availableReplicas", 0)
            },
            "conditions": []
        }
        
        # Parse conditions
        for condition in status.get("conditions", []):
            deployment_status["conditions"].append({
                "type": condition.get("type"),
                "status": condition.get("status"),
                "reason": condition.get("reason"),
                "message": condition.get("message")
            })
            
        # Determine overall health
        deployment_status["healthy"] = (
            deployment_status["replicas"]["ready"] == deployment_status["replicas"]["desired"] and
            deployment_status["replicas"]["desired"] > 0
        )
        
        return {"success": True, "deployment": deployment_status}
        
    async def scale_deployment(self, deployment_name: str, namespace: str, replicas: int) -> Dict[str, Any]:
        """Scale a deployment to specified number of replicas."""
        if not self.enable_destructive:
            return {
                "success": False,
                "error": "Destructive operations are disabled. Set K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true to enable."
            }
            
        cmd_args = ["scale", "deployment", deployment_name, "-n", namespace, f"--replicas={replicas}"]
        result = await self._execute_k8s_command(*cmd_args)
        
        if result.get("success"):
            return {
                "success": True,
                "message": f"Deployment {deployment_name} scaled to {replicas} replicas",
                "deployment": deployment_name,
                "namespace": namespace,
                "replicas": replicas
            }
        else:
            return result
            
    async def rollback_deployment(self, deployment_name: str, namespace: str) -> Dict[str, Any]:
        """Rollback a deployment to previous version."""
        if not self.enable_destructive:
            return {
                "success": False,
                "error": "Destructive operations are disabled. Set K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true to enable."
            }
            
        cmd_args = ["rollout", "undo", "deployment", deployment_name, "-n", namespace]
        result = await self._execute_k8s_command(*cmd_args)
        
        if result.get("success"):
            return {
                "success": True,
                "message": f"Deployment {deployment_name} rolled back to previous version",
                "deployment": deployment_name,
                "namespace": namespace
            }
        else:
            return result
            
    async def execute_kubectl_command(self, command: str) -> Dict[str, Any]:
        """Execute arbitrary kubectl command (with restrictions)."""
        # Safety: Disallow certain dangerous commands
        dangerous_keywords = ["delete", "exec", "port-forward", "proxy", "edit", "apply", "create", "patch"]
        command_lower = command.lower()
        
        if not self.enable_destructive and any(keyword in command_lower for keyword in dangerous_keywords):
            return {
                "success": False,
                "error": f"Command contains restricted keywords: {dangerous_keywords}. Enable destructive operations to use these."
            }
            
        # Parse and execute command
        cmd_parts = command.split()
        if cmd_parts[0] == "kubectl":
            cmd_parts = cmd_parts[1:]  # Remove kubectl prefix if present
            
        result = await self._execute_k8s_command(*cmd_parts)
        return result
        
    # Helper methods
    
    async def _execute_k8s_command(self, *args) -> Dict[str, Any]:
        """Execute a kubectl command via MCP server."""
        try:
            # Construct kubectl command
            cmd = ["kubectl"]
            if self.k8s_context:
                cmd.extend(["--context", self.k8s_context])
            cmd.extend(args)
            
            # Log the command
            self.logger.debug(f"Executing: {' '.join(cmd)}")
            
            # Execute command
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
                    "command": ' '.join(cmd)
                }
            else:
                return {
                    "success": False,
                    "error": stderr.decode(),
                    "command": ' '.join(cmd)
                }
                
        except Exception as e:
            self.logger.error(f"Error executing kubectl command: {e}")
            return {
                "success": False,
                "error": str(e),
                "command": ' '.join(args)
            }
            
    def _log_action(self, action: str, params: Dict[str, Any]) -> None:
        """Log an action for audit trail."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "params": params,
            "user": "oncall-agent"
        }
        self._audit_log.append(log_entry)
        self.logger.info(f"Audit: {action} executed with params: {params}")
        
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get the audit log of all actions taken."""
        return self._audit_log