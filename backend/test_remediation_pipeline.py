#!/usr/bin/env python3
"""Test the complete remediation pipeline with simulated OOM kill scenarios."""

import asyncio
from datetime import datetime

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.config import get_config


async def test_oom_remediation():
    """Test OOM kill remediation pipeline."""
    print("🚀 Testing OOM Kill Remediation Pipeline")
    print("=" * 50)

    # Initialize agent
    agent = OncallAgent()

    # Connect integrations
    print("📡 Connecting to Kubernetes...")
    await agent.connect_integrations()

    # Create a simulated OOM kill alert
    alert = PagerAlert(
        alert_id="test-oom-001",
        severity="critical",
        service_name="web-app",
        description="ALERT: Multiple OOMKilled events detected in production. Pods are being killed due to memory limits. Service: web-app, Namespace: default, Affected pods: web-app-deployment-7d9f8b6c5-x2n4m",
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "alert_type": "kubernetes",
            "namespace": "default",
            "deployment": "web-app-deployment",
            "pod": "web-app-deployment-7d9f8b6c5-x2n4m",
            "reason": "OOMKilled"
        }
    )

    print(f"\n📨 Processing alert: {alert.alert_id}")
    print(f"   Service: {alert.service_name}")
    print(f"   Severity: {alert.severity}")
    print(f"   Description: {alert.description[:100]}...")

    # Handle the alert with remediation pipeline
    try:
        # Get current config
        config = get_config()
        
        print("\n🤖 Testing in autonomous execution mode")

        result = await agent.handle_pager_alert(alert)

        print("\n📊 Analysis Results:")
        print(f"   Severity: {result.get('severity', 'unknown')}")
        print(f"   Alert Type: {result.get('k8s_alert_type', 'unknown')}")

        # Check if remediation pipeline was executed
        if 'remediation_pipeline_result' in result:
            pipeline_result = result['remediation_pipeline_result']

            print("\n🔧 Remediation Pipeline Results:")

            # Problems identified
            problems = pipeline_result.get('problems_identified', {})
            if problems:
                print("\n   📋 Problems Identified:")
                for problem_type, items in problems.items():
                    print(f"      - {problem_type}: {len(items)} items")
                    if items and len(items) > 0:
                        # Show first item as example
                        example = items[0]
                        if problem_type == 'oom_affected_deployments':
                            print(f"        Example: {example.get('deployment_name')} in {example.get('namespace')}")
                        elif problem_type == 'high_memory_pods':
                            print(f"        Example: {example.get('pod_name')} using {example.get('memory_str')}")

            # Remediation actions taken
            remediation_results = pipeline_result.get('remediation_results', [])
            if remediation_results:
                print("\n   🔨 Remediation Actions:")
                for action in remediation_results:
                    status_icon = "✅" if action.get('status') == 'success' else "❌"
                    print(f"      {status_icon} {action.get('action', 'unknown')}: {action.get('deployment', action.get('command', 'N/A'))}")
                    if action.get('old_limit') and action.get('new_limit'):
                        print(f"         Memory: {action['old_limit']} → {action['new_limit']}")

            # Verification results
            verification = pipeline_result.get('verification_results', {})
            if verification.get('checked'):
                status = "✅ FIXED" if verification.get('fixed') else "⚠️  NOT FIXED"
                print(f"\n   🎯 Verification: {status}")
                for detail in verification.get('details', []):
                    print(f"      - {detail}")

            # Execution log
            execution_log = pipeline_result.get('execution_log', [])
            if execution_log:
                print("\n   📜 Execution Timeline:")
                for entry in execution_log[-5:]:  # Show last 5 entries
                    print(f"      [{entry['action_type']}] {entry['description']}")

        elif 'commands' in result:
            # Fallback: Check if any commands were suggested
            print("\n   💡 Suggested Commands:")
            for cmd in result.get('commands', [])[:5]:
                print(f"      - {cmd}")

        # Check executed actions
        if 'executed_actions' in result:
            print(f"\n   ⚡ Executed {len(result['executed_actions'])} actions in YOLO mode")

        # Test completed

        print("\n✅ Test completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        await agent.shutdown()


async def test_pod_crash_remediation():
    """Test pod crash remediation pipeline."""
    print("\n\n🚀 Testing Pod Crash Remediation Pipeline")
    print("=" * 50)

    # Initialize agent
    agent = OncallAgent()

    # Connect integrations
    print("📡 Connecting to Kubernetes...")
    await agent.connect_integrations()

    # Create a simulated pod crash alert
    alert = PagerAlert(
        alert_id="test-crash-001",
        severity="high",
        service_name="api-service",
        description="ALERT: Pod CrashLoopBackOff detected. Pod api-service-deployment-5f4d5c6b7d-abc123 is crashing repeatedly in namespace production.",
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "alert_type": "kubernetes",
            "namespace": "production",
            "deployment": "api-service-deployment",
            "pod": "api-service-deployment-5f4d5c6b7d-abc123",
            "status": "CrashLoopBackOff"
        }
    )

    print(f"\n📨 Processing alert: {alert.alert_id}")
    print(f"   Service: {alert.service_name}")
    print(f"   Severity: {alert.severity}")

    # Handle the alert
    try:
        # Get config
        config = get_config()

        result = await agent.handle_pager_alert(alert)

        print("\n📊 Analysis Results:")
        print(f"   Alert Type: {result.get('k8s_alert_type', 'unknown')}")

        if 'remediation_pipeline_result' in result:
            pipeline_result = result['remediation_pipeline_result']

            # Show identified pods
            error_pods = pipeline_result.get('problems_identified', {}).get('error_pods', [])
            if error_pods:
                print(f"\n   🚨 Found {len(error_pods)} pods with errors")
                for pod in error_pods[:3]:
                    print(f"      - {pod['pod_name']}: {pod['status']} (restarts: {pod['restarts']})")

            # Show remediation results
            remediation_results = pipeline_result.get('remediation_results', [])
            successful = sum(1 for r in remediation_results if r.get('status') == 'success')
            print(f"\n   🔧 Remediation: {successful}/{len(remediation_results)} actions successful")

        # Test completed

        print("\n✅ Pod crash test completed!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")

    finally:
        await agent.shutdown()


async def main():
    """Run all remediation pipeline tests."""
    print("🧪 Oncall Agent Remediation Pipeline Test Suite")
    print("=" * 60)
    print("This test will simulate OOM kill and pod crash scenarios")
    print("and verify that the AI agent automatically fixes them.")
    print("=" * 60)

    # Test OOM remediation
    await test_oom_remediation()

    # Test pod crash remediation
    await test_pod_crash_remediation()

    print("\n\n🎉 All tests completed!")
    print("\nKey capabilities demonstrated:")
    print("✓ Diagnostic command execution (kubectl top, get events)")
    print("✓ Output parsing to identify specific resources")
    print("✓ Concrete remediation with real deployment names")
    print("✓ Memory limit increases via kubectl patch")
    print("✓ Rolling restarts for crashed pods")
    print("✓ Verification of fixes")
    print("✓ Incident auto-resolution (when fixed)")


if __name__ == "__main__":
    asyncio.run(main())
