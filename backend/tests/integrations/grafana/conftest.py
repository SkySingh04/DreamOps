"""Pytest configuration and fixtures for Grafana integration tests."""

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient

from oncall_agent.mcp_integrations.grafana_mcp import GrafanaMCPIntegration

# Test configuration
TEST_DASHBOARD_PREFIX = "test_oncall_"
TEST_TIMEOUT = 30.0


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def grafana_config() -> dict[str, Any]:
    """Load Grafana configuration from environment variables."""
    grafana_url = os.getenv("GRAFANA_MCP_URL") or os.getenv("GRAFANA_URL")
    grafana_api_key = os.getenv("GRAFANA_MCP_API_KEY") or os.getenv("GRAFANA_API_KEY")

    if not grafana_url or not grafana_api_key:
        pytest.skip("Grafana credentials not configured. Set GRAFANA_MCP_URL and GRAFANA_MCP_API_KEY")

    return {
        "grafana_url": grafana_url,
        "grafana_api_key": grafana_api_key,
        "timeout": TEST_TIMEOUT,
    }


@pytest_asyncio.fixture
async def grafana_integration(grafana_config) -> AsyncGenerator[GrafanaMCPIntegration, None]:
    """Create and connect Grafana integration instance."""
    integration = GrafanaMCPIntegration(grafana_config)

    try:
        await integration.connect()
        yield integration
    finally:
        await integration.disconnect()


@pytest_asyncio.fixture
async def grafana_client(grafana_config) -> AsyncGenerator[AsyncClient, None]:
    """Create direct Grafana API client for test setup/teardown."""
    headers = {"Authorization": f"Bearer {grafana_config['grafana_api_key']}"}

    async with AsyncClient(
        base_url=grafana_config["grafana_url"],
        headers=headers,
        timeout=grafana_config["timeout"]
    ) as client:
        yield client


@pytest.fixture
def test_dashboard_data() -> dict[str, Any]:
    """Generate test dashboard data."""
    test_id = str(uuid.uuid4())[:8]

    return {
        "uid": f"{TEST_DASHBOARD_PREFIX}{test_id}",
        "title": f"Test Dashboard {test_id}",
        "tags": ["test", "oncall-agent"],
        "timezone": "browser",
        "panels": [
            {
                "id": 1,
                "title": "Test Panel",
                "type": "graph",
                "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                "targets": [
                    {
                        "refId": "A",
                        "expr": "up",
                        "interval": "",
                        "legendFormat": ""
                    }
                ]
            }
        ],
        "schemaVersion": 16,
        "version": 0
    }


@pytest.fixture
def test_alert_rule_data() -> dict[str, Any]:
    """Generate test alert rule data."""
    test_id = str(uuid.uuid4())[:8]

    return {
        "uid": f"{TEST_DASHBOARD_PREFIX}alert_{test_id}",
        "title": f"Test Alert {test_id}",
        "condition": "A",
        "data": [
            {
                "refId": "A",
                "queryType": "",
                "model": {
                    "expr": "up == 0",
                    "interval": "30s",
                    "refId": "A"
                }
            }
        ],
        "noDataState": "NoData",
        "execErrState": "Alerting",
        "for": "5m",
        "annotations": {
            "description": "Test alert for OnCall Agent integration",
            "runbook_url": "https://example.com/runbook",
            "summary": "Service is down"
        },
        "labels": {
            "severity": "critical",
            "team": "oncall-test"
        }
    }


@pytest.fixture
def test_annotation_data() -> dict[str, Any]:
    """Generate test annotation data."""
    now = datetime.utcnow()

    return {
        "time": int(now.timestamp() * 1000),  # Milliseconds
        "timeEnd": int((now + timedelta(minutes=5)).timestamp() * 1000),
        "tags": ["test", "deployment"],
        "text": "Test deployment annotation",
        "isRegion": True
    }


@pytest.fixture
def prometheus_queries() -> list[dict[str, str]]:
    """Common Prometheus queries for testing."""
    return [
        {
            "name": "service_uptime",
            "query": 'up{job="test-service"}',
            "description": "Service availability"
        },
        {
            "name": "request_rate",
            "query": 'rate(http_requests_total{service="test-service"}[5m])',
            "description": "Request rate per second"
        },
        {
            "name": "error_rate",
            "query": 'rate(http_requests_total{service="test-service",status=~"5.."}[5m])',
            "description": "5xx error rate"
        },
        {
            "name": "latency_p95",
            "query": 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="test-service"}[5m]))',
            "description": "95th percentile latency"
        },
        {
            "name": "memory_usage",
            "query": 'process_resident_memory_bytes{job="test-service"}',
            "description": "Memory usage in bytes"
        },
        {
            "name": "cpu_usage",
            "query": 'rate(process_cpu_seconds_total{job="test-service"}[5m])',
            "description": "CPU usage rate"
        }
    ]


@pytest_asyncio.fixture
async def cleanup_test_dashboards(grafana_client):
    """Cleanup any test dashboards created during tests."""
    yield

    # Cleanup after tests
    try:
        # Search for test dashboards
        response = await grafana_client.get(f"/api/search?query={TEST_DASHBOARD_PREFIX}")
        dashboards = response.json()

        # Delete each test dashboard
        for dashboard in dashboards:
            if dashboard.get("uid", "").startswith(TEST_DASHBOARD_PREFIX):
                delete_response = await grafana_client.delete(f"/api/dashboards/uid/{dashboard['uid']}")
                if delete_response.status_code == 200:
                    print(f"Cleaned up test dashboard: {dashboard['uid']}")

    except Exception as e:
        print(f"Warning: Failed to cleanup test dashboards: {e}")


@pytest_asyncio.fixture
async def test_dashboard(grafana_client, test_dashboard_data, cleanup_test_dashboards) -> dict[str, Any]:
    """Create a test dashboard and ensure cleanup."""
    # Create dashboard
    response = await grafana_client.post(
        "/api/dashboards/db",
        json={"dashboard": test_dashboard_data, "overwrite": False}
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to create test dashboard: {response.text}")

    result = response.json()
    dashboard_uid = result.get("uid")

    # Return dashboard info
    return {
        "uid": dashboard_uid,
        "id": result.get("id"),
        "url": result.get("url"),
        "data": test_dashboard_data
    }


@pytest.fixture
def mock_metrics_data() -> dict[str, Any]:
    """Generate mock metrics data for testing."""
    now = datetime.utcnow()

    return {
        "status": "success",
        "data": {
            "resultType": "matrix",
            "result": [
                {
                    "metric": {
                        "__name__": "up",
                        "instance": "localhost:9090",
                        "job": "test-service"
                    },
                    "values": [
                        [int((now - timedelta(minutes=i)).timestamp()), "1"]
                        for i in range(10, 0, -1)
                    ]
                }
            ]
        }
    }


@pytest.fixture
def performance_threshold() -> dict[str, float]:
    """Performance thresholds for query operations."""
    return {
        "dashboard_list": 2.0,  # seconds
        "dashboard_get": 1.0,
        "query_simple": 3.0,
        "query_complex": 5.0,
        "alert_list": 2.0,
        "annotation_query": 2.0
    }


@pytest.mark.grafana
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "grafana: mark test as requiring Grafana connection"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "requires_permissions: mark test as requiring specific Grafana permissions"
    )


def pytest_collection_modifyitems(config, items):
    """Skip Grafana tests if credentials not available."""
    if not (os.getenv("GRAFANA_MCP_URL") or os.getenv("GRAFANA_URL")):
        skip_grafana = pytest.mark.skip(reason="Grafana credentials not configured")
        for item in items:
            if "grafana" in item.keywords:
                item.add_marker(skip_grafana)
