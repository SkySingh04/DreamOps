#!/usr/bin/env python3
"""Test the complete dashboard integration flow."""

import asyncio
from datetime import datetime

import aiohttp

from src.oncall_agent.agent import OncallAgent, PagerAlert


async def test_manual_incident_creation():
    """Test creating an incident directly via the dashboard API."""
    print("\n=== Testing Manual Incident Creation ===")

    async with aiohttp.ClientSession() as session:
        incident_data = {
            "title": "Test K8s Alert: Pod CrashLoopBackOff",
            "description": "Pod nginx-deployment-5d6cf97d6d-xyz is crash looping in namespace default",
            "severity": "critical",
            "source": "test_script",
            "sourceId": f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "metadata": {
                "namespace": "default",
                "pod_name": "nginx-deployment-5d6cf97d6d-xyz",
                "container": "nginx",
                "restarts": 5
            }
        }

        try:
            async with session.post(
                "http://localhost:3000/api/dashboard/incidents",
                json=incident_data
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    print(f"✅ Incident created successfully: {result}")
                    return result.get("id")
                else:
                    print(f"❌ Failed to create incident: {response.status}")
                    print(await response.text())
                    return None
        except Exception as e:
            print(f"❌ Error creating incident: {e}")
            return None


async def test_ai_action_creation(incident_id: int = None):
    """Test creating an AI action via the dashboard API."""
    print("\n=== Testing AI Action Creation ===")

    async with aiohttp.ClientSession() as session:
        action_data = {
            "action": "automated_restart",
            "description": "Attempted to restart pod nginx-deployment-5d6cf97d6d-xyz",
            "incidentId": incident_id,
            "status": "completed",
            "metadata": {
                "pod_name": "nginx-deployment-5d6cf97d6d-xyz",
                "namespace": "default",
                "confidence": 0.8
            }
        }

        try:
            async with session.post(
                "http://localhost:3000/api/dashboard/ai-actions",
                json=action_data
            ) as response:
                if response.status == 201:
                    result = await response.json()
                    print(f"✅ AI action created successfully: {result}")
                else:
                    print(f"❌ Failed to create AI action: {response.status}")
                    print(await response.text())
        except Exception as e:
            print(f"❌ Error creating AI action: {e}")


async def test_agent_integration():
    """Test the full agent integration with dashboard."""
    print("\n=== Testing Agent Integration with Dashboard ===")

    # Create and initialize the agent
    agent = OncallAgent()
    await agent.connect_integrations()

    # Create a test alert
    alert = PagerAlert(
        alert_id=f"test-alert-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        severity="critical",
        service_name="nginx-service",
        description="Pod nginx-deployment-5d6cf97d6d-abc123 is in CrashLoopBackOff state with 10 restarts",
        timestamp=datetime.now().isoformat(),
        metadata={
            "namespace": "default",
            "pod_name": "nginx-deployment-5d6cf97d6d-abc123",
            "container": "nginx",
            "restarts": 10,
            "alert_type": "pod_crash"
        }
    )

    print(f"\n📨 Sending alert to agent: {alert.alert_id}")

    # Process the alert
    result = await agent.handle_pager_alert(alert)

    print("\n✅ Agent processing complete")
    print(f"Status: {result.get('status')}")
    print(f"Context gathered from: {result.get('context_gathered')}")

    # Shutdown agent
    await agent.shutdown()


async def test_dashboard_metrics():
    """Test fetching dashboard metrics."""
    print("\n=== Testing Dashboard Metrics API ===")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:3000/api/dashboard/metrics") as response:
                if response.status == 200:
                    metrics = await response.json()
                    print("✅ Dashboard metrics retrieved:")
                    print(f"  - Active incidents: {metrics.get('activeIncidents', 0)}")
                    print(f"  - Resolved today: {metrics.get('resolvedToday', 0)}")
                    print(f"  - Avg response time: {metrics.get('avgResponseTime', 0)}ms")
                    print(f"  - Health score: {metrics.get('healthScore', 0)}%")
                else:
                    print(f"❌ Failed to fetch metrics: {response.status}")
                    print(await response.text())
        except Exception as e:
            print(f"❌ Error fetching metrics: {e}")


async def main():
    """Run all integration tests."""
    print("🚀 Starting Dashboard Integration Tests")
    print("=" * 60)

    # Test 1: Create incident manually
    incident_id = await test_manual_incident_creation()

    # Test 2: Create AI action
    if incident_id:
        await test_ai_action_creation(incident_id)

    # Test 3: Test agent integration
    await test_agent_integration()

    # Test 4: Fetch dashboard metrics
    await test_dashboard_metrics()

    print("\n" + "=" * 60)
    print("✅ Integration tests complete!")
    print("\n👉 Now check your dashboard at http://localhost:3000/dashboard")
    print("   You should see:")
    print("   - New incidents created")
    print("   - AI actions logged")
    print("   - Updated metrics")


if __name__ == "__main__":
    asyncio.run(main())
