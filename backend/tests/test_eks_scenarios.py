#!/usr/bin/env python3
"""Test various EKS failure scenarios with the Oncall Agent."""

import asyncio
import sys
from datetime import UTC, datetime

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging


async def test_eks_scenario(scenario_name: str, alert: PagerAlert):
    """Test a specific EKS scenario."""
    print(f"\n{'='*80}")
    print(f"🧪 TESTING EKS SCENARIO: {scenario_name}")
    print(f"{'='*80}\n")

    # Initialize agent
    agent = OncallAgent()
    await agent.connect_integrations()

    # Process alert
    print(f"📨 Alert: {alert.description}\n")
    result = await agent.handle_pager_alert(alert)

    # Show results
    if result.get('k8s_alert_type'):
        print(f"✅ Detected K8s Issue Type: {result['k8s_alert_type']}")

        if result.get('k8s_context'):
            ctx = result['k8s_context']
            if 'error' not in ctx:
                print("📊 Context gathered from EKS cluster")
                if ctx.get('automated_actions'):
                    print(f"🔧 Suggested actions: {len(ctx['automated_actions'])}")
                    for action in ctx['automated_actions']:
                        print(f"   - {action['action']} (confidence: {action['confidence']})")

    print("\n🤖 Claude's Analysis Summary:")
    print("-" * 40)
    # Print first 800 chars of analysis
    analysis = result.get('analysis', 'No analysis')[:800]
    print(analysis + "..." if len(result.get('analysis', '')) > 800 else analysis)

    await agent.shutdown()
    print("\n✅ Scenario complete\n")


async def main():
    """Run EKS test scenarios."""
    setup_logging(level="INFO")

    # Get scenario from command line or run all
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"

    # EKS-specific test scenarios
    eks_scenarios = {
        "config-missing": PagerAlert(
            alert_id="EKS-001",
            severity="critical",
            service_name="config-missing-app",
            description="Pod config-missing-app-7d9f8b6c5-x2n4m is in CrashLoopBackOff state in namespace test-apps",
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "pod_name": "config-missing-app-7d9f8b6c5-x2n4m",
                "namespace": "test-apps",
                "deployment_name": "config-missing-app",
                "restart_count": 5,
                "cluster": "oncall-agent-eks"
            }
        ),

        "oom-kill": PagerAlert(
            alert_id="EKS-002",
            severity="high",
            service_name="memory-hog-app",
            description="Pod memory-hog-app-55b6f9cfb5-h5ftt restarting due to OOMKilled in namespace test-apps",
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "pod_name": "memory-hog-app-55b6f9cfb5-h5ftt",
                "namespace": "test-apps",
                "deployment_name": "memory-hog-app",
                "memory_limit": "100Mi",
                "memory_requested": "150Mi",
                "cluster": "oncall-agent-eks"
            }
        ),

        "image-pull": PagerAlert(
            alert_id="EKS-003",
            severity="high",
            service_name="bad-image-app",
            description="Pod bad-image-app-6d4b5c8f9-n3k8p - ImagePullBackOff: failed to pull image nonexistent/doesnotexist:v99.99.99",
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "pod_name": "bad-image-app-6d4b5c8f9-n3k8p",
                "namespace": "test-apps",
                "deployment_name": "bad-image-app",
                "image": "nonexistent/doesnotexist:v99.99.99",
                "cluster": "oncall-agent-eks"
            }
        ),

        "cpu-throttle": PagerAlert(
            alert_id="EKS-004",
            severity="medium",
            service_name="cpu-intensive-app",
            description="Deployment cpu-intensive-app - CPU usage above threshold (95%) in namespace test-apps",
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "deployment_name": "cpu-intensive-app",
                "namespace": "test-apps",
                "cpu_usage": "95%",
                "cpu_limit": "200m",
                "replicas": 2,
                "cluster": "oncall-agent-eks"
            }
        ),

        "health-check": PagerAlert(
            alert_id="EKS-005",
            severity="high",
            service_name="unhealthy-app",
            description="Pod unhealthy-app-8f6d4b7c9-k2m4n failing liveness probe - container will be restarted",
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "pod_name": "unhealthy-app-8f6d4b7c9-k2m4n",
                "namespace": "test-apps",
                "deployment_name": "unhealthy-app",
                "probe_type": "liveness",
                "probe_path": "/health",
                "failure_count": 3,
                "cluster": "oncall-agent-eks"
            }
        ),

        "node-pressure": PagerAlert(
            alert_id="EKS-006",
            severity="critical",
            service_name="cluster",
            description="Node ip-10-1-2-123.ec2.internal experiencing memory pressure - pods being evicted",
            timestamp=datetime.now(UTC).isoformat(),
            metadata={
                "node_name": "ip-10-1-2-123.ec2.internal",
                "condition": "MemoryPressure",
                "available_memory": "100Mi",
                "pods_evicted": 3,
                "cluster": "oncall-agent-eks"
            }
        )
    }

    if scenario == "all":
        for name, alert in eks_scenarios.items():
            await test_eks_scenario(name, alert)
    elif scenario in eks_scenarios:
        await test_eks_scenario(scenario, eks_scenarios[scenario])
    else:
        print(f"Unknown scenario: {scenario}")
        print(f"Available: {', '.join(eks_scenarios.keys())} or 'all'")
        print("\nExample usage:")
        print("  python test_eks_scenarios.py config-missing")
        print("  python test_eks_scenarios.py oom-kill")
        print("  python test_eks_scenarios.py all")


if __name__ == "__main__":
    print("🚀 EKS Test Scenarios for Oncall Agent")
    print("Make sure you have:")
    print("1. Deployed the EKS cluster (see infrastructure/eks/)")
    print("2. Deployed test apps (./infrastructure/eks/deploy-sample-apps.sh)")
    print("3. Updated .env with correct K8S_CONTEXT and K8S_NAMESPACE=test-apps")
    print("4. AWS credentials configured")

    asyncio.run(main())
