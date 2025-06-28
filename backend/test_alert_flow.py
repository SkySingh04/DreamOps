#!/usr/bin/env python3
"""Test the complete 3 free alerts flow"""

import asyncio
from datetime import datetime

import httpx

BASE_URL = "http://localhost:8000"
TEAM_ID = "team_123"

async def test_alert_flow():
    """Test the complete alert flow with 3 free alerts"""

    print("🧪 Testing 3 Free Alerts Flow\n")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Check initial usage
        print("\n1️⃣ Checking initial alert usage...")
        response = await client.get(f"{BASE_URL}/api/v1/alert-tracking/usage/{TEAM_ID}")
        usage = response.json()
        print(f"   Current usage: {usage['alerts_used']}/{usage['alerts_limit']}")
        print(f"   Account tier: {usage['account_tier']}")
        print(f"   Alerts remaining: {usage['alerts_remaining']}")

        # 2. Simulate alerts
        print("\n2️⃣ Simulating alert incidents...")
        for i in range(4):  # Try to create 4 alerts (should fail on 4th)
            print(f"\n   Alert #{i+1}:")
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/alert-tracking/record",
                    json={
                        "team_id": TEAM_ID,
                        "alert_type": "test_incident",
                        "incident_id": f"test_incident_{i+1}",
                        "metadata": {"test": True, "alert_number": i+1}
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    print("   ✅ Alert recorded successfully")
                    print(f"   Alerts used: {data['alerts_used']}")
                    print(f"   Alerts remaining: {data['alerts_remaining']}")
                elif response.status_code == 403:
                    data = response.json()
                    print("   ❌ Alert limit reached!")
                    print(f"   Message: {data['detail']['message']}")
                    print(f"   Account tier: {data['detail']['account_tier']}")
                    break
            except Exception as e:
                print(f"   ❌ Error: {e}")

        # 3. Check usage after alerts
        print("\n3️⃣ Checking usage after alerts...")
        response = await client.get(f"{BASE_URL}/api/v1/alert-tracking/usage/{TEAM_ID}")
        usage = response.json()
        print(f"   Current usage: {usage['alerts_used']}/{usage['alerts_limit']}")
        print(f"   Is limit reached: {usage['is_limit_reached']}")

        # 4. Get subscription plans
        print("\n4️⃣ Getting available subscription plans...")
        response = await client.get(f"{BASE_URL}/api/v1/alert-tracking/plans")
        plans_data = response.json()
        print("   Available plans:")
        for plan in plans_data['plans']:
            limit = "Unlimited" if plan['alerts_limit'] == -1 else f"{plan['alerts_limit']} alerts"
            print(f"   - {plan['name']}: ₹{plan['price']}/month ({limit})")

        # 5. Simulate upgrade to Pro
        if usage['is_limit_reached']:
            print("\n5️⃣ Simulating upgrade to Pro plan...")
            response = await client.post(
                f"{BASE_URL}/api/v1/alert-tracking/upgrade",
                json={
                    "team_id": TEAM_ID,
                    "plan_id": "pro",
                    "transaction_id": f"mock_txn_{datetime.now().timestamp()}"
                }
            )

            if response.status_code == 200:
                data = response.json()
                print("   ✅ Upgrade successful!")
                print(f"   New tier: {data['new_tier']}")
                print(f"   New limit: {data['new_limit']} alerts")

                # Check usage after upgrade
                print("\n6️⃣ Checking usage after upgrade...")
                response = await client.get(f"{BASE_URL}/api/v1/alert-tracking/usage/{TEAM_ID}")
                usage = response.json()
                print(f"   Current usage: {usage['alerts_used']}/{usage['alerts_limit']}")
                print(f"   Account tier: {usage['account_tier']}")
                print("   Can now process more alerts!")

    print("\n" + "=" * 60)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_alert_flow())
