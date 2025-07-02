"""
Kubernetes Authentication Service

This service handles multiple authentication methods for connecting to any Kubernetes cluster:
- Kubeconfig file upload
- Service account token authentication
- Client certificate authentication
- Cloud provider authentication (EKS, GKE, AKS)
"""

import base64
import json
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from cryptography.fernet import Fernet
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from src.oncall_agent.config import get_config
from src.oncall_agent.utils.logger import get_logger


class AuthMethod(Enum):
    """Kubernetes authentication methods"""
    KUBECONFIG = "kubeconfig"
    SERVICE_ACCOUNT = "service_account"
    CLIENT_CERT = "client_certificate"
    EKS = "eks"
    GKE = "gke"
    AKS = "aks"
    OIDC = "oidc"


@dataclass
class K8sCredentials:
    """Kubernetes cluster credentials"""
    auth_method: AuthMethod
    cluster_endpoint: str
    cluster_name: str

    # Kubeconfig method
    kubeconfig_data: str | None = None

    # Service account method
    service_account_token: str | None = None
    ca_certificate: str | None = None

    # Client certificate method
    client_certificate: str | None = None
    client_key: str | None = None

    # Cloud provider specific
    cloud_config: dict[str, Any] | None = None

    # Common options
    namespace: str = "default"
    verify_ssl: bool = True
    proxy_url: str | None = None


class KubernetesAuthService:
    """Service for handling Kubernetes authentication"""

    def __init__(self):
        self.config = get_config()
        self.logger = get_logger(__name__)
        self._fernet = Fernet(self._get_or_create_key())

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for credentials"""
        key_path = Path(".k8s_auth_key")
        if key_path.exists():
            return key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            return key

    async def validate_kubeconfig(self, kubeconfig_content: str) -> dict[str, Any]:
        """Validate and parse kubeconfig file content"""
        try:
            # Parse kubeconfig
            kubeconfig = yaml.safe_load(kubeconfig_content)

            if not isinstance(kubeconfig, dict):
                return {
                    "valid": False,
                    "error": "Invalid kubeconfig format"
                }

            # Extract available contexts
            contexts = []
            current_context = kubeconfig.get("current-context", "")

            for context in kubeconfig.get("contexts", []):
                context_name = context.get("name", "")
                cluster_name = context.get("context", {}).get("cluster", "")
                user_name = context.get("context", {}).get("user", "")
                namespace = context.get("context", {}).get("namespace", "default")

                # Find cluster info
                cluster_info = None
                for cluster in kubeconfig.get("clusters", []):
                    if cluster.get("name") == cluster_name:
                        cluster_info = cluster.get("cluster", {})
                        break

                if cluster_info:
                    contexts.append({
                        "name": context_name,
                        "cluster": cluster_name,
                        "user": user_name,
                        "namespace": namespace,
                        "server": cluster_info.get("server", ""),
                        "is_current": context_name == current_context
                    })

            return {
                "valid": True,
                "contexts": contexts,
                "current_context": current_context
            }

        except Exception as e:
            self.logger.error(f"Failed to validate kubeconfig: {e}")
            return {
                "valid": False,
                "error": str(e)
            }

    async def test_connection(self, credentials: K8sCredentials) -> dict[str, Any]:
        """Test connection to Kubernetes cluster"""
        try:
            # Create temporary config
            api_client = await self._create_api_client(credentials)

            # Test connection by getting version
            v1 = client.VersionApi(api_client)
            version = v1.get_code()

            # Try to list namespaces (basic permission check)
            core_v1 = client.CoreV1Api(api_client)
            namespaces = core_v1.list_namespace(limit=1)

            return {
                "connected": True,
                "cluster_version": f"{version.major}.{version.minor}",
                "platform": version.platform,
                "can_list_namespaces": True
            }

        except ApiException as e:
            if e.status == 403:
                # Connection works but insufficient permissions
                return {
                    "connected": True,
                    "error": "Connected but insufficient permissions",
                    "can_list_namespaces": False
                }
            else:
                return {
                    "connected": False,
                    "error": f"API error: {e.reason}"
                }
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return {
                "connected": False,
                "error": str(e)
            }

    async def verify_permissions(self, credentials: K8sCredentials,
                               required_permissions: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Verify RBAC permissions for the credentials"""
        if required_permissions is None:
            # Default permissions needed for oncall-agent
            required_permissions = [
                {"verb": "get", "resource": "pods"},
                {"verb": "list", "resource": "pods"},
                {"verb": "watch", "resource": "pods"},
                {"verb": "delete", "resource": "pods"},
                {"verb": "get", "resource": "deployments"},
                {"verb": "list", "resource": "deployments"},
                {"verb": "update", "resource": "deployments"},
                {"verb": "patch", "resource": "deployments"},
                {"verb": "get", "resource": "services"},
                {"verb": "list", "resource": "services"},
                {"verb": "get", "resource": "events"},
                {"verb": "list", "resource": "events"},
            ]

        try:
            api_client = await self._create_api_client(credentials)
            auth_v1 = client.AuthorizationV1Api(api_client)

            results = []
            for perm in required_permissions:
                # Create self subject access review
                body = client.V1SelfSubjectAccessReview(
                    spec=client.V1SelfSubjectAccessReviewSpec(
                        resource_attributes=client.V1ResourceAttributes(
                            verb=perm["verb"],
                            resource=perm["resource"],
                            namespace=credentials.namespace
                        )
                    )
                )

                try:
                    review = auth_v1.create_self_subject_access_review(body)
                    allowed = review.status.allowed
                except Exception as e:
                    allowed = False
                    self.logger.error(f"Permission check failed: {e}")

                results.append({
                    "permission": f"{perm['verb']} {perm['resource']}",
                    "allowed": allowed
                })

            all_allowed = all(r["allowed"] for r in results)

            return {
                "all_permissions_granted": all_allowed,
                "permissions": results
            }

        except Exception as e:
            self.logger.error(f"Permission verification failed: {e}")
            return {
                "all_permissions_granted": False,
                "error": str(e)
            }

    async def get_cluster_info(self, credentials: K8sCredentials) -> dict[str, Any]:
        """Get detailed cluster information"""
        try:
            api_client = await self._create_api_client(credentials)

            # Get nodes
            core_v1 = client.CoreV1Api(api_client)
            nodes = core_v1.list_node()

            node_info = []
            total_cpu = 0
            total_memory = 0

            for node in nodes.items:
                status = node.status
                allocatable = status.allocatable

                # Parse CPU (convert to millicores)
                cpu_str = allocatable.get("cpu", "0")
                if cpu_str.endswith("m"):
                    cpu_millicores = int(cpu_str[:-1])
                else:
                    cpu_millicores = int(cpu_str) * 1000

                # Parse memory (convert to bytes)
                memory_str = allocatable.get("memory", "0Ki")
                memory_bytes = self._parse_memory(memory_str)

                total_cpu += cpu_millicores
                total_memory += memory_bytes

                node_info.append({
                    "name": node.metadata.name,
                    "status": "Ready" if self._is_node_ready(node) else "NotReady",
                    "version": status.node_info.kubelet_version,
                    "os": status.node_info.operating_system,
                    "cpu_millicores": cpu_millicores,
                    "memory_bytes": memory_bytes
                })

            # Get namespaces count
            namespaces = core_v1.list_namespace()

            # Get pods count
            pods = core_v1.list_pod_for_all_namespaces()

            # Get services count
            services = core_v1.list_service_for_all_namespaces()

            # Get deployments count
            apps_v1 = client.AppsV1Api(api_client)
            deployments = apps_v1.list_deployment_for_all_namespaces()

            return {
                "nodes": node_info,
                "node_count": len(node_info),
                "total_cpu_cores": total_cpu / 1000,  # Convert back to cores
                "total_memory_gb": total_memory / (1024**3),  # Convert to GB
                "namespace_count": len(namespaces.items),
                "pod_count": len(pods.items),
                "service_count": len(services.items),
                "deployment_count": len(deployments.items)
            }

        except Exception as e:
            self.logger.error(f"Failed to get cluster info: {e}")
            return {
                "error": str(e)
            }

    def encrypt_credentials(self, credentials: K8sCredentials) -> str:
        """Encrypt credentials for storage"""
        # Convert credentials to dict
        cred_dict = {
            "auth_method": credentials.auth_method.value,
            "cluster_endpoint": credentials.cluster_endpoint,
            "cluster_name": credentials.cluster_name,
            "kubeconfig_data": credentials.kubeconfig_data,
            "service_account_token": credentials.service_account_token,
            "ca_certificate": credentials.ca_certificate,
            "client_certificate": credentials.client_certificate,
            "client_key": credentials.client_key,
            "cloud_config": credentials.cloud_config,
            "namespace": credentials.namespace,
            "verify_ssl": credentials.verify_ssl,
            "proxy_url": credentials.proxy_url
        }

        # Encrypt
        json_str = json.dumps(cred_dict)
        encrypted = self._fernet.encrypt(json_str.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_credentials(self, encrypted_data: str) -> K8sCredentials:
        """Decrypt stored credentials"""
        try:
            # Decrypt
            encrypted_bytes = base64.b64decode(encrypted_data)
            decrypted = self._fernet.decrypt(encrypted_bytes)
            cred_dict = json.loads(decrypted.decode())

            # Convert back to credentials object
            return K8sCredentials(
                auth_method=AuthMethod(cred_dict["auth_method"]),
                cluster_endpoint=cred_dict["cluster_endpoint"],
                cluster_name=cred_dict["cluster_name"],
                kubeconfig_data=cred_dict.get("kubeconfig_data"),
                service_account_token=cred_dict.get("service_account_token"),
                ca_certificate=cred_dict.get("ca_certificate"),
                client_certificate=cred_dict.get("client_certificate"),
                client_key=cred_dict.get("client_key"),
                cloud_config=cred_dict.get("cloud_config"),
                namespace=cred_dict.get("namespace", "default"),
                verify_ssl=cred_dict.get("verify_ssl", True),
                proxy_url=cred_dict.get("proxy_url")
            )
        except Exception as e:
            self.logger.error(f"Failed to decrypt credentials: {e}")
            raise

    async def _create_api_client(self, credentials: K8sCredentials) -> client.ApiClient:
        """Create Kubernetes API client from credentials"""
        configuration = client.Configuration()

        if credentials.auth_method == AuthMethod.KUBECONFIG:
            # Use kubeconfig
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(credentials.kubeconfig_data)
                f.flush()

                # Load config from file
                config.load_kube_config(config_file=f.name)
                Path(f.name).unlink()  # Clean up temp file

                return client.ApiClient()

        elif credentials.auth_method == AuthMethod.SERVICE_ACCOUNT:
            # Configure with service account token
            configuration.host = credentials.cluster_endpoint
            configuration.verify_ssl = credentials.verify_ssl

            if credentials.ca_certificate:
                # Write CA cert to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
                    f.write(credentials.ca_certificate)
                    f.flush()
                    configuration.ssl_ca_cert = f.name

            configuration.api_key = {"authorization": f"Bearer {credentials.service_account_token}"}

            return client.ApiClient(configuration)

        elif credentials.auth_method == AuthMethod.CLIENT_CERT:
            # Configure with client certificates
            configuration.host = credentials.cluster_endpoint
            configuration.verify_ssl = credentials.verify_ssl

            if credentials.ca_certificate:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
                    f.write(credentials.ca_certificate)
                    f.flush()
                    configuration.ssl_ca_cert = f.name

            if credentials.client_certificate:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
                    f.write(credentials.client_certificate)
                    f.flush()
                    configuration.cert_file = f.name

            if credentials.client_key:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as f:
                    f.write(credentials.client_key)
                    f.flush()
                    configuration.key_file = f.name

            return client.ApiClient(configuration)

        else:
            raise NotImplementedError(f"Auth method {credentials.auth_method} not implemented yet")

    def _parse_memory(self, memory_str: str) -> int:
        """Parse Kubernetes memory string to bytes"""
        units = {
            "Ki": 1024,
            "Mi": 1024**2,
            "Gi": 1024**3,
            "Ti": 1024**4,
            "K": 1000,
            "M": 1000**2,
            "G": 1000**3,
            "T": 1000**4
        }

        for unit, multiplier in units.items():
            if memory_str.endswith(unit):
                return int(float(memory_str[:-len(unit)]) * multiplier)

        # No unit means bytes
        return int(memory_str)

    def _is_node_ready(self, node) -> bool:
        """Check if node is ready"""
        for condition in node.status.conditions:
            if condition.type == "Ready":
                return condition.status == "True"
        return False
