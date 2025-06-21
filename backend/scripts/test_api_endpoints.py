#!/usr/bin/env python3
"""Test script to verify all API endpoints are working."""

import asyncio
import httpx
import json
from typing import Dict, Any
from datetime import datetime, UTC

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


async def test_endpoint(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    data: Dict[str, Any] = None,
    params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Test a single endpoint."""
    url = f"{BASE_URL}{API_PREFIX}{path}"
    
    try:
        if method == "GET":
            response = await client.get(url, params=params)
        elif method == "POST":
            response = await client.post(url, json=data)
        elif method == "PUT":
            response = await client.put(url, json=data)
        elif method == "PATCH":
            response = await client.patch(url, json=data)
        else:
            return {"error": f"Unsupported method: {method}"}
        
        return {
            "status": "success",
            "status_code": response.status_code,
            "response": response.json() if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


async def test_all_endpoints():
    """Test all API endpoints."""
    print("Testing OnCall Agent API Endpoints...")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint
        print("\n1. Testing Health Check...")
        result = await test_endpoint(client, "GET", "/../health")
        print(f"   Status: {result['status']}")
        
        # Test Dashboard endpoints
        print("\n2. Testing Dashboard Endpoints...")
        dashboard_endpoints = [
            ("GET", "/dashboard/stats"),
            ("GET", "/dashboard/metrics/incidents", {"period": "24h"}),
            ("GET", "/dashboard/activity-feed", {"limit": 5}),
            ("GET", "/dashboard/severity-distribution"),
        ]
        
        for method, path, *args in dashboard_endpoints:
            params = args[0] if args else None
            result = await test_endpoint(client, method, path, params=params)
            print(f"   {method} {path}: {result['status']}")
        
        # Test Incidents endpoints
        print("\n3. Testing Incidents Endpoints...")
        
        # Create an incident
        incident_data = {
            "title": "Test API Incident",
            "description": "Testing the new API endpoints",
            "severity": "medium",
            "service_name": "test-service",
            "alert_source": "manual"
        }
        result = await test_endpoint(client, "POST", "/incidents", data=incident_data)
        print(f"   POST /incidents: {result['status']}")
        
        if result['status'] == 'success' and result['status_code'] == 201:
            incident_id = result['response']['id']
            
            # Test other incident endpoints
            incident_endpoints = [
                ("GET", "/incidents"),
                ("GET", f"/incidents/{incident_id}"),
                ("GET", f"/incidents/{incident_id}/timeline"),
            ]
            
            for method, path in incident_endpoints:
                result = await test_endpoint(client, method, path)
                print(f"   {method} {path}: {result['status']}")
        
        # Test Agent endpoints
        print("\n4. Testing AI Agent Endpoints...")
        agent_endpoints = [
            ("GET", "/agent/status"),
            ("GET", "/agent/capabilities"),
            ("GET", "/agent/knowledge-base", {"query": "database", "limit": 5}),
            ("GET", "/agent/learning-metrics"),
        ]
        
        for method, path, *args in agent_endpoints:
            params = args[0] if args else None
            result = await test_endpoint(client, method, path, params=params)
            print(f"   {method} {path}: {result['status']}")
        
        # Test Integrations endpoints
        print("\n5. Testing Integrations Endpoints...")
        integration_endpoints = [
            ("GET", "/integrations"),
            ("GET", "/integrations/kubernetes"),
            ("GET", "/integrations/available"),
        ]
        
        for method, path in integration_endpoints:
            result = await test_endpoint(client, method, path)
            print(f"   {method} {path}: {result['status']}")
        
        # Test Analytics endpoints
        print("\n6. Testing Analytics Endpoints...")
        analytics_data = {
            "time_range": {
                "start": "2024-01-01T00:00:00Z",
                "end": datetime.now(UTC).isoformat()
            }
        }
        result = await test_endpoint(client, "POST", "/analytics/incidents", data=analytics_data)
        print(f"   POST /analytics/incidents: {result['status']}")
        
        analytics_endpoints = [
            ("GET", "/analytics/services/health", {"days": 7}),
            ("GET", "/analytics/patterns", {"days": 30}),
            ("GET", "/analytics/predictions"),
        ]
        
        for method, path, *args in analytics_endpoints:
            params = args[0] if args else None
            result = await test_endpoint(client, method, path, params=params)
            print(f"   {method} {path}: {result['status']}")
        
        # Test Security endpoints
        print("\n7. Testing Security Endpoints...")
        security_endpoints = [
            ("GET", "/security/audit-logs", {"page": 1, "page_size": 10}),
            ("GET", "/security/permissions", {"user_email": "test@example.com"}),
            ("GET", "/security/compliance-report"),
        ]
        
        for method, path, *args in security_endpoints:
            params = args[0] if args else None
            result = await test_endpoint(client, method, path, params=params)
            print(f"   {method} {path}: {result['status']}")
        
        # Test Monitoring endpoints
        print("\n8. Testing Monitoring Endpoints...")
        monitoring_endpoints = [
            ("GET", "/monitoring/logs", {"limit": 10}),
            ("GET", "/monitoring/metrics"),
            ("GET", "/monitoring/status"),
            ("GET", "/monitoring/alerts/active"),
        ]
        
        for method, path, *args in monitoring_endpoints:
            params = args[0] if args else None
            result = await test_endpoint(client, method, path, params=params)
            print(f"   {method} {path}: {result['status']}")
        
        # Test Settings endpoints
        print("\n9. Testing Settings Endpoints...")
        settings_endpoints = [
            ("GET", "/settings"),
            ("GET", "/settings/notifications"),
            ("GET", "/settings/automation"),
            ("GET", "/settings/oncall-schedules"),
        ]
        
        for method, path in settings_endpoints:
            result = await test_endpoint(client, method, path)
            print(f"   {method} {path}: {result['status']}")
    
    print("\n" + "=" * 50)
    print("API Endpoint Testing Complete!")


if __name__ == "__main__":
    asyncio.run(test_all_endpoints())