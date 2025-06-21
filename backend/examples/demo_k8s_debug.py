#!/usr/bin/env python3
"""Demo script showing how the agent debugs a Kubernetes issue step by step."""

import asyncio
import logging
from datetime import UTC, datetime

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.strategies.kubernetes_resolver import KubernetesResolver
from src.oncall_agent.utils import setup_logging


async def get_actual_pod_name():
    """Get the actual pod name from the cluster."""
    import subprocess
    result = subprocess.run(
        ["kubectl", "get", "pods", "-l", "app=payment-service", "-o", "jsonpath={.items[0].metadata.name}"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()


async def main():
    """Main demo showing agent's thinking process."""
    # Set up logging with more detail
    setup_logging(level="DEBUG")
    logger = logging.getLogger(__name__)

    print("\n" + "="*80)
    print("🤖 ONCALL AI AGENT - KUBERNETES DEBUGGING DEMO")
    print("="*80 + "\n")

    # Get actual pod name
    pod_name = await get_actual_pod_name()
    if not pod_name:
        logger.error("No payment-service pod found!")
        return

    print(f"📍 Found problematic pod: {pod_name}\n")

    # Initialize the agent
    print("🚀 Initializing AI Agent with Kubernetes integration...\n")
    agent = OncallAgent()

    # Connect integrations
    await agent.connect_integrations()

    # Create alert for the actual crashed pod
    alert = PagerAlert(
        alert_id="K8S-DEMO-001",
        severity="critical",
        service_name="payment-service",
        description=f"Pod {pod_name} is in CrashLoopBackOff state",
        timestamp=datetime.now(UTC).isoformat(),
        metadata={
            "pod_name": pod_name,
            "namespace": "default",
            "deployment_name": "payment-service",
            "cluster": "kind-oncall-test"
        }
    )

    print("🚨 ALERT RECEIVED:")
    print(f"   ID: {alert.alert_id}")
    print(f"   Service: {alert.service_name}")
    print(f"   Description: {alert.description}")
    print(f"   Pod: {pod_name}")
    print("\n" + "-"*60 + "\n")

    # Step 1: Agent detects K8s alert type
    print("🔍 STEP 1: DETECTING ALERT TYPE")
    alert_type = agent._detect_k8s_alert_type(alert.description)
    print(f"   ✓ Detected Kubernetes alert type: {alert_type}")
    print("\n" + "-"*60 + "\n")

    # Step 2: Gather K8s context
    print("📊 STEP 2: GATHERING KUBERNETES CONTEXT")
    print("   The agent is now querying the Kubernetes cluster...\n")

    if "kubernetes" in agent.mcp_integrations:
        k8s = agent.mcp_integrations["kubernetes"]

        # Get pod status
        print("   🔸 Checking pod status...")
        pods = await k8s.list_pods("default")
        for pod in pods.get("pods", []):
            if pod["name"] == pod_name:
                print(f"      Status: {pod['status']}")
                print(f"      Ready: {pod['ready']}")
                print(f"      Restarts: {pod['restarts']}")

        # Get pod logs
        print("\n   🔸 Fetching pod logs...")
        logs_result = await k8s.get_pod_logs(pod_name, "default", tail_lines=20)
        if logs_result.get("success"):
            logs = logs_result.get("logs", "")
            print("      Recent logs:")
            for line in logs.split('\n')[-10:]:  # Last 10 lines
                if line.strip():
                    print(f"      | {line}")

        # Get pod events
        print("\n   🔸 Checking pod events...")
        events_result = await k8s.get_pod_events(pod_name, "default")
        if events_result.get("success"):
            events = events_result.get("events", [])
            print(f"      Found {len(events)} events")
            for event in events[-3:]:  # Last 3 events
                print(f"      - {event.get('type')}: {event.get('reason')} - {event.get('message')}")

        # Get pod description
        print("\n   🔸 Getting pod description...")
        desc_result = await k8s.describe_pod(pod_name, "default")
        if desc_result.get("success"):
            desc = desc_result.get("description", "")
            # Extract key information
            if "Controlled By:" in desc:
                controller = desc.split("Controlled By:")[1].split('\n')[0].strip()
                print(f"      Controlled By: {controller}")

    print("\n" + "-"*60 + "\n")

    # Step 3: AI Analysis
    print("🧠 STEP 3: AI ANALYSIS")
    print("   Claude is analyzing the gathered context...\n")

    # Process the alert through the agent
    result = await agent.handle_pager_alert(alert)

    # Display K8s context findings
    if result.get("k8s_context"):
        context = result["k8s_context"]
        print("   📋 Context Summary:")
        print(f"      Alert Type: {context.get('alert_type')}")

        if "error" in context:
            print(f"      Error: {context['error']}")
        else:
            if "pod_logs" in context and context["pod_logs"].get("logs"):
                # Analyze logs for root cause
                logs = context["pod_logs"]["logs"]
                if "config" in logs.lower() and "not found" in logs.lower():
                    print("      ⚠️  Root Cause: Configuration file missing")
                elif "memory" in logs.lower():
                    print("      ⚠️  Root Cause: Memory issues detected")
                elif "connection" in logs.lower():
                    print("      ⚠️  Root Cause: Connection/dependency issues")

            if "automated_actions" in context:
                print(f"\n      🔧 Automated Actions Available: {len(context['automated_actions'])}")
                for action in context['automated_actions']:
                    print(f"         - {action['action']} (confidence: {action['confidence']})")
                    print(f"           Reason: {action['reason']}")

    print("\n" + "-"*60 + "\n")

    # Step 4: Resolution Strategy
    print("🛠️  STEP 4: RESOLUTION STRATEGY")

    if "kubernetes" in agent.mcp_integrations:
        resolver = KubernetesResolver(agent.mcp_integrations["kubernetes"])

        # Get resolution actions
        k8s_context = result.get("k8s_context", {})
        actions = await resolver.resolve_pod_crash(pod_name, "default", k8s_context)

        print("   Recommended actions (sorted by confidence):")
        for i, action in enumerate(actions[:3], 1):  # Top 3 actions
            print(f"\n   {i}. {action.description}")
            print(f"      Type: {action.action_type}")
            print(f"      Confidence: {action.confidence}")
            print(f"      Risk: {action.risk_level}")
            print(f"      Time: {action.estimated_time}")
            if action.prerequisites:
                print(f"      Prerequisites: {', '.join(action.prerequisites)}")

    print("\n" + "-"*60 + "\n")

    # Step 5: Show Claude's full analysis
    print("📝 STEP 5: COMPLETE AI ANALYSIS")
    print("\n" + "="*60)
    print("CLAUDE'S ANALYSIS:")
    print("="*60)
    if result.get('analysis'):
        print(result['analysis'])
    print("="*60 + "\n")

    # Step 6: Decision point
    print("🤔 STEP 6: DECISION POINT")
    if result.get("k8s_context", {}).get("automated_actions"):
        print("   The agent has identified automated remediation options.")
        print("   However, K8S_ENABLE_DESTRUCTIVE_OPERATIONS is set to 'false'")
        print("   In production with this setting enabled, the agent would:")
        print("   1. Execute high-confidence actions automatically")
        print("   2. Log all actions for audit trail")
        print("   3. Monitor the results")
        print("   4. Escalate if the issue persists")
    else:
        print("   Manual intervention required based on the analysis.")

    # Cleanup
    await agent.shutdown()

    print("\n" + "="*80)
    print("✅ DEMO COMPLETE")
    print("="*80 + "\n")

    # Show how to fix the issue
    print("💡 TO FIX THIS ISSUE:")
    print("   1. Create a ConfigMap with the required configuration:")
    print("      kubectl create configmap payment-config --from-literal=app.conf='db.host=localhost'")
    print("   2. Mount it in the deployment:")
    print("      kubectl set volume deployment/payment-service --add --name=config --mount-path=/config --configmap=payment-config")
    print("   3. The pod will automatically restart and should run successfully")
    print()


if __name__ == "__main__":
    asyncio.run(main())
