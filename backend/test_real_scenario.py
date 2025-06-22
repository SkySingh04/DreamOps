#!/usr/bin/env python3
"""Test real Kubernetes scenario with actual pod names."""

import asyncio
import subprocess
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oncall_agent.agent import PagerAlert
from oncall_agent.agent_enhanced import EnhancedOncallAgent
from oncall_agent.api.schemas import AIMode
from oncall_agent.utils import setup_logging


async def test_real_oom_scenario():
    """Test with real OOM killed pod."""
    setup_logging(level="INFO")

    # Get actual pod name
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "oncall-test-apps", "-o", "name"],
        capture_output=True,
        text=True
    )

    oom_pod = None
    for line in result.stdout.strip().split('\n'):
        if "oom-test-app" in line:
            oom_pod = line.replace("pod/", "")
            break

    if not oom_pod:
        print("No OOM pod found. Creating one...")
        subprocess.run([
            "kubectl", "apply", "-f", "-"
        ], input="""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-test-app
  namespace: oncall-test-apps
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom-test-app
  template:
    metadata:
      labels:
        app: oom-test-app
    spec:
      containers:
      - name: oom-test-app
        image: polinux/stress
        command: ["stress", "--vm", "1", "--vm-bytes", "256M", "--vm-hang", "1"]
        resources:
          limits:
            memory: "128Mi"
          requests:
            memory: "64Mi"
""", text=True)
        await asyncio.sleep(5)
        # Get the new pod name
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", "oncall-test-apps", "-o", "name"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.strip().split('\n'):
            if "oom-test-app" in line:
                oom_pod = line.replace("pod/", "")
                break

    print(f"Testing with pod: {oom_pod}")

    # Create alert
    alert = PagerAlert(
        alert_id="K8S-OOM-REAL-001",
        service_name="oom-test-app",
        severity="high",
        description=f"Pod {oom_pod} killed due to OOMKilled - memory limit exceeded",
        timestamp="2025-06-22T00:00:00Z",
        metadata={
            "pod_name": oom_pod,
            "namespace": "oncall-test-apps",
            "memory_limit": "128Mi",
            "memory_usage": "256Mi",
            "cluster": "oncall-agent-eks",
            "deployment_name": "oom-test-app"
        }
    )

    # Initialize enhanced agent in YOLO mode
    agent = EnhancedOncallAgent(ai_mode=AIMode.YOLO)
    await agent.connect_integrations()

    print("\n🚀 Running enhanced agent in YOLO mode...")
    result = await agent.handle_pager_alert(alert)

    print("\n📊 EXECUTION RESULTS:")
    if "execution_results" in result:
        exec_results = result["execution_results"]
        print(f"✅ Actions executed: {exec_results.get('actions_executed', 0)}")
        print(f"✅ Successful: {exec_results.get('actions_successful', 0)}")
        print(f"❌ Failed: {exec_results.get('actions_failed', 0)}")

        print("\n📝 Execution Details:")
        for detail in exec_results.get("execution_details", []):
            action = detail.get("action", {})
            print(f"\n  Action: {action.get('action_type')}")
            print(f"  Description: {action.get('description')}")
            print(f"  Executed: {detail.get('executed', False)}")
            if detail.get("result"):
                print(f"  Success: {detail['result'].get('success', False)}")
                if detail['result'].get('command'):
                    print(f"  Command: {detail['result']['command']}")
                if detail['result'].get('error'):
                    print(f"  Error: {detail['result']['error']}")

    # Check pod status after remediation
    print("\n🔍 Checking pod status after remediation...")
    await asyncio.sleep(3)
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "oncall-test-apps", "-l", "app=oom-test-app"],
        capture_output=True,
        text=True
    )
    print(result.stdout)

    await agent.disconnect_integrations()


if __name__ == "__main__":
    asyncio.run(test_real_oom_scenario())
