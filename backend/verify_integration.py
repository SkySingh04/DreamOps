#!/usr/bin/env python3
"""Verify the complete integration flow."""

import requests
import json
from datetime import datetime
import time

def check_frontend():
    """Check if frontend is accessible."""
    print("1. Checking Frontend...")
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        print(f"   ✅ Frontend is running (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"   ❌ Frontend is not accessible: {e}")
        return False

def check_backend():
    """Check if backend API is accessible."""
    print("\n2. Checking Backend API...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"   ✅ Backend is running (status: {response.status_code})")
        return True
    except Exception as e:
        print(f"   ❌ Backend is not accessible: {e}")
        return False

def check_dashboard_api():
    """Check if dashboard API endpoints are working."""
    print("\n3. Checking Dashboard API Endpoints...")
    
    # Test public endpoints (no auth required)
    endpoints = [
        ("/api/public/dashboard/metrics", "Public Metrics"),
        ("/api/public/dashboard/incidents", "Public Incidents"),
        ("/api/public/dashboard/ai-actions", "Public AI Actions")
    ]
    
    working = True
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"http://localhost:3000{endpoint}", timeout=5)
            if response.status_code in [200, 201]:
                print(f"   ✅ {name} endpoint is working")
            else:
                print(f"   ⚠️  {name} endpoint returned {response.status_code}")
                working = False
        except Exception as e:
            print(f"   ❌ {name} endpoint failed: {e}")
            working = False
    
    return working

def test_incident_creation():
    """Test creating an incident via API."""
    print("\n4. Testing Incident Creation...")
    
    incident_data = {
        "title": f"Test Alert: Service Down - {datetime.now().strftime('%H:%M:%S')}",
        "description": "Testing dashboard integration",
        "severity": "high",
        "source": "test_script",
        "sourceId": f"test-{int(time.time())}"
    }
    
    try:
        # Test internal API endpoint
        response = requests.post(
            "http://localhost:3000/api/dashboard/internal/incidents",
            json=incident_data,
            headers={"x-internal-api-key": "oncall-agent-internal"},
            timeout=5
        )
        if response.status_code == 201:
            incident = response.json()
            print(f"   ✅ Incident created successfully with ID: {incident.get('id')}")
            return incident.get('id')
        else:
            print(f"   ❌ Failed to create incident: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Error creating incident: {e}")
        return None

def test_ai_action_creation(incident_id=None):
    """Test creating an AI action via API."""
    print("\n5. Testing AI Action Creation...")
    
    action_data = {
        "action": "test_verification",
        "description": "Verifying AI action recording",
        "incidentId": incident_id,
        "status": "completed",
        "metadata": {"verified": True}
    }
    
    try:
        response = requests.post(
            "http://localhost:3000/api/dashboard/internal/ai-actions",
            json=action_data,
            headers={"x-internal-api-key": "oncall-agent-internal"},
            timeout=5
        )
        if response.status_code == 201:
            ai_action = response.json()
            print(f"   ✅ AI action created successfully with ID: {ai_action.get('id')}")
            return True
        else:
            print(f"   ❌ Failed to create AI action: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error creating AI action: {e}")
        return False

def check_database_connection():
    """Check if database queries are working."""
    print("\n6. Checking Database Connection...")
    
    try:
        # Test public API endpoint
        response = requests.get("http://localhost:3000/api/public/dashboard/metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Database queries working")
            print(f"   - Active incidents: {data.get('activeIncidents', 0)}")
            print(f"   - Resolved today: {data.get('resolvedToday', 0)}")
            print(f"   - Health score: {data.get('healthScore', 0)}%")
            return True
        else:
            print(f"   ❌ Database query failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error checking database: {e}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("🔍 Verifying OnCall Agent Dashboard Integration")
    print("=" * 60)
    
    # Run all checks
    frontend_ok = check_frontend()
    backend_ok = check_backend()
    api_ok = check_dashboard_api()
    
    if frontend_ok and api_ok:
        incident_id = test_incident_creation()
        incident_ok = incident_id is not None
        
        if incident_ok:
            ai_action_ok = test_ai_action_creation(incident_id)
        else:
            ai_action_ok = False
            
        db_ok = check_database_connection()
    else:
        incident_ok = False
        ai_action_ok = False
        db_ok = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    print("=" * 60)
    
    checks = [
        ("Frontend", frontend_ok),
        ("Backend API", backend_ok),
        ("Dashboard API", api_ok),
        ("Incident Creation", incident_ok),
        ("AI Action Creation", ai_action_ok),
        ("Database Connection", db_ok)
    ]
    
    for name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}: {'Working' if status else 'Not Working'}")
    
    all_ok = all(status for _, status in checks)
    
    if all_ok:
        print("\n🎉 All systems operational! The integration is working correctly.")
        print("\n📝 Next steps:")
        print("1. Run fuck_kubernetes.sh to trigger real alerts")
        print("2. Check the dashboard at http://localhost:3000/dashboard")
        print("3. Monitor the backend logs for alert processing")
        print("\n🔄 Flow: K8s Issue → CloudWatch → PagerDuty → Backend Agent → Dashboard")
    else:
        print("\n⚠️  Some components are not working. Please check:")
        print("1. Is the frontend running? (npm run dev in frontend/)")
        print("2. Is the backend running? (uv run python api_server.py in backend/)")
        print("3. Are the .env files configured correctly?")
        print("4. Is the database accessible?")

if __name__ == "__main__":
    main()