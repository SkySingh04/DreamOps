#!/usr/bin/env python3
"""Test script to verify the webhook flow works correctly with MCP integrations."""

import asyncio
import json
from datetime import datetime

import aiohttp


async def test_webhook():
    """Send a test webhook to verify the flow."""

    # Test webhook payload (PagerDuty V3 format)
    webhook_payload = {
        "event": {
            "id": f"TEST-{datetime.now().timestamp()}",
            "event_type": "incident.triggered",
            "resource_type": "incident",
            "occurred_at": datetime.now().isoformat() + "Z",
            "agent": {
                "id": "PG8UW3O",
                "type": "inbound_integration_reference",
                "summary": "Amazon CloudWatch"
            },
            "client": {
                "name": "AWS Console",
                "url": "https://console.aws.amazon.com/cloudwatch/home?region=ap-south-1#s=Alarms&alarm=eks-pod-errors"
            },
            "data": {
                "id": f"TEST-INC-{int(datetime.now().timestamp())}",
                "type": "incident",
                "number": 999,
                "status": "triggered",
                "incident_key": None,
                "created_at": datetime.now().isoformat() + "Z",
                "title": "CRITICAL: Multiple pods crashing in production cluster",
                "description": "Pod errors detected: nginx-deployment pods are in CrashLoopBackOff state. Service unavailable.",
                "service": {
                    "id": "PUX61H3",
                    "type": "service_reference",
                    "summary": "Production Web Service"
                },
                "urgency": "high",
                "html_url": "https://example.pagerduty.com/incidents/TEST"
            }
        }
    }

    # Send webhook to local API server
    url = "http://localhost:8000/webhook/pagerduty"

    print("🚀 Sending test webhook to API server...")
    print(f"📋 Alert title: {webhook_payload['event']['data']['title']}")
    print(f"📋 Alert description: {webhook_payload['event']['data']['description']}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=webhook_payload) as response:
                if response.status == 200:
                    result = await response.json()
                    print("\n✅ Webhook processed successfully!")
                    print(f"📊 Response: {json.dumps(result, indent=2)}")

                    # Check if MCP integrations were used
                    if result.get("results") and len(result["results"]) > 0:
                        first_result = result["results"][0]
                        if first_result.get("agent_response", {}).get("context_gathered"):
                            print("\n🔍 MCP Integrations Used:")
                            for integration, success in first_result["agent_response"]["context_gathered"].items():
                                print(f"  - {integration}: {'✅ Success' if success else '❌ Failed'}")

                else:
                    print(f"❌ Error: API returned status {response.status}")
                    print(await response.text())

        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
            print("Make sure the API server is running: uv run python api_server.py")


if __name__ == "__main__":
    print("=" * 80)
    print("🧪 TESTING ONCALL AGENT WEBHOOK FLOW")
    print("=" * 80)
    print("\nThis test will:")
    print("1. Send a simulated PagerDuty webhook")
    print("2. Verify the agent processes it")
    print("3. Check that MCP integrations are called")
    print("4. Display the analysis results")
    print("\n" + "=" * 80)

    asyncio.run(test_webhook())
