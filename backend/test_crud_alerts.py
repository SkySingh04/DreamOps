#!/usr/bin/env python3
"""Test CRUD operations for alerts"""

import asyncio

import httpx

BASE_URL = "http://localhost:8000"
TEAM_ID = "team_123"

async def test_crud_operations():
    """Test all CRUD operations for alerts"""

    print("🧪 Testing Alert CRUD Operations\n")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 1. Create alerts
        print("\n1️⃣ Creating test alerts...")
        created_alerts = []

        for i in range(5):  # Try to create 5 alerts (should fail after 3 for free tier)
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/alerts/",
                    json={
                        "team_id": TEAM_ID,
                        "incident_id": f"manual_test_{i+1}",
                        "alert_type": "manual",
                        "title": f"Test Alert #{i+1}",
                        "description": "This is a test alert created via CRUD API",
                        "severity": ["low", "medium", "high", "critical"][i % 4],
                        "status": "active"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    created_alerts.append(data["alert"]["id"])
                    print(f"   ✅ Alert #{i+1} created: {data['alert']['title']}")
                elif response.status_code == 403:
                    error_data = response.json()
                    print(f"   ❌ Alert #{i+1} blocked: {error_data['detail']['message']}")
                    break
            except Exception as e:
                print(f"   ❌ Error creating alert #{i+1}: {e}")

        # 2. List all alerts
        print("\n2️⃣ Listing all alerts...")
        response = await client.get(f"{BASE_URL}/api/v1/alerts/?team_id={TEAM_ID}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {data['count']} alerts:")
            for alert in data["alerts"]:
                print(f"   - {alert['title']} ({alert['status']}) - Severity: {alert['severity']}")

        # 3. Get specific alert
        if created_alerts:
            print("\n3️⃣ Getting specific alert...")
            alert_id = created_alerts[0]
            response = await client.get(f"{BASE_URL}/api/v1/alerts/{alert_id}")
            if response.status_code == 200:
                alert = response.json()["alert"]
                print(f"   Alert details: {alert['title']}")
                print(f"   Created at: {alert['created_at']}")
                print(f"   Status: {alert['status']}")

        # 4. Update an alert
        if created_alerts:
            print("\n4️⃣ Updating alert...")
            alert_id = created_alerts[0]
            response = await client.put(
                f"{BASE_URL}/api/v1/alerts/{alert_id}",
                json={
                    "status": "resolved",
                    "description": "This alert has been resolved"
                }
            )
            if response.status_code == 200:
                alert = response.json()["alert"]
                print(f"   ✅ Alert updated: Status changed to {alert['status']}")

        # 5. Get statistics
        print("\n5️⃣ Getting alert statistics...")
        response = await client.get(f"{BASE_URL}/api/v1/alerts/stats/{TEAM_ID}")
        if response.status_code == 200:
            stats = response.json()
            print(f"   Usage: {stats['usage']['alerts_used']}/{stats['usage']['alerts_limit']} alerts")
            print(f"   Account tier: {stats['usage']['account_tier']}")
            print(f"   Stats: {stats['stats']}")

        # 6. Reset usage (for testing)
        print("\n6️⃣ Resetting alert usage...")
        response = await client.post(f"{BASE_URL}/api/v1/alerts/reset-usage/{TEAM_ID}")
        if response.status_code == 200:
            print("   ✅ Usage reset successfully")

        # 7. Delete an alert
        if created_alerts:
            print("\n7️⃣ Deleting an alert...")
            alert_id = created_alerts[-1]
            response = await client.delete(f"{BASE_URL}/api/v1/alerts/{alert_id}")
            if response.status_code == 200:
                print("   ✅ Alert deleted successfully")

        # 8. Delete all alerts for the team
        print("\n8️⃣ Cleaning up - deleting all test alerts...")
        response = await client.delete(
            f"{BASE_URL}/api/v1/alerts/?team_id={TEAM_ID}&confirm=true"
        )
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Deleted {data['count']} alerts")

    print("\n" + "=" * 60)
    print("✅ CRUD operations test completed!")
    print("\n💡 You can now:")
    print("   - Create alerts manually via POST /api/v1/alerts/")
    print("   - View all alerts at GET /api/v1/alerts/")
    print("   - Check usage at GET /api/v1/alert-tracking/usage/team_123")
    print("   - Reset usage at POST /api/v1/alerts/reset-usage/team_123")

if __name__ == "__main__":
    asyncio.run(test_crud_operations())
