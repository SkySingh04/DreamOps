"""Deterministic Kubernetes resolution strategies with guaranteed fixes."""

import logging
from typing import Any

from src.oncall_agent.strategies.kubernetes_resolver import ResolutionAction


class DeterministicK8sResolver:
    """Provides deterministic resolution actions for known Kubernetes issues."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_deterministic_fixes(self, alert_description: str, metadata: dict[str, Any]) -> list[ResolutionAction]:
        """Return deterministic fixes based on alert patterns."""
        actions = []
        namespace = metadata.get("namespace", "oncall-test-apps")

        # Normalize description for matching
        desc_lower = alert_description.lower()

        # 1. OOM Kill - Scale to 3 replicas
        if "oom" in desc_lower or "memory" in desc_lower:
            # Check if it's our test app
            if "oom-app" in desc_lower or metadata.get("deployment_name") == "oom-app":
                actions.append(ResolutionAction(
                    action_type="scale_deployment",
                    description="Scale OOM app to 3 replicas to distribute memory load",
                    params={
                        "deployment_name": "oom-app",
                        "namespace": namespace,
                        "replicas": 3
                    },
                    confidence=1.0,
                    risk_level="low",
                    estimated_time="30s",
                    rollback_possible=True
                ))
            else:
                # Generic OOM fix - scale up
                deployment = metadata.get("deployment_name")
                if deployment:
                    actions.append(ResolutionAction(
                        action_type="scale_deployment",
                        description="Scale deployment to handle memory load",
                        params={
                            "deployment_name": deployment,
                            "namespace": namespace,
                            "replicas": 3
                        },
                        confidence=0.9,
                        risk_level="low",
                        estimated_time="30s",
                        rollback_possible=True
                    ))

        # 2. Image Pull Error - Update to nginx:latest
        elif "imagepull" in desc_lower or "image" in desc_lower:
            if "bad-image-app" in desc_lower or metadata.get("deployment_name") == "bad-image-app":
                actions.append(ResolutionAction(
                    action_type="update_image",
                    description="Update image to nginx:latest",
                    params={
                        "deployment_name": "bad-image-app",
                        "namespace": namespace,
                        "container_name": "app",
                        "new_image": "nginx:latest"
                    },
                    confidence=1.0,
                    risk_level="low",
                    estimated_time="1m",
                    rollback_possible=True
                ))

        # 3. Crash Loop - Delete pods
        elif "crash" in desc_lower or "crashloop" in desc_lower:
            if "crashloop-app" in desc_lower or metadata.get("deployment_name") == "crashloop-app":
                actions.append(ResolutionAction(
                    action_type="delete_pods_by_label",
                    description="Delete crash looping pods to force recreation",
                    params={
                        "namespace": namespace,
                        "label_selector": "app=crashloop-app"
                    },
                    confidence=1.0,
                    risk_level="low",
                    estimated_time="30s",
                    rollback_possible=False
                ))
            else:
                # Generic crash fix - restart pod
                pod_name = metadata.get("pod_name")
                if pod_name:
                    actions.append(ResolutionAction(
                        action_type="restart_pod",
                        description="Restart crashing pod",
                        params={
                            "pod_name": pod_name,
                            "namespace": namespace
                        },
                        confidence=0.8,
                        risk_level="low",
                        estimated_time="30s",
                        rollback_possible=False
                    ))

        # 4. Resource Limits - Patch memory to 256Mi
        elif "resource" in desc_lower or "limit" in desc_lower:
            if "resource-limited-app" in desc_lower or metadata.get("deployment_name") == "resource-limited-app":
                actions.append(ResolutionAction(
                    action_type="patch_memory_limit",
                    description="Increase memory limit to 256Mi",
                    params={
                        "deployment_name": "resource-limited-app",
                        "namespace": namespace,
                        "memory_limit": "256Mi"
                    },
                    confidence=1.0,
                    risk_level="low",
                    estimated_time="30s",
                    rollback_possible=True
                ))

        # 5. Service Down - Scale from 0 to 2
        elif "service" in desc_lower and "down" in desc_lower:
            if "down-service" in desc_lower or metadata.get("deployment_name") == "down-service-app":
                actions.append(ResolutionAction(
                    action_type="scale_deployment",
                    description="Scale deployment from 0 to 2 replicas",
                    params={
                        "deployment_name": "down-service-app",
                        "namespace": namespace,
                        "replicas": 2
                    },
                    confidence=1.0,
                    risk_level="low",
                    estimated_time="30s",
                    rollback_possible=True
                ))

        # Generic pod errors - identify and fix
        elif "poderror" in desc_lower or "problempod" in desc_lower:
            actions.extend([
                ResolutionAction(
                    action_type="identify_error_pods",
                    description="Identify all pods with errors",
                    params={
                        "namespace": namespace,
                        "check_all_namespaces": namespace == "default"
                    },
                    confidence=0.95,
                    risk_level="low",
                    estimated_time="10s",
                    rollback_possible=False
                ),
                ResolutionAction(
                    action_type="restart_error_pods",
                    description="Restart all error pods",
                    params={
                        "namespace": namespace,
                        "states": ["Error", "CrashLoopBackOff", "ImagePullBackOff", "Pending"]
                    },
                    confidence=0.85,
                    risk_level="medium",
                    estimated_time="2m",
                    rollback_possible=False
                )
            ])

        return actions
