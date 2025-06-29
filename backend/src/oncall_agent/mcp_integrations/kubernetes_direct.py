"""
Direct Kubernetes integration using the official Python client.

This integration provides a more reliable alternative to MCP servers
by using the kubernetes Python client directly.
"""

import base64
import tempfile
from datetime import UTC, datetime
from typing import Any

import yaml
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.base import MCPIntegration
from src.oncall_agent.utils.logger import get_logger


class KubernetesDirectIntegration(MCPIntegration):
    """Direct Kubernetes integration using Python client."""

    def __init__(self,
                 namespace: str = "default",
                 context: str | None = None,
                 kubeconfig_content: str | None = None,
                 enable_destructive_operations: bool = False):
        """Initialize Kubernetes integration."""
        super().__init__(name="kubernetes_direct")
        self.config = get_config()
        self.logger = get_logger(f"{__name__}.Direct")

        # Configuration
        self.namespace = namespace
        self.context = context
        self.kubeconfig_content = kubeconfig_content
        self.enable_destructive_operations = enable_destructive_operations

        # Kubernetes clients
        self.core_v1 = None
        self.apps_v1 = None
        self._connected = False
        self.connected = False
        self.connection_time = None
        self._kubeconfig_file = None

    async def connect(self) -> bool:
        """Connect to Kubernetes cluster."""
        try:
            self.logger.info(f"Attempting to connect to Kubernetes - context: '{self.context}', namespace: '{self.namespace}'")

            if self.kubeconfig_content:
                # Use provided kubeconfig
                with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                    # Decode if base64 encoded
                    if self.kubeconfig_content.startswith('LS0t'):
                        content = base64.b64decode(self.kubeconfig_content).decode('utf-8')
                    else:
                        content = self.kubeconfig_content

                    f.write(content)
                    self._kubeconfig_file = f.name

                self.logger.info(f"Loading kubeconfig from temporary file with context: '{self.context}'")
                config.load_kube_config(
                    config_file=self._kubeconfig_file,
                    context=self.context
                )
            else:
                # Use default kubeconfig
                self.logger.info(f"Loading default kubeconfig with context: '{self.context}'")
                config.load_kube_config(context=self.context)

            # Initialize clients
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()

            # Test connection
            self.core_v1.list_namespace(limit=1)

            self._connected = True
            self.connected = True
            self.connection_time = datetime.now(UTC)

            self.logger.info(f"Connected to Kubernetes (context: {self.context or 'current'})")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Kubernetes: {e}")
            self._connected = False
            self.connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from Kubernetes."""
        self._connected = False
        self.connected = False
        self.core_v1 = None
        self.apps_v1 = None

        # Clean up temp kubeconfig
        if self._kubeconfig_file:
            import os
            try:
                os.unlink(self._kubeconfig_file)
            except:
                pass
            self._kubeconfig_file = None

        self.logger.info("Disconnected from Kubernetes")

    async def fetch_context(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch Kubernetes context information."""
        if not self._connected:
            return {"error": "Not connected to Kubernetes"}

        context_type = params.get("type", "pods")
        namespace = params.get("namespace", self.namespace)

        try:
            if context_type == "pods":
                pods = self.core_v1.list_namespaced_pod(namespace)
                return {
                    "pods": [{
                        "name": pod.metadata.name,
                        "namespace": pod.metadata.namespace,
                        "status": pod.status.phase,
                        "ready": all(c.ready for c in pod.status.container_statuses or []),
                        "containers": len(pod.spec.containers)
                    } for pod in pods.items]
                }

            elif context_type == "deployments":
                deployments = self.apps_v1.list_namespaced_deployment(namespace)
                return {
                    "deployments": [{
                        "name": d.metadata.name,
                        "namespace": d.metadata.namespace,
                        "replicas": d.spec.replicas,
                        "ready_replicas": d.status.ready_replicas or 0,
                        "available": d.status.available_replicas == d.spec.replicas
                    } for d in deployments.items]
                }

            elif context_type == "services":
                services = self.core_v1.list_namespaced_service(namespace)
                return {
                    "services": [{
                        "name": s.metadata.name,
                        "namespace": s.metadata.namespace,
                        "type": s.spec.type,
                        "cluster_ip": s.spec.cluster_ip,
                        "ports": [{"port": p.port, "protocol": p.protocol} for p in s.spec.ports or []]
                    } for s in services.items]
                }

            elif context_type == "events":
                events = self.core_v1.list_event_for_all_namespaces(limit=100)
                return {
                    "events": [{
                        "namespace": e.namespace,
                        "name": e.metadata.name,
                        "reason": e.reason,
                        "message": e.message,
                        "type": e.type,
                        "object": f"{e.involved_object.kind}/{e.involved_object.name}",
                        "timestamp": e.first_timestamp.isoformat() if e.first_timestamp else None
                    } for e in events.items]
                }

            elif context_type == "namespaces":
                namespaces = self.core_v1.list_namespace()
                return {
                    "namespaces": [{
                        "name": ns.metadata.name,
                        "status": ns.status.phase,
                        "labels": ns.metadata.labels or {}
                    } for ns in namespaces.items]
                }

            else:
                return {"error": f"Unknown context type: {context_type}"}

        except ApiException as e:
            return {"error": f"Kubernetes API error: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a Kubernetes action."""
        if not self._connected:
            return {"success": False, "error": "Not connected to Kubernetes"}

        # Check permissions for destructive operations
        destructive_actions = ["restart_pod", "delete_resource", "scale_deployment"]
        if action in destructive_actions and not self.enable_destructive_operations:
            return {
                "success": False,
                "error": f"Destructive operation '{action}' not enabled"
            }

        try:
            if action == "restart_pod":
                pod_name = params.get("pod_name")
                namespace = params.get("namespace", self.namespace)

                # Delete pod to force restart
                self.core_v1.delete_namespaced_pod(
                    name=pod_name,
                    namespace=namespace,
                    grace_period_seconds=30
                )

                return {
                    "success": True,
                    "message": f"Pod {pod_name} deleted for restart",
                    "action": action,
                    "params": params
                }

            elif action == "check_pod_logs":
                pod_name = params.get("pod_name")
                namespace = params.get("namespace", self.namespace)
                tail_lines = params.get("tail_lines", 100)
                container = params.get("container")

                logs = self.core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    container=container,
                    tail_lines=tail_lines
                )

                return {
                    "success": True,
                    "logs": logs,
                    "action": action,
                    "params": params
                }

            elif action == "scale_deployment":
                deployment_name = params.get("deployment_name")
                replicas = params.get("replicas")
                namespace = params.get("namespace", self.namespace)

                # Get current deployment
                deployment = self.apps_v1.read_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace
                )

                # Update replicas
                deployment.spec.replicas = replicas

                # Apply update
                self.apps_v1.patch_namespaced_deployment(
                    name=deployment_name,
                    namespace=namespace,
                    body=deployment
                )

                return {
                    "success": True,
                    "message": f"Deployment {deployment_name} scaled to {replicas} replicas",
                    "action": action,
                    "params": params
                }

            elif action == "describe_resource":
                kind = params.get("kind", "pod").lower()
                name = params.get("name")
                namespace = params.get("namespace", self.namespace)

                if kind == "pod":
                    resource = self.core_v1.read_namespaced_pod(name, namespace)
                elif kind == "deployment":
                    resource = self.apps_v1.read_namespaced_deployment(name, namespace)
                elif kind == "service":
                    resource = self.core_v1.read_namespaced_service(name, namespace)
                else:
                    return {"success": False, "error": f"Unsupported resource kind: {kind}"}

                # Convert to dict for JSON serialization
                description = {
                    "name": resource.metadata.name,
                    "namespace": resource.metadata.namespace,
                    "labels": resource.metadata.labels,
                    "annotations": resource.metadata.annotations,
                    "creation_timestamp": resource.metadata.creation_timestamp.isoformat()
                }

                return {
                    "success": True,
                    "description": description,
                    "action": action,
                    "params": params
                }

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except ApiException as e:
            return {
                "success": False,
                "error": f"Kubernetes API error: {e.reason}",
                "status_code": e.status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_capabilities(self) -> list[str]:
        """Get list of available capabilities."""
        capabilities = [
            "get_pods",
            "get_deployments",
            "get_services",
            "get_logs",
            "describe_resource",
            "get_events",
            "get_namespaces"
        ]

        if self.enable_destructive_operations:
            capabilities.extend([
                "restart_pod",
                "scale_deployment",
                "delete_resource"
            ])

        return capabilities

    async def health_check(self) -> bool:
        """Check if connection is healthy."""
        if not self._connected:
            return False

        try:
            self.core_v1.list_namespace(limit=1)
            return True
        except:
            return False

    async def test_connection(self, context_name: str | None = None) -> dict[str, Any]:
        """Test connection to Kubernetes."""
        try:
            # If different context, reconnect
            if context_name and context_name != self.context:
                await self.disconnect()
                self.context = context_name
                connected = await self.connect()

                if not connected:
                    return {
                        "connected": False,
                        "error": "Failed to connect to Kubernetes cluster"
                    }

            # Get cluster info
            version = self.core_v1.get_api_resources().group_version

            # Count namespaces
            namespaces = self.core_v1.list_namespace()

            # Get nodes
            nodes = self.core_v1.list_node()

            return {
                "connected": True,
                "context": self.context or "current",
                "namespace": self.namespace,
                "api_version": version,
                "namespaces_count": len(namespaces.items),
                "nodes_count": len(nodes.items),
                "nodes": [{"name": n.metadata.name, "status": n.status.phase} for n in nodes.items]
            }

        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }

    async def discover_contexts(self) -> list[dict[str, Any]]:
        """Discover available Kubernetes contexts."""
        try:
            # Load kubeconfig to get contexts
            if self.kubeconfig_content:
                # Parse kubeconfig
                if self.kubeconfig_content.startswith('LS0t'):
                    content = base64.b64decode(self.kubeconfig_content).decode('utf-8')
                else:
                    content = self.kubeconfig_content

                kubeconfig = yaml.safe_load(content)
            else:
                # Load default kubeconfig
                from pathlib import Path
                kubeconfig_path = Path.home() / ".kube" / "config"

                if not kubeconfig_path.exists():
                    return []

                with open(kubeconfig_path) as f:
                    kubeconfig = yaml.safe_load(f)

            contexts = []
            current_context = kubeconfig.get("current-context")

            for ctx in kubeconfig.get("contexts", []):
                contexts.append({
                    "name": ctx["name"],
                    "cluster": ctx["context"]["cluster"],
                    "namespace": ctx["context"].get("namespace", "default"),
                    "is_current": ctx["name"] == current_context
                })

            return contexts

        except Exception as e:
            self.logger.error(f"Error discovering contexts: {e}")
            return []

    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information."""
        return {
            "type": "direct",
            "context": self.context or "current",
            "namespace": self.namespace,
            "destructive_operations_enabled": self.enable_destructive_operations,
            "connected": self._connected,
            "using_kubeconfig": self.kubeconfig_content is not None
        }
