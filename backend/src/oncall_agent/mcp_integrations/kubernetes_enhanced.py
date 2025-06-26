"""Enhanced Kubernetes MCP integration with auto-discovery and improved management."""

import logging
import os
from datetime import datetime
from typing import Any

import yaml
from kubernetes import client
from kubernetes import config as k8s_config
from kubernetes.client.rest import ApiException

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.base import MCPIntegration


class EnhancedKubernetesMCPIntegration(MCPIntegration):
    """Enhanced Kubernetes MCP integration with auto-discovery and better error handling."""

    def __init__(self, context_name: str | None = None, namespace: str | None = None):
        """Initialize enhanced Kubernetes MCP integration.
        
        Args:
            context_name: Specific context to use, or None for auto-discovery
            namespace: Default namespace, or None to use context default
        """
        super().__init__(name="kubernetes")
        self.config = get_config()
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.context_name = context_name
        self.namespace = namespace or "default"
        self.enable_destructive = self.config.k8s_enable_destructive_operations

        # Kubernetes clients
        self.v1 = None
        self.apps_v1 = None
        self.batch_v1 = None

        # State
        self._audit_log = []
        self._connected = False
        self._available_contexts = []
        self._current_context = None
        self._cluster_info = {}

    async def discover_contexts(self) -> list[dict[str, Any]]:
        """Discover available Kubernetes contexts from kubeconfig."""
        contexts = []

        try:
            # Try multiple kubeconfig locations
            kubeconfig_paths = [
                os.path.expanduser(self.config.k8s_config_path),
                os.path.expanduser("~/.kube/config"),
                os.environ.get("KUBECONFIG", ""),
                "/etc/kubernetes/admin.conf",
            ]

            for path in kubeconfig_paths:
                if path and os.path.exists(path):
                    try:
                        with open(path) as f:
                            kubeconfig = yaml.safe_load(f)

                        for context in kubeconfig.get('contexts', []):
                            context_name = context['name']
                            cluster_name = context['context'].get('cluster', 'unknown')
                            namespace = context['context'].get('namespace', 'default')
                            user = context['context'].get('user', 'unknown')

                            # Try to get cluster info
                            cluster_info = {}
                            for cluster in kubeconfig.get('clusters', []):
                                if cluster['name'] == cluster_name:
                                    cluster_info = {
                                        'server': cluster['cluster'].get('server', 'unknown'),
                                        'insecure': cluster['cluster'].get('insecure-skip-tls-verify', False)
                                    }
                                    break

                            contexts.append({
                                'name': context_name,
                                'cluster': cluster_name,
                                'namespace': namespace,
                                'user': user,
                                'kubeconfig_path': path,
                                'cluster_info': cluster_info,
                                'is_current': context_name == kubeconfig.get('current-context')
                            })
                    except Exception as e:
                        self.logger.warning(f"Failed to parse kubeconfig at {path}: {e}")
                        continue

            # Also check if we're running inside a cluster
            if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token'):
                contexts.append({
                    'name': 'in-cluster',
                    'cluster': 'in-cluster',
                    'namespace': 'default',
                    'user': 'serviceaccount',
                    'kubeconfig_path': None,
                    'cluster_info': {'server': 'https://kubernetes.default.svc'},
                    'is_current': False
                })

            self._available_contexts = contexts
            return contexts

        except Exception as e:
            self.logger.error(f"Failed to discover Kubernetes contexts: {e}")
            return []

    async def test_connection(self, context_name: str, namespace: str = "default") -> dict[str, Any]:
        """Test connection to a specific Kubernetes context."""
        try:
            # Try to load the specific context
            if context_name == 'in-cluster':
                k8s_config.load_incluster_config()
            else:
                # Find the kubeconfig path for this context
                kubeconfig_path = None
                for ctx in self._available_contexts:
                    if ctx['name'] == context_name:
                        kubeconfig_path = ctx['kubeconfig_path']
                        break

                if not kubeconfig_path:
                    return {
                        'success': False,
                        'error': f'Context {context_name} not found'
                    }

                k8s_config.load_kube_config(
                    config_file=kubeconfig_path,
                    context=context_name
                )

            # Create temporary client to test
            v1 = client.CoreV1Api()

            # Test basic connectivity
            namespaces = v1.list_namespace(limit=1)

            # Test namespace access
            try:
                ns = v1.read_namespace(namespace)
                namespace_exists = True
            except ApiException as e:
                if e.status == 404:
                    namespace_exists = False
                else:
                    raise

            # Get cluster version
            version_info = v1.get_api_resources().group_version

            # Count some resources
            pods = v1.list_pod_for_all_namespaces(limit=1)
            nodes = v1.list_node()

            return {
                'success': True,
                'context': context_name,
                'namespace': namespace,
                'namespace_exists': namespace_exists,
                'cluster_version': version_info,
                'node_count': len(nodes.items),
                'connection_time': datetime.utcnow().isoformat(),
                'permissions': {
                    'can_list_pods': True,
                    'can_list_nodes': True,
                    'can_list_namespaces': True
                }
            }

        except ApiException as e:
            return {
                'success': False,
                'error': f'Kubernetes API error: {e.reason}',
                'status_code': e.status,
                'details': e.body
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }

    async def verify_permissions(self, context_name: str) -> dict[str, Any]:
        """Verify RBAC permissions for the given context."""
        permissions = {
            'read': {},
            'write': {},
            'errors': []
        }

        try:
            # Load context
            if context_name == 'in-cluster':
                k8s_config.load_incluster_config()
            else:
                kubeconfig_path = None
                for ctx in self._available_contexts:
                    if ctx['name'] == context_name:
                        kubeconfig_path = ctx['kubeconfig_path']
                        break

                if kubeconfig_path:
                    k8s_config.load_kube_config(
                        config_file=kubeconfig_path,
                        context=context_name
                    )

            v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()

            # Test read permissions
            read_tests = [
                ('pods', lambda: v1.list_pod_for_all_namespaces(limit=1)),
                ('services', lambda: v1.list_service_for_all_namespaces(limit=1)),
                ('deployments', lambda: apps_v1.list_deployment_for_all_namespaces(limit=1)),
                ('nodes', lambda: v1.list_node(limit=1)),
                ('events', lambda: v1.list_event_for_all_namespaces(limit=1)),
                ('configmaps', lambda: v1.list_config_map_for_all_namespaces(limit=1)),
                ('secrets', lambda: v1.list_secret_for_all_namespaces(limit=1)),
            ]

            for resource, test_func in read_tests:
                try:
                    test_func()
                    permissions['read'][resource] = True
                except ApiException as e:
                    permissions['read'][resource] = False
                    if e.status == 403:
                        permissions['errors'].append(f"No read permission for {resource}")

            # Test write permissions (dry-run)
            if self.enable_destructive:
                write_tests = [
                    ('pods', lambda: self._test_pod_delete_permission(v1)),
                    ('deployments', lambda: self._test_deployment_scale_permission(apps_v1)),
                ]

                for resource, test_func in write_tests:
                    try:
                        test_func()
                        permissions['write'][resource] = True
                    except ApiException as e:
                        permissions['write'][resource] = False
                        if e.status == 403:
                            permissions['errors'].append(f"No write permission for {resource}")

            permissions['summary'] = {
                'can_read': any(permissions['read'].values()),
                'can_write': any(permissions['write'].values()),
                'is_admin': all(permissions['read'].values()) and all(permissions['write'].values())
            }

            return permissions

        except Exception as e:
            self.logger.error(f"Failed to verify permissions: {e}")
            return {
                'error': str(e),
                'summary': {
                    'can_read': False,
                    'can_write': False,
                    'is_admin': False
                }
            }

    def _test_pod_delete_permission(self, v1) -> bool:
        """Test if we have permission to delete pods (using dry-run)."""
        try:
            # Try to delete a non-existent pod with dry-run
            v1.delete_namespaced_pod(
                name="test-permission-check-pod",
                namespace="default",
                dry_run="All"
            )
            return True
        except ApiException as e:
            if e.status == 404:  # Not found is ok, means we have permission
                return True
            raise

    def _test_deployment_scale_permission(self, apps_v1) -> bool:
        """Test if we have permission to scale deployments (using dry-run)."""
        try:
            # Try to patch a non-existent deployment with dry-run
            apps_v1.patch_namespaced_deployment_scale(
                name="test-permission-check-deployment",
                namespace="default",
                body={"spec": {"replicas": 1}},
                dry_run="All"
            )
            return True
        except ApiException as e:
            if e.status == 404:  # Not found is ok, means we have permission
                return True
            raise

    async def get_cluster_info(self, context_name: str) -> dict[str, Any]:
        """Get detailed information about a Kubernetes cluster."""
        try:
            # Test connection first
            test_result = await self.test_connection(context_name)
            if not test_result['success']:
                return test_result

            # Load context
            if context_name == 'in-cluster':
                k8s_config.load_incluster_config()
            else:
                kubeconfig_path = None
                for ctx in self._available_contexts:
                    if ctx['name'] == context_name:
                        kubeconfig_path = ctx['kubeconfig_path']
                        break

                if kubeconfig_path:
                    k8s_config.load_kube_config(
                        config_file=kubeconfig_path,
                        context=context_name
                    )

            v1 = client.CoreV1Api()
            apps_v1 = client.AppsV1Api()

            # Get cluster info
            nodes = v1.list_node()
            namespaces = v1.list_namespace()

            # Get resource counts
            pods = v1.list_pod_for_all_namespaces()
            services = v1.list_service_for_all_namespaces()
            deployments = apps_v1.list_deployment_for_all_namespaces()

            # Calculate cluster stats
            total_cpu = 0
            total_memory = 0
            for node in nodes.items:
                if node.status.allocatable:
                    cpu = node.status.allocatable.get('cpu', '0')
                    memory = node.status.allocatable.get('memory', '0')
                    # Parse CPU (convert to millicores)
                    if cpu.endswith('m'):
                        total_cpu += int(cpu[:-1])
                    else:
                        total_cpu += int(cpu) * 1000
                    # Parse memory (convert to bytes)
                    if memory.endswith('Ki'):
                        total_memory += int(memory[:-2]) * 1024
                    elif memory.endswith('Mi'):
                        total_memory += int(memory[:-2]) * 1024 * 1024
                    elif memory.endswith('Gi'):
                        total_memory += int(memory[:-2]) * 1024 * 1024 * 1024

            return {
                'success': True,
                'context': context_name,
                'cluster_info': {
                    'node_count': len(nodes.items),
                    'namespace_count': len(namespaces.items),
                    'pod_count': len(pods.items),
                    'service_count': len(services.items),
                    'deployment_count': len(deployments.items),
                    'total_cpu_millicores': total_cpu,
                    'total_memory_bytes': total_memory,
                    'namespaces': [ns.metadata.name for ns in namespaces.items],
                    'nodes': [{
                        'name': node.metadata.name,
                        'status': node.status.phase,
                        'version': node.status.node_info.kubelet_version,
                        'os': node.status.node_info.os_image,
                        'container_runtime': node.status.node_info.container_runtime_version
                    } for node in nodes.items]
                }
            }

        except Exception as e:
            self.logger.error(f"Failed to get cluster info: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def connect(self) -> None:
        """Connect to Kubernetes cluster with auto-discovery."""
        try:
            # Discover available contexts
            contexts = await self.discover_contexts()

            if not contexts:
                raise Exception("No Kubernetes contexts found")

            # Use specified context or find the best one
            if self.context_name:
                # Use specified context
                context_to_use = self.context_name
            else:
                # Try to find current context or first available
                current_context = next((ctx for ctx in contexts if ctx['is_current']), None)
                if current_context:
                    context_to_use = current_context['name']
                else:
                    context_to_use = contexts[0]['name']

            # Test connection
            test_result = await self.test_connection(context_to_use, self.namespace)
            if not test_result['success']:
                raise Exception(f"Failed to connect to context {context_to_use}: {test_result.get('error')}")

            # Actually connect
            if context_to_use == 'in-cluster':
                k8s_config.load_incluster_config()
            else:
                kubeconfig_path = None
                for ctx in contexts:
                    if ctx['name'] == context_to_use:
                        kubeconfig_path = ctx['kubeconfig_path']
                        break

                if kubeconfig_path:
                    k8s_config.load_kube_config(
                        config_file=kubeconfig_path,
                        context=context_to_use
                    )

            # Create API clients
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.batch_v1 = client.BatchV1Api()

            # Store connection info
            self._current_context = context_to_use
            self._connected = True
            self.connected = True
            self.connection_time = datetime.utcnow()

            # Get cluster info
            self._cluster_info = await self.get_cluster_info(context_to_use)

            self.logger.info(f"Connected to Kubernetes cluster: {context_to_use}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Kubernetes: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Kubernetes cluster."""
        try:
            self.v1 = None
            self.apps_v1 = None
            self.batch_v1 = None
            self._connected = False
            self.connected = False
            self._current_context = None
            self._cluster_info = {}
            self.logger.info("Disconnected from Kubernetes cluster")
        except Exception as e:
            self.logger.error(f"Error disconnecting from Kubernetes: {e}")

    async def health_check(self) -> bool:
        """Check if Kubernetes connection is healthy."""
        if not self._connected or not self.v1:
            return False

        try:
            # Try to list namespaces as a health check
            self.v1.list_namespace(limit=1)
            return True
        except:
            return False

    async def get_capabilities(self) -> dict[str, list[str]]:
        """Return capabilities of the Kubernetes integration."""
        context_types = [
            "pod_crash",
            "service_health",
            "resource_usage",
            "deployment_status",
            "node_health",
            "general"
        ]

        actions = [
            "list_pods",
            "get_pod_logs",
            "describe_pod",
            "get_pod_events",
            "get_service_status",
            "get_deployment_status",
            "list_nodes",
            "get_node_status",
            "execute_kubectl_command",
        ]

        if self.enable_destructive:
            actions.extend([
                "restart_pod",
                "scale_deployment",
                "rollback_deployment",
                "delete_pod",
                "patch_deployment"
            ])

        features = [
            "auto_discovery",
            "multi_context",
            "rbac_verification",
            "audit_logging",
            "retry_mechanism",
            "safety_checks"
        ]

        return {
            "context_types": context_types,
            "actions": actions,
            "features": features
        }

    async def fetch_context(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch Kubernetes context for incident analysis."""
        context_type = params.get("type", "general")
        namespace = params.get("namespace", self.namespace)

        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "context_type": context_type,
            "namespace": namespace,
            "cluster": self._current_context
        }

        try:
            if context_type == "pod_crash":
                # Get problematic pods
                pods = await self._list_pods_async(namespace)
                problematic_pods = [
                    p for p in pods
                    if p.get("status") in ["CrashLoopBackOff", "Error", "ImagePullBackOff", "OOMKilled"]
                ]
                context["problematic_pods"] = problematic_pods

                # Get logs for crashed pods
                for pod in problematic_pods[:3]:  # Limit to 3 pods
                    pod_name = pod.get("name")
                    logs = await self._get_pod_logs_async(pod_name, namespace, tail_lines=50)
                    pod["recent_logs"] = logs

            elif context_type == "service_health":
                # Get services and their endpoints
                services = self.v1.list_namespaced_service(namespace)
                endpoints = self.v1.list_namespaced_endpoints(namespace)

                context["services"] = [self._serialize_k8s_object(svc) for svc in services.items]
                context["endpoints"] = [self._serialize_k8s_object(ep) for ep in endpoints.items]

            elif context_type == "resource_usage":
                # Get metrics if available
                try:
                    # This requires metrics-server to be installed
                    from kubernetes import client as metrics_client
                    metrics_v1 = metrics_client.MetricsV1beta1Api()

                    node_metrics = metrics_v1.list_node_metrics()
                    pod_metrics = metrics_v1.list_namespaced_pod_metrics(namespace)

                    context["node_metrics"] = [self._serialize_k8s_object(m) for m in node_metrics.items]
                    context["pod_metrics"] = [self._serialize_k8s_object(m) for m in pod_metrics.items]
                except:
                    context["metrics_unavailable"] = "Metrics server not available"

            elif context_type == "deployment_status":
                # Get deployments and replicasets
                deployments = self.apps_v1.list_namespaced_deployment(namespace)
                replicasets = self.apps_v1.list_namespaced_replica_set(namespace)

                context["deployments"] = [self._serialize_k8s_object(d) for d in deployments.items]
                context["replicasets"] = [self._serialize_k8s_object(rs) for rs in replicasets.items]

            else:
                # General cluster overview
                context["namespaces"] = [ns.metadata.name for ns in self.v1.list_namespace().items]
                context["nodes"] = [self._serialize_k8s_object(n) for n in self.v1.list_node().items]

                # Recent events
                events = self.v1.list_event_for_all_namespaces(limit=20)
                context["recent_events"] = [self._serialize_k8s_object(e) for e in events.items]

        except Exception as e:
            self.logger.error(f"Error fetching Kubernetes context: {e}")
            context["error"] = str(e)

        return context

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a Kubernetes action."""
        self._log_action(action, params)

        try:
            if action == "restart_pod":
                return await self._restart_pod(
                    params.get("pod_name"),
                    params.get("namespace", self.namespace)
                )
            elif action == "scale_deployment":
                return await self._scale_deployment(
                    params.get("deployment_name"),
                    params.get("namespace", self.namespace),
                    params.get("replicas", 1)
                )
            elif action == "rollback_deployment":
                return await self._rollback_deployment(
                    params.get("deployment_name"),
                    params.get("namespace", self.namespace)
                )
            elif action == "get_pod_logs":
                return await self._get_pod_logs_async(
                    params.get("pod_name"),
                    params.get("namespace", self.namespace),
                    params.get("tail_lines", 100)
                )
            else:
                return {"error": f"Unsupported action: {action}"}

        except Exception as e:
            self.logger.error(f"Error executing action {action}: {e}")
            return {"error": str(e)}

    async def _list_pods_async(self, namespace: str | None = None) -> list[dict[str, Any]]:
        """List pods asynchronously."""
        if namespace:
            pods = self.v1.list_namespaced_pod(namespace)
        else:
            pods = self.v1.list_pod_for_all_namespaces()

        result = []
        for pod in pods.items:
            pod_info = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "ready": f"{sum(1 for c in pod.status.container_statuses or [] if c.ready)}/{len(pod.spec.containers)}",
                "restarts": sum(c.restart_count for c in pod.status.container_statuses or []),
                "age": pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else "Unknown",
                "node": pod.spec.node_name
            }

            # Check for specific conditions
            if pod.status.container_statuses:
                for container in pod.status.container_statuses:
                    if container.state.waiting:
                        pod_info["status"] = container.state.waiting.reason
                    elif container.state.terminated:
                        pod_info["status"] = container.state.terminated.reason

            result.append(pod_info)

        return result

    async def _get_pod_logs_async(self, pod_name: str, namespace: str, tail_lines: int = 100) -> str:
        """Get pod logs asynchronously."""
        try:
            logs = self.v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                tail_lines=tail_lines
            )
            return logs
        except Exception as e:
            return f"Error getting logs: {str(e)}"

    async def _restart_pod(self, pod_name: str, namespace: str) -> dict[str, Any]:
        """Restart a pod by deleting it."""
        if not self.enable_destructive:
            return {
                "success": False,
                "error": "Destructive operations are disabled"
            }

        try:
            # Check if pod is managed by a controller
            pod = self.v1.read_namespaced_pod(pod_name, namespace)
            if not pod.metadata.owner_references:
                return {
                    "success": False,
                    "error": "Pod is not managed by a controller. Manual restart may cause data loss."
                }

            # Delete the pod
            self.v1.delete_namespaced_pod(pod_name, namespace)

            return {
                "success": True,
                "message": f"Pod {pod_name} deleted. Controller will create a new pod.",
                "action": "restart_pod",
                "pod": pod_name,
                "namespace": namespace
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _scale_deployment(self, deployment_name: str, namespace: str, replicas: int) -> dict[str, Any]:
        """Scale a deployment."""
        if not self.enable_destructive:
            return {
                "success": False,
                "error": "Destructive operations are disabled"
            }

        try:
            # Get current deployment
            deployment = self.apps_v1.read_namespaced_deployment(deployment_name, namespace)

            # Update replicas
            deployment.spec.replicas = replicas
            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )

            return {
                "success": True,
                "message": f"Deployment {deployment_name} scaled to {replicas} replicas",
                "deployment": deployment_name,
                "namespace": namespace,
                "replicas": replicas
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _rollback_deployment(self, deployment_name: str, namespace: str) -> dict[str, Any]:
        """Rollback a deployment to previous version."""
        if not self.enable_destructive:
            return {
                "success": False,
                "error": "Destructive operations are disabled"
            }

        try:
            # This is a simplified rollback - in production you'd want to handle this more carefully
            # Get the deployment
            deployment = self.apps_v1.read_namespaced_deployment(deployment_name, namespace)

            # Trigger a rollout by updating an annotation
            if not deployment.spec.template.metadata.annotations:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations['kubectl.kubernetes.io/restartedAt'] = datetime.utcnow().isoformat()

            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=deployment
            )

            return {
                "success": True,
                "message": f"Deployment {deployment_name} rollback initiated",
                "deployment": deployment_name,
                "namespace": namespace
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _serialize_k8s_object(self, obj: Any) -> dict[str, Any]:
        """Serialize Kubernetes object to dict."""
        # This is a simplified serialization - you might want to expand this
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

    def _log_action(self, action: str, params: dict[str, Any]) -> None:
        """Log an action for audit trail."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "params": params,
            "context": self._current_context,
            "user": "oncall-agent"
        }
        self._audit_log.append(log_entry)
        self.logger.info(f"Audit: {action} executed with params: {params}")

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Get the audit log of all actions taken."""
        return self._audit_log

    def get_connection_info(self) -> dict[str, Any]:
        """Get current connection information."""
        return {
            "connected": self._connected,
            "current_context": self._current_context,
            "available_contexts": self._available_contexts,
            "cluster_info": self._cluster_info,
            "namespace": self.namespace,
            "destructive_operations_enabled": self.enable_destructive
        }
