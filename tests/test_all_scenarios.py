#!/usr/bin/env python3
"""Test different Kubernetes failure scenarios with the Oncall Agent."""

import asyncio
from datetime import datetime, timezone
import sys

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging


async def test_scenario(scenario_name: str, alert: PagerAlert):
    """Test a specific scenario."""
    print(f"\n{'='*80}")
    print(f"🧪 TESTING SCENARIO: {scenario_name}")
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
                print(f"📊 Context gathered successfully")
                if ctx.get('automated_actions'):
                    print(f"🔧 Suggested actions: {len(ctx['automated_actions'])}")
                    for action in ctx['automated_actions']:
                        print(f"   - {action['action']} (confidence: {action['confidence']})")
    
    print(f"\n🤖 Claude's Analysis Summary:")
    print("-" * 40)
    # Print first 500 chars of analysis
    analysis = result.get('analysis', 'No analysis')[:500]
    print(analysis + "..." if len(result.get('analysis', '')) > 500 else analysis)
    
    await agent.shutdown()
    print(f"\n✅ Scenario complete\n")


async def main():
    """Run all test scenarios."""
    setup_logging(level="INFO")
    
    # Get scenario from command line or run all
    scenario = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    scenarios = {
        "config": PagerAlert(
            alert_id="TEST-001",
            severity="critical",
            service_name="app-service",
            description="Pod app-service-abc123 is in CrashLoopBackOff - configuration error",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "pod_name": "app-service-abc123",
                "namespace": "default",
                "restart_count": 5
            }
        ),
        
        "image": PagerAlert(
            alert_id="TEST-002",
            severity="high",
            service_name="bad-image-app",
            description="Pod bad-image-app-xyz789 - ImagePullBackOff: failed to pull image nonexistent/image:v1.0.0",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "pod_name": "bad-image-app-xyz789",
                "namespace": "default",
                "image": "nonexistent/image:v1.0.0"
            }
        ),
        
        "oom": PagerAlert(
            alert_id="TEST-003",
            severity="high",
            service_name="memory-hog",
            description="Pod memory-hog-def456 restarting - memory usage exceeded limits",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "pod_name": "memory-hog-def456",
                "namespace": "default",
                "deployment_name": "memory-hog",
                "memory_limit": "100Mi",
                "memory_usage": "150Mi"
            }
        ),
        
        "cpu": PagerAlert(
            alert_id="TEST-004",
            severity="medium",
            service_name="cpu-intensive-app",
            description="Deployment cpu-intensive-app - CPU usage above threshold (95%)",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "deployment_name": "cpu-intensive-app",
                "namespace": "production",
                "cpu_usage": "95%",
                "cpu_limit": "1000m"
            }
        ),
        
        "service": PagerAlert(
            alert_id="TEST-005",
            severity="critical",
            service_name="api-gateway",
            description="Service api-gateway is down - no healthy endpoints available",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "service_name": "api-gateway",
                "namespace": "default",
                "endpoint_count": 0
            }
        ),
        
        "deployment": PagerAlert(
            alert_id="TEST-006",
            severity="high",
            service_name="frontend",
            description="Deployment frontend-app failed - 0/3 replicas available",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "deployment_name": "frontend-app",
                "namespace": "default",
                "desired_replicas": 3,
                "available_replicas": 0
            }
        ),
        
        "node": PagerAlert(
            alert_id="TEST-007",
            severity="critical",
            service_name="cluster",
            description="Node worker-node-1 is NotReady - kubelet not responding",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "node_name": "worker-node-1",
                "condition": "NotReady",
                "reason": "KubeletNotResponding"
            }
        )
    }
    
    if scenario == "all":
        for name, alert in scenarios.items():
            await test_scenario(name, alert)
    elif scenario in scenarios:
        await test_scenario(scenario, scenarios[scenario])
    else:
        print(f"Unknown scenario: {scenario}")
        print(f"Available: {', '.join(scenarios.keys())} or 'all'")


if __name__ == "__main__":
    asyncio.run(main())