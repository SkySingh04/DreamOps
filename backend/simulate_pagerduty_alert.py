#!/usr/bin/env python3
"""
PagerDuty Alert Simulation Script for Oncall Agent Testing

This script simulates PagerDuty alerts and tests the complete flow:
1. Trigger alerts in EKS to cause real issues
2. Simulate PagerDuty webhook notification
3. Run oncall agent with GitHub MCP integration
4. Verify AI analysis and response

Usage:
    python3 simulate_pagerduty_alert.py [scenario] [--real-pagerduty]

Scenarios:
    - pod_crash: Simulate pod CrashLoopBackOff
    - oom_kill: Simulate Out of Memory kill
    - image_pull: Simulate ImagePullBackOff error
    - cpu_throttle: Simulate CPU throttling
    - service_down: Simulate service unavailability
    - all: Run all scenarios sequentially

Options:
    --real-pagerduty: Send actual alerts to PagerDuty (requires API key)
    --github-integration: Test with GitHub MCP server integration
    --notion-integration: Test with Notion integration
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

# Add the src directory to the path so we can import the agent modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oncall_agent.agent import OncallAgent, PagerAlert
from oncall_agent.mcp_integrations.github_mcp import GitHubMCPIntegration
from oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration
from oncall_agent.utils import setup_logging


class PagerDutySimulator:
    """Simulates PagerDuty alerts and webhooks for testing."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.pagerduty_api_key = config.get("pagerduty_api_key", "")
        self.pagerduty_service_key = config.get("pagerduty_service_key", "")
        self.use_real_pagerduty = config.get("use_real_pagerduty", False)

    def trigger_real_pagerduty_alert(self, alert_data: dict[str, Any]) -> dict[str, Any]:
        """Send a real alert to PagerDuty using Events API v2."""
        if not self.use_real_pagerduty or not self.pagerduty_service_key:
            self.logger.info("Skipping real PagerDuty alert (not configured or disabled)")
            return {"status": "skipped", "reason": "Real PagerDuty not configured"}

        try:
            # PagerDuty Events API v2 endpoint
            url = "https://events.pagerduty.com/v2/enqueue"

            payload = {
                "routing_key": self.pagerduty_service_key,
                "event_action": "trigger",
                "dedup_key": alert_data.get("alert_id", f"alert-{int(time.time())}"),
                "payload": {
                    "summary": alert_data.get("description", "Alert from Oncall Agent Test"),
                    "severity": alert_data.get("severity", "critical"),
                    "source": alert_data.get("service_name", "oncall-agent-test"),
                    "component": "kubernetes",
                    "group": "oncall-test",
                    "class": alert_data.get("alert_type", "infrastructure"),
                    "custom_details": alert_data.get("metadata", {})
                },
                "client": "oncall-agent-simulator",
                "client_url": "https://github.com/yourusername/oncall-agent"
            }

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            self.logger.info(f"✅ PagerDuty alert triggered: {result.get('dedup_key')}")
            return {
                "status": "success",
                "dedup_key": result.get("dedup_key"),
                "message": result.get("message", "Alert sent to PagerDuty")
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to send PagerDuty alert: {e}")
            return {"status": "error", "error": str(e)}

    def simulate_webhook_payload(self, alert_data: dict[str, Any]) -> dict[str, Any]:
        """Simulate a PagerDuty webhook payload that would be received."""
        return {
            "messages": [
                {
                    "id": f"webhook-{int(time.time())}",
                    "created_on": datetime.now(UTC).isoformat(),
                    "type": "incident.trigger",
                    "data": {
                        "incident": {
                            "id": alert_data.get("alert_id", f"incident-{int(time.time())}"),
                            "incident_number": int(time.time()) % 10000,
                            "created_at": datetime.now(UTC).isoformat(),
                            "status": "triggered",
                            "incident_key": alert_data.get("alert_id"),
                            "service": {
                                "name": alert_data.get("service_name", "unknown-service"),
                                "description": f"Service for {alert_data.get('service_name')}"
                            },
                            "title": alert_data.get("description", "Alert from simulation"),
                            "urgency": "high" if alert_data.get("severity") == "critical" else "low",
                            "assignments": [],
                            "escalation_policy": {
                                "name": "Default Escalation Policy",
                                "id": "escalation-001"
                            }
                        }
                    }
                }
            ]
        }


class EKSAlertSimulator:
    """Simulates various EKS/Kubernetes issues that would trigger alerts."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.namespace = "oncall-test-apps"

    def check_kubectl_available(self) -> bool:
        """Check if kubectl is available and configured."""
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def apply_broken_manifest(self, scenario: str) -> dict[str, Any]:
        """Apply a broken Kubernetes manifest to simulate issues."""
        if not self.check_kubectl_available():
            self.logger.warning("kubectl not available - simulating EKS issue instead")
            return self._simulate_issue_without_kubectl(scenario)

        manifests = {
            "pod_crash": self._get_crashloop_manifest(),
            "oom_kill": self._get_oom_manifest(),
            "image_pull": self._get_imagepull_manifest(),
            "cpu_throttle": self._get_cpu_throttle_manifest(),
            "service_down": self._get_service_down_manifest()
        }

        if scenario not in manifests:
            raise ValueError(f"Unknown scenario: {scenario}")

        try:
            # Create namespace if it doesn't exist
            subprocess.run([
                "kubectl", "create", "namespace", self.namespace, "--dry-run=client", "-o", "yaml"
            ], capture_output=True)
            subprocess.run([
                "kubectl", "apply", "-f", "-"
            ], input=f"apiVersion: v1\nkind: Namespace\nmetadata:\n  name: {self.namespace}",
               text=True, capture_output=True)

            # Apply the broken manifest
            result = subprocess.run([
                "kubectl", "apply", "-f", "-"
            ], input=manifests[scenario], text=True, capture_output=True, timeout=30)

            if result.returncode == 0:
                self.logger.info(f"✅ Applied {scenario} manifest to EKS cluster")
                return {"status": "success", "output": result.stdout}
            else:
                self.logger.error(f"❌ Failed to apply manifest: {result.stderr}")
                return {"status": "error", "error": result.stderr}

        except Exception as e:
            self.logger.error(f"❌ Error applying manifest: {e}")
            return {"status": "error", "error": str(e)}

    def _simulate_issue_without_kubectl(self, scenario: str) -> dict[str, Any]:
        """Simulate an issue when kubectl is not available."""
        self.logger.info(f"Simulating {scenario} issue (kubectl not available)")
        return {
            "status": "simulated",
            "message": f"Simulated {scenario} issue - kubectl not available for real deployment"
        }

    def _get_crashloop_manifest(self) -> str:
        """Get manifest for CrashLoopBackOff simulation."""
        return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crashloop-test-app
  namespace: oncall-test-apps
  labels:
    app: crashloop-test
    scenario: pod_crash
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crashloop-test
  template:
    metadata:
      labels:
        app: crashloop-test
    spec:
      containers:
      - name: crashloop-container
        image: busybox:1.35
        command: ["/bin/sh"]
        args: ["-c", "echo 'Starting application...'; sleep 5; echo 'Configuration file not found!'; exit 1"]
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
"""

    def _get_oom_manifest(self) -> str:
        """Get manifest for OOM simulation."""
        return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-test-app
  namespace: oncall-test-apps
  labels:
    app: oom-test
    scenario: oom_kill
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom-test
  template:
    metadata:
      labels:
        app: oom-test
    spec:
      containers:
      - name: memory-hog
        image: python:3.9-slim
        command: ["/bin/sh"]
        args: ["-c", "python3 -c 'data=[]; [data.append(' ' * 10**6) for _ in range(1000)]'"]
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"  # Very low limit to trigger OOM
            cpu: "200m"
"""

    def _get_imagepull_manifest(self) -> str:
        """Get manifest for ImagePullBackOff simulation."""
        return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imagepull-test-app
  namespace: oncall-test-apps
  labels:
    app: imagepull-test
    scenario: image_pull
spec:
  replicas: 1
  selector:
    matchLabels:
      app: imagepull-test
  template:
    metadata:
      labels:
        app: imagepull-test
    spec:
      containers:
      - name: bad-image
        image: nonexistent-registry.example.com/fake-image:latest
        imagePullPolicy: Always
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
"""

    def _get_cpu_throttle_manifest(self) -> str:
        """Get manifest for CPU throttling simulation."""
        return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cpu-throttle-test-app
  namespace: oncall-test-apps
  labels:
    app: cpu-throttle-test
    scenario: cpu_throttle
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cpu-throttle-test
  template:
    metadata:
      labels:
        app: cpu-throttle-test
    spec:
      containers:
      - name: cpu-intensive
        image: busybox:1.35
        command: ["/bin/sh"]
        args: ["-c", "while true; do echo 'CPU intensive task...'; done"]
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "150m"  # Low limit to cause throttling
"""

    def _get_service_down_manifest(self) -> str:
        """Get manifest for service down simulation."""
        return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: service-down-test-app
  namespace: oncall-test-apps
  labels:
    app: service-down-test
    scenario: service_down
spec:
  replicas: 0  # No replicas = service down
  selector:
    matchLabels:
      app: service-down-test
  template:
    metadata:
      labels:
        app: service-down-test
    spec:
      containers:
      - name: app
        image: nginx:1.21
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: service-down-test-svc
  namespace: oncall-test-apps
  labels:
    app: service-down-test
spec:
  selector:
    app: service-down-test
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
"""


async def test_complete_alert_flow(scenario: str, config: dict[str, Any]) -> dict[str, Any]:
    """Test the complete alert flow from simulation to AI response."""
    logger = logging.getLogger(__name__)

    logger.info(f"🧪 Testing complete alert flow for scenario: {scenario}")

    # Step 1: Simulate EKS issue
    logger.info("📦 Step 1: Simulating EKS issue...")
    eks_simulator = EKSAlertSimulator()
    eks_result = eks_simulator.apply_broken_manifest(scenario)

    if eks_result["status"] == "error":
        logger.warning(f"EKS simulation failed: {eks_result['error']}")

    # Step 2: Create alert data based on scenario
    alert_data = get_scenario_alert_data(scenario)

    # Step 3: Optionally send real PagerDuty alert
    logger.info("📟 Step 2: Optionally triggering PagerDuty alert...")
    pd_simulator = PagerDutySimulator(config)
    pd_result = pd_simulator.trigger_real_pagerduty_alert(alert_data)

    # Step 4: Simulate webhook payload
    webhook_payload = pd_simulator.simulate_webhook_payload(alert_data)

    # Step 5: Initialize and run oncall agent
    logger.info("🤖 Step 3: Running oncall agent analysis...")
    agent_result = await run_oncall_agent_with_integrations(alert_data, config)

    # Step 6: Compile results
    results = {
        "scenario": scenario,
        "timestamp": datetime.now(UTC).isoformat(),
        "eks_simulation": eks_result,
        "pagerduty_alert": pd_result,
        "webhook_payload": webhook_payload,
        "agent_analysis": agent_result,
        "success": agent_result.get("status") == "success"
    }

    # Step 7: Display summary
    print_test_summary(results)

    return results


async def run_oncall_agent_with_integrations(alert_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Run the oncall agent with configured integrations."""
    logger = logging.getLogger(__name__)

    try:
        # Create PagerAlert from alert data
        alert = PagerAlert(
            alert_id=alert_data["alert_id"],
            severity=alert_data["severity"],
            service_name=alert_data["service_name"],
            description=alert_data["description"],
            timestamp=alert_data["timestamp"],
            metadata=alert_data.get("metadata", {})
        )

        # Initialize agent
        agent = OncallAgent()

        # Register GitHub MCP integration if enabled
        if config.get("github_integration", False):
            logger.info("🔗 Registering GitHub MCP integration...")
            try:
                github_config = {
                    "github_token": config.get("github_token", ""),
                    "mcp_server_path": config.get("github_mcp_server_path", "../github-mcp-server/github-mcp-server"),
                    "server_host": "localhost",
                    "server_port": 8081
                }
                github_integration = GitHubMCPIntegration(github_config)
                agent.register_mcp_integration("github", github_integration)
                logger.info("✅ GitHub MCP integration registered")
            except Exception as e:
                logger.warning(f"⚠️ GitHub MCP integration failed: {e}")

        # Register Notion integration if enabled
        if config.get("notion_integration", False):
            logger.info("📝 Registering Notion integration...")
            try:
                notion_config = {
                    "notion_token": config.get("notion_token", ""),
                    "database_id": config.get("notion_database_id", ""),
                    "notion_version": config.get("notion_version", "2022-06-28")
                }
                notion_integration = NotionDirectIntegration(notion_config)
                agent.register_mcp_integration("notion", notion_integration)
                logger.info("✅ Notion integration registered")
            except Exception as e:
                logger.warning(f"⚠️ Notion integration failed: {e}")

        # Connect integrations
        await agent.connect_integrations()

        # Process the alert
        logger.info("⚡ Processing alert with AI agent...")
        result = await agent.handle_pager_alert(alert)

        # Clean up
        await agent.shutdown()

        return {
            "status": "success",
            "alert_id": alert.alert_id,
            "analysis": result.get("analysis", ""),
            "k8s_alert_type": result.get("k8s_alert_type"),
            "integrations_used": result.get("available_integrations", []),
            "suggested_actions": result.get("suggested_actions", []),
            "raw_result": result
        }

    except Exception as e:
        logger.error(f"❌ Agent processing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "alert_id": alert_data.get("alert_id", "unknown")
        }


def get_scenario_alert_data(scenario: str) -> dict[str, Any]:
    """Get alert data for a specific scenario."""
    base_timestamp = datetime.now(UTC).isoformat()

    scenarios = {
        "pod_crash": {
            "alert_id": f"K8S-CRASH-{int(time.time())}",
            "severity": "critical",
            "service_name": "crashloop-test-app",
            "description": "Pod crashloop-test-app is in CrashLoopBackOff state - Configuration file not found",
            "timestamp": base_timestamp,
            "alert_type": "pod_crash",
            "metadata": {
                "pod_name": "crashloop-test-app-xxx",
                "namespace": "oncall-test-apps",
                "deployment_name": "crashloop-test-app",
                "restart_count": 5,
                "last_restart": "30 seconds ago",
                "cluster": "oncall-agent-eks"
            }
        },
        "oom_kill": {
            "alert_id": f"K8S-OOM-{int(time.time())}",
            "severity": "high",
            "service_name": "oom-test-app",
            "description": "Pod oom-test-app killed due to OOMKilled - memory limit exceeded",
            "timestamp": base_timestamp,
            "alert_type": "oom_kill",
            "metadata": {
                "pod_name": "oom-test-app-xxx",
                "namespace": "oncall-test-apps",
                "deployment_name": "oom-test-app",
                "memory_limit": "128Mi",
                "memory_used": "256Mi",
                "cluster": "oncall-agent-eks"
            }
        },
        "image_pull": {
            "alert_id": f"K8S-IMG-{int(time.time())}",
            "severity": "medium",
            "service_name": "imagepull-test-app",
            "description": "Pod imagepull-test-app in ImagePullBackOff state - cannot pull image",
            "timestamp": base_timestamp,
            "alert_type": "image_pull",
            "metadata": {
                "pod_name": "imagepull-test-app-xxx",
                "namespace": "oncall-test-apps",
                "image": "nonexistent-registry.example.com/fake-image:latest",
                "pull_error": "repository does not exist",
                "cluster": "oncall-agent-eks"
            }
        },
        "cpu_throttle": {
            "alert_id": f"K8S-CPU-{int(time.time())}",
            "severity": "medium",
            "service_name": "cpu-throttle-test-app",
            "description": "Pod cpu-throttle-test-app experiencing CPU throttling - high CPU usage",
            "timestamp": base_timestamp,
            "alert_type": "cpu_throttle",
            "metadata": {
                "pod_name": "cpu-throttle-test-app-xxx",
                "namespace": "oncall-test-apps",
                "cpu_limit": "150m",
                "cpu_usage": "100%",
                "throttle_percentage": "80%",
                "cluster": "oncall-agent-eks"
            }
        },
        "service_down": {
            "alert_id": f"K8S-SVC-{int(time.time())}",
            "severity": "critical",
            "service_name": "service-down-test-svc",
            "description": "Service service-down-test-svc has no healthy endpoints - service unavailable",
            "timestamp": base_timestamp,
            "alert_type": "service_down",
            "metadata": {
                "service_name": "service-down-test-svc",
                "namespace": "oncall-test-apps",
                "endpoint_count": 0,
                "target_pods": 0,
                "last_healthy": "5 minutes ago",
                "cluster": "oncall-agent-eks"
            }
        }
    }

    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario}. Available: {list(scenarios.keys())}")

    return scenarios[scenario]


def print_test_summary(results: dict[str, Any]) -> None:
    """Print a summary of the test results."""
    print("\n" + "="*80)
    print("🧪 PAGERDUTY ALERT SIMULATION TEST SUMMARY")
    print("="*80)
    print(f"📋 Scenario: {results['scenario']}")
    print(f"⏰ Timestamp: {results['timestamp']}")
    print(f"✅ Overall Success: {results['success']}")
    print()

    # EKS Simulation Results
    eks = results['eks_simulation']
    print(f"📦 EKS Simulation: {eks['status']}")
    if eks['status'] == 'error':
        print(f"   ❌ Error: {eks['error']}")
    elif eks['status'] == 'simulated':
        print(f"   ⚠️  {eks['message']}")
    else:
        print("   ✅ Successfully applied manifest")
    print()

    # PagerDuty Results
    pd = results['pagerduty_alert']
    print(f"📟 PagerDuty Alert: {pd['status']}")
    if pd['status'] == 'success':
        print(f"   ✅ Alert triggered: {pd['dedup_key']}")
    elif pd['status'] == 'skipped':
        print(f"   ⚠️  {pd['reason']}")
    else:
        print(f"   ❌ Error: {pd.get('error', 'Unknown error')}")
    print()

    # Agent Analysis Results
    agent = results['agent_analysis']
    print(f"🤖 AI Agent Analysis: {agent['status']}")
    if agent['status'] == 'success':
        print(f"   🔍 Alert Type: {agent.get('k8s_alert_type', 'Unknown')}")
        print(f"   🔗 Integrations: {', '.join(agent.get('integrations_used', []))}")
        print(f"   ⚡ Suggested Actions: {len(agent.get('suggested_actions', []))}")
        if agent.get('analysis'):
            print("   📊 Analysis Preview:")
            lines = agent['analysis'].split('\n')[:3]
            for line in lines:
                if line.strip():
                    print(f"      {line[:100]}...")
    else:
        print(f"   ❌ Error: {agent.get('error', 'Unknown error')}")

    print("="*80)


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="PagerDuty Alert Simulation for Oncall Agent")
    parser.add_argument(
        "scenario",
        nargs="?",
        default="pod_crash",
        choices=["pod_crash", "oom_kill", "image_pull", "cpu_throttle", "service_down", "all"],
        help="Scenario to simulate"
    )
    parser.add_argument(
        "--real-pagerduty",
        action="store_true",
        help="Send actual alerts to PagerDuty (requires API key)"
    )
    parser.add_argument(
        "--github-integration",
        action="store_true",
        help="Test with GitHub MCP server integration"
    )
    parser.add_argument(
        "--notion-integration",
        action="store_true",
        help="Test with Notion integration"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging(level=args.log_level)
    logger = logging.getLogger(__name__)

    # Load configuration
    config = {
        "use_real_pagerduty": args.real_pagerduty,
        "github_integration": args.github_integration,
        "notion_integration": args.notion_integration,
        "pagerduty_api_key": "",  # Set if using real PagerDuty
        "pagerduty_service_key": "",  # Set if using real PagerDuty
        "github_token": "",  # Set if using GitHub integration
        "github_mcp_server_path": "../github-mcp-server/github-mcp-server",
        "notion_token": "",  # Set if using Notion integration
        "notion_database_id": "",  # Set if using Notion integration
        "notion_version": "2022-06-28"
    }

    logger.info("🚀 Starting PagerDuty Alert Simulation")

    if args.scenario == "all":
        scenarios = ["pod_crash", "oom_kill", "image_pull", "cpu_throttle", "service_down"]
        results = []

        for scenario in scenarios:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing scenario: {scenario}")
            logger.info(f"{'='*50}")

            result = await test_complete_alert_flow(scenario, config)
            results.append(result)

            # Wait between scenarios
            await asyncio.sleep(5)

        # Print overall summary
        print("\n" + "="*80)
        print("🎯 OVERALL TEST SUMMARY")
        print("="*80)
        successful = [r for r in results if r['success']]
        print(f"Total scenarios tested: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(results) - len(successful)}")
        print("="*80)

    else:
        await test_complete_alert_flow(args.scenario, config)

    logger.info("✅ PagerDuty Alert Simulation completed")


if __name__ == "__main__":
    asyncio.run(main())
