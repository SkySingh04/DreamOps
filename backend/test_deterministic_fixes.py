#!/usr/bin/env python3
"""Test deterministic fixes with real Kubernetes issues."""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oncall_agent.agent import PagerAlert
from oncall_agent.agent_enhanced import EnhancedOncallAgent
from oncall_agent.api.schemas import AIMode
from oncall_agent.utils import setup_logging


async def test_deterministic_fix(issue_number: int):
    """Test a specific deterministic fix."""
    setup_logging(level="INFO")

    # Inject the issue
    print(f"\n🔧 Injecting issue {issue_number}...")
    result = subprocess.run(["./fuck_kubernetes.sh", str(issue_number)], capture_output=True, text=True)
    print(result.stdout)

    # Wait for issue to manifest
    await asyncio.sleep(10)

    # Get pod status
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "oncall-test-apps", "-o", "wide"],
        capture_output=True,
        text=True
    )
    print("\n📊 Current pod status:")
    print(result.stdout)

    # Create appropriate alert based on issue type
    alerts = {
        1: PagerAlert(
            alert_id=f"K8S-OOM-TEST-{int(time.time())}",
            service_name="oom-app",
            severity="high",
            description="Pod oom-app killed due to OOMKilled - memory limit exceeded",
            timestamp="2025-06-22T00:00:00Z",
            metadata={
                "deployment_name": "oom-app",
                "namespace": "oncall-test-apps",
                "memory_limit": "128Mi",
                "memory_usage": "150Mi"
            }
        ),
        2: PagerAlert(
            alert_id=f"K8S-IMG-TEST-{int(time.time())}",
            service_name="bad-image-app",
            severity="medium",
            description="Pod bad-image-app in ImagePullBackOff state - cannot pull image",
            timestamp="2025-06-22T00:00:00Z",
            metadata={
                "deployment_name": "bad-image-app",
                "namespace": "oncall-test-apps",
                "image": "nonexistent-registry.invalid/fake-image:v999"
            }
        ),
        3: PagerAlert(
            alert_id=f"K8S-CRASH-TEST-{int(time.time())}",
            service_name="crashloop-app",
            severity="critical",
            description="Pod crashloop-app is in CrashLoopBackOff state",
            timestamp="2025-06-22T00:00:00Z",
            metadata={
                "deployment_name": "crashloop-app",
                "namespace": "oncall-test-apps"
            }
        ),
        4: PagerAlert(
            alert_id=f"K8S-LIMIT-TEST-{int(time.time())}",
            service_name="resource-limited-app",
            severity="medium",
            description="Pod resource-limited-app experiencing resource limits",
            timestamp="2025-06-22T00:00:00Z",
            metadata={
                "deployment_name": "resource-limited-app",
                "namespace": "oncall-test-apps"
            }
        ),
        5: PagerAlert(
            alert_id=f"K8S-SVC-TEST-{int(time.time())}",
            service_name="down-service",
            severity="critical",
            description="Service down-service has no healthy endpoints - service unavailable",
            timestamp="2025-06-22T00:00:00Z",
            metadata={
                "deployment_name": "down-service-app",
                "namespace": "oncall-test-apps",
                "service_name": "down-service"
            }
        )
    }

    alert = alerts.get(issue_number)
    if not alert:
        print(f"❌ No alert defined for issue {issue_number}")
        return

    # Initialize enhanced agent in YOLO mode
    agent = EnhancedOncallAgent(ai_mode=AIMode.YOLO)
    await agent.connect_integrations()

    print(f"\n🚀 Running enhanced agent in YOLO mode for issue {issue_number}...")
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
                if detail['result'].get('output'):
                    print(f"  Output: {detail['result']['output'][:200]}")

    # Wait for fix to apply
    await asyncio.sleep(5)

    # Check final status
    print("\n🔍 Checking final status...")
    result = subprocess.run(
        ["kubectl", "get", "deployments", "-n", "oncall-test-apps"],
        capture_output=True,
        text=True
    )
    print("Deployments:")
    print(result.stdout)

    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "oncall-test-apps"],
        capture_output=True,
        text=True
    )
    print("\nPods:")
    print(result.stdout)


async def test_all_issues():
    """Test all deterministic fixes."""
    for i in range(1, 6):
        print(f"\n{'='*80}")
        print(f"TESTING ISSUE {i}")
        print(f"{'='*80}")

        await test_deterministic_fix(i)

        # Clean up before next test
        print("\n🧹 Cleaning up...")
        subprocess.run(["./fuck_kubernetes.sh", "clean"], capture_output=True)
        await asyncio.sleep(5)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        issue_num = int(sys.argv[1])
        asyncio.run(test_deterministic_fix(issue_num))
    else:
        asyncio.run(test_all_issues())
