#!/usr/bin/env python3
"""Test the payment and upgrade flow"""

import asyncio

import httpx

BASE_URL = "http://localhost:8000"
TEAM_ID = "team_123"

async def test_payment_upgrade():
    """Test the complete payment upgrade flow"""

    print("🧪 Testing Payment Upgrade Flow\n")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Check initial usage
        print("\n1️⃣ Checking initial alert usage...")
        response = await client.get(f"{BASE_URL}/api/v1/alert-tracking/usage/{TEAM_ID}")
        usage = response.json()
        print(f"   Current usage: {usage['alerts_used']}/{usage['alerts_limit']}")
        print(f"   Account tier: {usage['account_tier']}")

        # 2. Reset usage for clean test
        print("\n2️⃣ Resetting usage for clean test...")
        response = await client.post(f"{BASE_URL}/api/v1/alerts/reset-usage/{TEAM_ID}")
        print("   ✅ Usage reset")

        # 3. Create 3 alerts to exhaust free tier
        print("\n3️⃣ Creating 3 alerts to exhaust free tier...")
        for i in range(3):
            response = await client.post(
                f"{BASE_URL}/api/v1/alerts/",
                json={
                    "team_id": TEAM_ID,
                    "incident_id": f"test_payment_{i+1}",
                    "title": f"Test Alert #{i+1}",
                    "alert_type": "manual"
                }
            )
            print(f"   ✅ Alert #{i+1} created")

        # 4. Check usage after alerts
        print("\n4️⃣ Checking usage after alerts...")
        response = await client.get(f"{BASE_URL}/api/v1/alert-tracking/usage/{TEAM_ID}")
        usage = response.json()
        print(f"   Current usage: {usage['alerts_used']}/{usage['alerts_limit']}")
        print(f"   Is limit reached: {usage['is_limit_reached']}")

        # 5. Initiate payment for Pro plan
        print("\n5️⃣ Initiating payment for Pro plan...")
        response = await client.post(
            f"{BASE_URL}/api/v1/mock-payments/initiate",
            json={
                "team_id": TEAM_ID,
                "amount": 299900,  # ₹2999 in paise
                "plan": "PRO",
                "metadata": {"test": True}
            }
        )
        payment_data = response.json()
        transaction_id = payment_data["transaction_id"]
        print(f"   Transaction ID: {transaction_id}")
        print(f"   Redirect URL: {payment_data['redirect_url']}")

        # 6. Simulate payment completion
        print("\n6️⃣ Simulating payment completion...")
        response = await client.post(
            f"{BASE_URL}/api/v1/mock-payments/status",
            json={
                "merchant_transaction_id": transaction_id,
                "team_id": TEAM_ID,
                "amount": 299900
            }
        )
        status_data = response.json()
        print(f"   Payment status: {status_data['payment_status']}")
        print(f"   Upgraded to plan: {status_data.get('transaction_details', {}).get('plan_id')}")

        # 7. Check usage after upgrade
        print("\n7️⃣ Checking usage after upgrade...")
        response = await client.get(f"{BASE_URL}/api/v1/alert-tracking/usage/{TEAM_ID}")
        usage = response.json()
        print(f"   Current usage: {usage['alerts_used']}/{usage['alerts_limit']}")
        print(f"   Account tier: {usage['account_tier']}")
        print(f"   Is limit reached: {usage['is_limit_reached']}")

        # 8. Try creating another alert
        print("\n8️⃣ Creating alert after upgrade...")
        response = await client.post(
            f"{BASE_URL}/api/v1/alerts/",
            json={
                "team_id": TEAM_ID,
                "incident_id": "test_after_upgrade",
                "title": "Alert after upgrade",
                "alert_type": "manual"
            }
        )
        if response.status_code == 200:
            print("   ✅ Alert created successfully - upgrade worked!")
        else:
            print("   ❌ Failed to create alert - upgrade didn't work")

    print("\n" + "=" * 60)
    print("✅ Payment upgrade test completed!")

if __name__ == "__main__":
    asyncio.run(test_payment_upgrade())
