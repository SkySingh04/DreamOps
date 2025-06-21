#!/usr/bin/env python3
"""Example of handling Kubernetes incidents with the Oncall AI Agent.

This example demonstrates:
1. Handling a pod crash alert
2. Gathering Kubernetes context
3. Using AI to analyze the issue
4. Executing automated remediation
"""

import asyncio
import logging
from datetime import datetime

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.mcp_integrations.kubernetes import KubernetesMCPIntegration
from src.oncall_agent.strategies.kubernetes_resolver import KubernetesResolver
from src.oncall_agent.utils import setup_logging


async def simulate_pod_crash_incident():
    """Simulate handling a pod crash incident."""
    # Set up logging
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)

    logger.info("=== Kubernetes Incident Handler Example ===")

    # Initialize the agent
    logger.info("Initializing Oncall Agent with Kubernetes integration...")
    agent = OncallAgent()

    # Connect integrations
    await agent.connect_integrations()

    # Simulate a pod crash alert
    alert = PagerAlert(
        alert_id="K8S-CRASH-001",
        severity="high",
        service_name="payment-service",
        description="Pod payment-service-7d9f8b6c5-x2n4m is in CrashLoopBackOff state",
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "pod_name": "payment-service-7d9f8b6c5-x2n4m",
            "namespace": "production",
            "deployment_name": "payment-service",
            "restart_count": 5,
            "last_restart": "2 minutes ago"
        }
    )

    logger.info(f"\n📨 Received Alert: {alert.alert_id}")
    logger.info(f"   Service: {alert.service_name}")
    logger.info(f"   Description: {alert.description}")
    logger.info(f"   Metadata: {alert.metadata}")

    # Handle the alert
    logger.info("\n🤖 AI Agent analyzing the alert...")
    result = await agent.handle_pager_alert(alert)

    # Display analysis
    logger.info("\n📊 Alert Analysis Complete:")
    logger.info(f"   Status: {result['status']}")
    logger.info(f"   K8s Alert Type: {result.get('k8s_alert_type', 'Unknown')}")

    if result.get('k8s_context'):
        logger.info("\n🔍 Kubernetes Context Gathered:")
        context = result['k8s_context']

        if 'pod_logs' in context:
            logger.info("   Recent Pod Logs:")
            logs = context['pod_logs'].get('logs', '')
            for line in logs.split('\n')[-5:]:  # Last 5 lines
                if line.strip():
                    logger.info(f"     {line}")

        if 'pod_events' in context:
            logger.info("   Recent Pod Events:")
            for event in context['pod_events'].get('events', [])[-3:]:  # Last 3 events
                logger.info(f"     - {event.get('type')}: {event.get('message')}")

    logger.info("\n🧠 Claude AI Analysis:")
    analysis_lines = result['analysis'].split('\n')
    for line in analysis_lines[:10]:  # First 10 lines
        if line.strip():
            logger.info(f"   {line}")

    # Check for automated actions
    if result.get('suggested_actions'):
        logger.info("\n🛠️  Suggested Automated Actions:")
        for action in result['suggested_actions']:
            logger.info(f"   - {action['action']} (confidence: {action['confidence']})")
            logger.info(f"     Reason: {action['reason']}")

        # Execute high-confidence actions if enabled
        if agent.config.get("K8S_ENABLE_DESTRUCTIVE_OPERATIONS", "false").lower() == "true":
            k8s_integration = agent.mcp_integrations.get('kubernetes')
            if k8s_integration:
                resolver = KubernetesResolver(k8s_integration)

                for action in result['suggested_actions']:
                    if action['confidence'] >= 0.7:  # High confidence threshold
                        logger.info(f"\n⚡ Executing action: {action['action']}")

                        # Create resolution action
                        resolution = await resolver.resolve_pod_crash(
                            action['params']['pod_name'],
                            action['params']['namespace'],
                            result['k8s_context']
                        )

                        if resolution:
                            success, message = await resolver.execute_resolution(resolution[0])
                            if success:
                                logger.info(f"   ✅ Success: {message}")
                            else:
                                logger.error(f"   ❌ Failed: {message}")
        else:
            logger.info("\n⚠️  Automated actions available but destructive operations are disabled")
            logger.info("   Set K8S_ENABLE_DESTRUCTIVE_OPERATIONS=true to enable automated remediation")

    # Show audit log
    if hasattr(k8s_integration, 'get_audit_log'):
        audit_log = k8s_integration.get_audit_log()
        if audit_log:
            logger.info("\n📜 Audit Log:")
            for entry in audit_log:
                logger.info(f"   [{entry['timestamp']}] {entry['action']} - {entry['params']}")

    # Cleanup
    await agent.shutdown()
    logger.info("\n✅ Example completed successfully!")


async def simulate_service_down_incident():
    """Simulate handling a service down incident."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== Service Down Incident Example ===")

    # Initialize agent
    agent = OncallAgent()
    await agent.connect_integrations()

    # Create service down alert
    alert = PagerAlert(
        alert_id="K8S-SVC-002",
        severity="critical",
        service_name="api-gateway",
        description="Service api-gateway is not responding, no healthy endpoints",
        timestamp=datetime.utcnow().isoformat(),
        metadata={
            "service_name": "api-gateway",
            "namespace": "production",
            "endpoint_count": 0,
            "last_healthy": "10 minutes ago"
        }
    )

    logger.info(f"\n📨 Received Alert: {alert.description}")

    # Handle the alert
    result = await agent.handle_pager_alert(alert)

    # Display results
    logger.info(f"\n📊 Analysis: {result.get('k8s_alert_type', 'Unknown')}")

    if result.get('k8s_context', {}).get('service_status'):
        svc = result['k8s_context']['service_status'].get('service', {})
        logger.info(f"   Service Health: {'Healthy' if svc.get('healthy') else 'Unhealthy'}")
        logger.info(f"   Endpoints: {svc.get('endpoint_count', 0)}")

        if 'matching_pods' in result['k8s_context']:
            logger.info("   Matching Pods:")
            for pod in result['k8s_context']['matching_pods']:
                logger.info(f"     - {pod['name']} ({pod['status']})")

    await agent.shutdown()


async def demonstrate_k8s_operations():
    """Demonstrate various Kubernetes operations."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== Kubernetes Operations Demo ===")

    # Initialize just the K8s integration
    k8s = KubernetesMCPIntegration()

    try:
        await k8s.connect()
        logger.info("✅ Connected to Kubernetes MCP server")

        # List pods
        logger.info("\n📋 Listing pods in default namespace:")
        pods_result = await k8s.list_pods("default")
        if pods_result.get("success"):
            for pod in pods_result.get("pods", [])[:5]:  # First 5 pods
                logger.info(f"   - {pod['name']} ({pod['status']}) Ready: {pod['ready']}")
        else:
            logger.error(f"   Failed: {pods_result.get('error')}")

        # Check a specific service
        logger.info("\n🔍 Checking service status:")
        service_result = await k8s.get_service_status("kubernetes", "default")
        if service_result.get("success"):
            svc = service_result.get("service", {})
            logger.info(f"   Service: {svc['name']}")
            logger.info(f"   Type: {svc['type']}")
            logger.info(f"   ClusterIP: {svc['cluster_ip']}")
            logger.info(f"   Endpoints: {svc['endpoint_count']}")
        else:
            logger.error(f"   Failed: {service_result.get('error')}")

        # Execute a safe kubectl command
        logger.info("\n💻 Executing kubectl command:")
        cmd_result = await k8s.execute_kubectl_command("get nodes")
        if cmd_result.get("success"):
            logger.info("   Nodes in cluster:")
            for line in cmd_result.get("output", "").split("\n")[:5]:
                if line.strip():
                    logger.info(f"   {line}")
        else:
            logger.error(f"   Failed: {cmd_result.get('error')}")

    finally:
        await k8s.disconnect()
        logger.info("\n✅ Disconnected from Kubernetes")


async def main():
    """Run all examples."""
    setup_logging(level="INFO")

    # Example 1: Pod crash incident
    await simulate_pod_crash_incident()

    # Example 2: Service down incident
    await simulate_service_down_incident()

    # Example 3: K8s operations demo
    await demonstrate_k8s_operations()


if __name__ == "__main__":
    asyncio.run(main())
