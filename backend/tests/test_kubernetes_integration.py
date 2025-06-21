"""Tests for Kubernetes MCP integration."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.mcp_integrations.kubernetes import KubernetesMCPIntegration
from src.oncall_agent.strategies.kubernetes_resolver import (
    KubernetesResolver,
)


class TestKubernetesMCPIntegration:
    """Test Kubernetes MCP integration functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            "K8S_CONFIG_PATH": "/mock/.kube/config",
            "K8S_CONTEXT": "test-context",
            "K8S_MCP_SERVER_URL": "http://localhost:8080",
            "K8S_ENABLE_DESTRUCTIVE_OPERATIONS": "false"
        }

    @pytest.fixture
    async def k8s_integration(self, mock_config, monkeypatch):
        """Create a Kubernetes integration with mocked config."""
        monkeypatch.setattr("src.oncall_agent.config.get_config", lambda: Mock(get=lambda k, d=None: mock_config.get(k, d)))
        integration = KubernetesMCPIntegration()
        # Mock the MCP server process
        integration.mcp_process = Mock()
        integration._connected = True
        return integration

    @pytest.mark.asyncio
    async def test_list_pods(self, k8s_integration):
        """Test listing pods."""
        # Mock kubectl command execution
        mock_output = '''
        {
            "items": [
                {
                    "metadata": {"name": "test-pod-1", "namespace": "default"},
                    "status": {"phase": "Running", "containerStatuses": [{"ready": true, "restartCount": 0}]},
                    "spec": {"containers": [{"name": "test"}]}
                }
            ]
        }
        '''

        with patch.object(k8s_integration, '_execute_k8s_command',
                         return_value={"success": True, "output": mock_output}):
            result = await k8s_integration.list_pods("default")

        assert result["success"] is True
        assert len(result["pods"]) == 1
        assert result["pods"][0]["name"] == "test-pod-1"
        assert result["pods"][0]["status"] == "Running"

    @pytest.mark.asyncio
    async def test_get_pod_logs(self, k8s_integration):
        """Test getting pod logs."""
        mock_logs = "2024-01-01 10:00:00 INFO Application started\n2024-01-01 10:00:01 ERROR Connection refused"

        with patch.object(k8s_integration, '_execute_k8s_command',
                         return_value={"success": True, "output": mock_logs}):
            result = await k8s_integration.get_pod_logs("test-pod", "default", tail_lines=50)

        assert result["success"] is True
        assert result["pod"] == "test-pod"
        assert "Connection refused" in result["logs"]

    @pytest.mark.asyncio
    async def test_restart_pod_disabled(self, k8s_integration):
        """Test that restart pod fails when destructive operations are disabled."""
        result = await k8s_integration.restart_pod("test-pod", "default")

        assert result["success"] is False
        assert "Destructive operations are disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_restart_pod_enabled(self, k8s_integration, monkeypatch):
        """Test restart pod when destructive operations are enabled."""
        k8s_integration.enable_destructive = True

        # Mock describe pod to show it's controlled
        mock_describe = "Controlled By: ReplicaSet/test-rs"
        with patch.object(k8s_integration, 'describe_pod',
                         return_value={"success": True, "description": mock_describe}):
            with patch.object(k8s_integration, '_execute_k8s_command',
                             return_value={"success": True, "output": "pod deleted"}):
                result = await k8s_integration.restart_pod("test-pod", "default")

        assert result["success"] is True
        assert "deleted" in result["message"]

    @pytest.mark.asyncio
    async def test_get_service_status(self, k8s_integration):
        """Test getting service status."""
        mock_service = '''
        {
            "spec": {
                "type": "ClusterIP",
                "clusterIP": "10.0.0.1",
                "ports": [{"port": 80, "targetPort": 8080}],
                "selector": {"app": "test"}
            }
        }
        '''
        mock_endpoints = '''
        {
            "subsets": [{
                "addresses": [{"ip": "10.1.0.1", "targetRef": {"name": "test-pod-1"}}]
            }]
        }
        '''

        with patch.object(k8s_integration, '_execute_k8s_command') as mock_exec:
            mock_exec.side_effect = [
                {"success": True, "output": mock_service},
                {"success": True, "output": mock_endpoints}
            ]
            result = await k8s_integration.get_service_status("test-service", "default")

        assert result["success"] is True
        assert result["service"]["healthy"] is True
        assert result["service"]["endpoint_count"] == 1

    @pytest.mark.asyncio
    async def test_safety_checks(self, k8s_integration):
        """Test safety mechanisms for destructive operations."""
        # Test dangerous kubectl commands are blocked
        result = await k8s_integration.execute_kubectl_command("delete pod test-pod")
        assert result["success"] is False
        assert "restricted keywords" in result["error"]

        # Test non-dangerous commands work
        with patch.object(k8s_integration, '_execute_k8s_command',
                         return_value={"success": True, "output": "pod list"}):
            result = await k8s_integration.execute_kubectl_command("get pods")
        assert result["success"] is True


class TestKubernetesResolver:
    """Test Kubernetes resolution strategies."""

    @pytest.fixture
    def k8s_resolver(self):
        """Create a Kubernetes resolver with mocked integration."""
        mock_k8s = Mock(spec=KubernetesMCPIntegration)
        return KubernetesResolver(mock_k8s)

    @pytest.mark.asyncio
    async def test_resolve_pod_crash_oom(self, k8s_resolver):
        """Test resolution for OOM killed pods."""
        context = {
            "pod_logs": {"logs": "java.lang.OutOfMemoryError: Java heap space"},
            "pod_events": {"events": [{"message": "OOMKilled", "reason": "OOMKilling"}]}
        }

        actions = await k8s_resolver.resolve_pod_crash("test-pod", "default", context)

        # Should suggest increasing memory as first action
        assert len(actions) > 0
        assert actions[0].action_type == "increase_memory_limit"
        assert actions[0].confidence >= 0.8

    @pytest.mark.asyncio
    async def test_resolve_pod_crash_config(self, k8s_resolver):
        """Test resolution for configuration issues."""
        context = {
            "pod_logs": {"logs": "Error: config file not found at /etc/app/config.yaml"},
            "pod_events": {"events": []}
        }

        actions = await k8s_resolver.resolve_pod_crash("test-pod", "default", context)

        # Should suggest checking configmaps/secrets
        config_actions = [a for a in actions if a.action_type == "check_configmaps_secrets"]
        assert len(config_actions) > 0

    @pytest.mark.asyncio
    async def test_resolve_image_pull_error(self, k8s_resolver):
        """Test resolution for image pull errors."""
        context = {
            "pod_events": {
                "events": [{
                    "message": 'Failed to pull image "myregistry.io/app:v1.2.3"',
                    "reason": "Failed"
                }]
            }
        }

        actions = await k8s_resolver.resolve_image_pull_error("test-pod", "default", context)

        # Should suggest verifying image and credentials
        assert any(a.action_type == "verify_image_pull_secret" for a in actions)
        assert any(a.action_type == "verify_image_exists" for a in actions)

    @pytest.mark.asyncio
    async def test_confidence_scoring(self, k8s_resolver):
        """Test that actions are sorted by confidence."""
        context = {
            "pod_logs": {"logs": "OOMKilled and config error"},
            "pod_events": {"events": [{"message": "OOMKilled"}]}
        }

        actions = await k8s_resolver.resolve_pod_crash("test-pod", "default", context)

        # Actions should be sorted by confidence (highest first)
        confidences = [a.confidence for a in actions]
        assert confidences == sorted(confidences, reverse=True)


class TestOncallAgentK8sIntegration:
    """Test the main agent's Kubernetes alert handling."""

    @pytest.fixture
    def mock_agent(self, monkeypatch):
        """Create an agent with mocked dependencies."""
        mock_config = Mock(
            anthropic_api_key="test-key",
            claude_model="claude-3",
            get=lambda k, d=None: "true" if k == "K8S_ENABLED" else d
        )
        monkeypatch.setattr("src.oncall_agent.config.get_config", lambda: mock_config)

        # Mock Anthropic client
        mock_anthropic = Mock()
        monkeypatch.setattr("src.oncall_agent.agent.AsyncAnthropic", lambda **kwargs: mock_anthropic)

        # Mock K8s integration
        with patch("src.oncall_agent.agent.KubernetesMCPIntegration"):
            agent = OncallAgent()

        return agent

    def test_k8s_alert_detection(self, mock_agent):
        """Test detection of Kubernetes alert types."""
        test_cases = [
            ("Pod api-server is in CrashLoopBackOff", "pod_crash"),
            ("Failed to pull image myapp:latest - ImagePullBackOff", "image_pull"),
            ("Memory usage above threshold for deployment web-app", "high_memory"),
            ("CPU usage exceeded 90% on node-1", "high_cpu"),
            ("Service frontend-svc is down and not responding", "service_down"),
            ("Deployment backend-api failed to roll out", "deployment_failed"),
            ("Node worker-1 is NotReady", "node_issue"),
            ("Regular alert without k8s keywords", None)
        ]

        for description, expected_type in test_cases:
            detected = mock_agent._detect_k8s_alert_type(description)
            assert detected == expected_type, f"Failed for: {description}"

    @pytest.mark.asyncio
    async def test_handle_k8s_alert(self, mock_agent):
        """Test handling of a Kubernetes alert."""
        # Create a mock K8s integration
        mock_k8s = AsyncMock()
        mock_k8s.get_pod_logs.return_value = {"logs": "Error: OOMKilled"}
        mock_k8s.get_pod_events.return_value = {"events": [{"message": "OOMKilled"}]}
        mock_k8s.describe_pod.return_value = {"description": "Pod details"}
        mock_agent.mcp_integrations["kubernetes"] = mock_k8s

        # Mock Claude response
        mock_response = Mock()
        mock_response.content = [Mock(text="Analysis: Pod is experiencing memory issues")]
        mock_agent.anthropic_client.messages.create = AsyncMock(return_value=mock_response)

        # Create a K8s alert
        alert = PagerAlert(
            alert_id="K8S-001",
            severity="high",
            service_name="api-server",
            description="Pod api-server-abc123 is in CrashLoopBackOff",
            timestamp=datetime.utcnow().isoformat(),
            metadata={"pod_name": "api-server-abc123", "namespace": "production"}
        )

        result = await mock_agent.handle_pager_alert(alert)

        assert result["status"] == "analyzed"
        assert result["k8s_alert_type"] == "pod_crash"
        assert "k8s_context" in result
        assert "automated_actions" in result["k8s_context"]

        # Verify K8s context was gathered
        mock_k8s.get_pod_logs.assert_called_once()
        mock_k8s.get_pod_events.assert_called_once()
        mock_k8s.describe_pod.assert_called_once()
