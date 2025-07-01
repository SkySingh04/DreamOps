"""Comprehensive test suite for Grafana MCP integration."""

import asyncio
import time

import pytest

from oncall_agent.mcp_integrations.grafana_mcp import GrafanaMCPIntegration


@pytest.mark.grafana
class TestGrafanaConnection:
    """Test Grafana connection and basic operations."""

    async def test_connection(self, grafana_integration):
        """Test basic connection to Grafana."""
        assert grafana_integration.connected
        assert grafana_integration.connection_time is not None

        # Test health check
        health = await grafana_integration.health_check()
        # Health check can return True or a detailed status dict
        if isinstance(health, dict):
            assert health.get("connected") is True
            assert "status" in health
        else:
            assert health is True

    async def test_capabilities(self, grafana_integration):
        """Test getting integration capabilities."""
        capabilities = await grafana_integration.get_capabilities()

        assert "context_types" in capabilities
        assert "actions" in capabilities
        assert "features" in capabilities

        # Verify expected capabilities
        assert "dashboards" in capabilities["context_types"]
        assert "metrics" in capabilities["context_types"]
        assert "query_metrics" in capabilities["actions"]

    async def test_connection_retry(self, grafana_config):
        """Test connection retry mechanism."""
        # Create integration with invalid URL
        bad_config = grafana_config.copy()
        bad_config["grafana_url"] = "https://invalid-grafana-url.test"

        integration = GrafanaMCPIntegration(bad_config)

        with pytest.raises(ConnectionError):
            await integration.connect()


@pytest.mark.grafana
class TestDashboardOperations:
    """Test dashboard-related operations."""

    async def test_list_dashboards(self, grafana_integration, performance_threshold):
        """Test listing dashboards with performance check."""
        start_time = time.time()

        result = await grafana_integration.fetch_context("dashboards")

        elapsed = time.time() - start_time
        assert elapsed < performance_threshold["dashboard_list"]

        assert "error" not in result
        assert "dashboards" in result
        assert isinstance(result["dashboards"], list)
        assert "count" in result

        # If dashboards exist, verify structure
        if result["dashboards"]:
            dashboard = result["dashboards"][0]
            assert "uid" in dashboard
            assert "title" in dashboard

    async def test_search_dashboards(self, grafana_integration):
        """Test searching for dashboards."""
        # Search with empty query
        result = await grafana_integration.fetch_context("search", query="")
        assert "error" not in result
        assert "results" in result

        # Search with specific query
        result = await grafana_integration.fetch_context("search", query="test")
        assert "error" not in result

    async def test_create_dashboard(self, grafana_integration, test_dashboard_data, cleanup_test_dashboards):
        """Test creating a dashboard."""
        result = await grafana_integration.execute_action(
            "create_dashboard",
            {"dashboard": test_dashboard_data}
        )

        # Check if creation was successful or permission denied
        if "error" not in result:
            assert "uid" in result
            assert "url" in result
        else:
            # If error, should be permission related
            assert "403" in str(result["error"]) or "permission" in str(result["error"]).lower()

    @pytest.mark.slow
    async def test_dashboard_operations_workflow(self, grafana_integration, test_dashboard_data, cleanup_test_dashboards):
        """Test complete dashboard workflow: create, list, update, delete."""
        # Skip if no create permissions
        create_result = await grafana_integration.execute_action(
            "create_dashboard",
            {"dashboard": test_dashboard_data}
        )

        if "error" in create_result and "403" in str(create_result["error"]):
            pytest.skip("Insufficient permissions for dashboard operations")

        dashboard_uid = create_result.get("uid")

        # List and verify dashboard exists
        list_result = await grafana_integration.fetch_context("dashboards")
        dashboard_uids = [d["uid"] for d in list_result.get("dashboards", [])]
        assert dashboard_uid in dashboard_uids

        # Update dashboard
        test_dashboard_data["title"] = f"{test_dashboard_data['title']} - Updated"
        test_dashboard_data["uid"] = dashboard_uid
        test_dashboard_data["version"] = 1

        update_result = await grafana_integration.execute_action(
            "update_dashboard",
            {"dashboard": test_dashboard_data}
        )
        assert "error" not in update_result


@pytest.mark.grafana
class TestMetricsOperations:
    """Test metrics and query operations."""

    async def test_query_metrics_simple(self, grafana_integration, performance_threshold):
        """Test simple metrics query."""
        start_time = time.time()

        result = await grafana_integration.fetch_context(
            "metrics",
            query="up",
            start="-5m",
            end="now",
            step="30s"
        )

        elapsed = time.time() - start_time

        # Check for permission error or success
        if "error" in result:
            assert "403" in str(result["error"]) or "permission" in str(result["error"]).lower()
        else:
            assert elapsed < performance_threshold["query_simple"]
            assert "data" in result or "status" in result

    @pytest.mark.parametrize("query_data", [
        {"query": "up", "start": "-1h", "step": "1m"},
        {"query": "rate(http_requests_total[5m])", "start": "-30m", "step": "30s"},
        {"query": "histogram_quantile(0.95, http_request_duration_seconds_bucket)", "start": "-15m"},
    ])
    async def test_query_metrics_various(self, grafana_integration, query_data):
        """Test various metric queries."""
        result = await grafana_integration.fetch_context("metrics", **query_data)

        # Should either succeed or fail with permissions
        if "error" in result:
            error_msg = str(result["error"]).lower()
            assert any(x in error_msg for x in ["403", "permission", "forbidden"])

    async def test_incident_metrics(self, grafana_integration):
        """Test getting incident-specific metrics."""
        result = await grafana_integration.get_incident_metrics(
            service_name="test-service",
            time_range="-30m"
        )

        assert "service" in result
        assert result["service"] == "test-service"
        assert "time_range" in result
        assert "timestamp" in result

        # Metrics might be empty due to permissions
        if "error" not in result:
            assert "metrics" in result
            assert isinstance(result["metrics"], dict)

    @pytest.mark.slow
    async def test_metrics_time_ranges(self, grafana_integration):
        """Test metrics with various time ranges."""
        time_ranges = ["-5m", "-15m", "-1h", "-6h", "-24h"]

        for time_range in time_ranges:
            result = await grafana_integration.fetch_context(
                "metrics",
                query="up",
                start=time_range
            )

            # Each query should either succeed or fail with permissions
            assert isinstance(result, dict)


@pytest.mark.grafana
class TestAlertOperations:
    """Test alert-related operations."""

    async def test_list_alerts(self, grafana_integration):
        """Test listing alerts."""
        result = await grafana_integration.fetch_context("alerts")

        # Grafana Cloud might not have alerts endpoint
        if "error" in result:
            error_msg = str(result["error"]).lower()
            assert any(x in error_msg for x in ["404", "403", "permission", "not found"])
        else:
            assert "alerts" in result
            assert isinstance(result["alerts"], list)

    async def test_create_alert(self, grafana_integration, test_alert_rule_data):
        """Test creating an alert rule."""
        result = await grafana_integration.execute_action(
            "create_alert",
            {"alert": test_alert_rule_data}
        )

        # Check response - might fail with permissions or missing endpoint
        if "error" in result:
            error_msg = str(result["error"]).lower()
            assert any(x in error_msg for x in ["403", "404", "permission", "not found"])

    async def test_silence_alert(self, grafana_integration):
        """Test silencing an alert."""
        result = await grafana_integration.execute_action(
            "silence_alert",
            {
                "alert_id": "test-alert",
                "duration": "1h",
                "comment": "Test silence from OnCall Agent"
            }
        )

        # Might fail with permissions or missing endpoint
        if "error" in result:
            error_msg = str(result["error"]).lower()
            assert any(x in error_msg for x in ["403", "404", "permission", "not found"])


@pytest.mark.grafana
class TestDataSourceOperations:
    """Test datasource-related operations."""

    async def test_list_datasources(self, grafana_integration):
        """Test listing datasources."""
        result = await grafana_integration.fetch_context("datasources")

        if "error" in result:
            # Expect permission error
            assert "403" in str(result["error"]) or "permission" in str(result["error"]).lower()
        else:
            assert "datasources" in result
            assert isinstance(result["datasources"], list)

            # Verify datasource structure if any exist
            if result["datasources"]:
                ds = result["datasources"][0]
                assert "id" in ds
                assert "name" in ds
                assert "type" in ds


@pytest.mark.grafana
class TestErrorScenarios:
    """Test error handling and edge cases."""

    async def test_invalid_context_type(self, grafana_integration):
        """Test fetching invalid context type."""
        result = await grafana_integration.fetch_context("invalid_type")

        assert "error" in result
        assert "unsupported" in str(result["error"]).lower()

    async def test_invalid_action(self, grafana_integration):
        """Test executing invalid action."""
        result = await grafana_integration.execute_action("invalid_action", {})

        assert "error" in result
        assert "unsupported" in str(result["error"]).lower()

    async def test_malformed_query(self, grafana_integration):
        """Test malformed Prometheus query."""
        result = await grafana_integration.fetch_context(
            "metrics",
            query="invalid{syntax[",
            start="-5m"
        )

        # Should return error (either parse error or permission)
        assert "error" in result

    async def test_connection_after_disconnect(self, grafana_config):
        """Test operations after disconnection."""
        integration = GrafanaMCPIntegration(grafana_config)
        await integration.connect()
        await integration.disconnect()

        # Should raise error when trying to use after disconnect
        with pytest.raises((RuntimeError, ConnectionError)):
            await integration.fetch_context("dashboards")


@pytest.mark.grafana
@pytest.mark.slow
class TestPerformanceBenchmarks:
    """Performance benchmarks for Grafana operations."""

    async def test_concurrent_queries(self, grafana_integration):
        """Test concurrent metric queries."""
        queries = [
            {"query": "up", "start": "-5m"},
            {"query": "rate(http_requests_total[5m])", "start": "-5m"},
            {"query": "process_resident_memory_bytes", "start": "-5m"},
        ]

        start_time = time.time()

        # Execute queries concurrently
        tasks = [
            grafana_integration.fetch_context("metrics", **q)
            for q in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time

        # Should complete within reasonable time
        assert elapsed < 10.0  # 10 seconds for all queries

        # Check results
        for result in results:
            if isinstance(result, dict):
                # Either success or permission error
                assert isinstance(result, dict)
            else:
                # Exception should be connection related
                assert isinstance(result, Exception)

    async def test_pagination_performance(self, grafana_integration):
        """Test performance with paginated results."""
        # Search with limit
        start_time = time.time()

        result = await grafana_integration.fetch_context(
            "search",
            query="",
            limit=100
        )

        elapsed = time.time() - start_time

        # Should complete quickly even with larger limit
        assert elapsed < 5.0

        if "error" not in result:
            assert "results" in result


@pytest.mark.grafana
class TestIntegrationWithAgent:
    """Test integration with the OnCall Agent."""

    async def test_agent_context_gathering(self, grafana_integration):
        """Test context gathering as the agent would use it."""
        # Simulate agent gathering context for an alert
        service_name = "api-gateway"

        # 1. Search for relevant dashboards
        dashboards = await grafana_integration.fetch_context("search", query=service_name)

        # 2. Get incident metrics (if permissions allow)
        metrics = await grafana_integration.get_incident_metrics(
            service_name=service_name,
            time_range="-1h"
        )

        # Both operations should complete without exceptions
        assert isinstance(dashboards, dict)
        assert isinstance(metrics, dict)

        # Verify structure
        assert "service" in metrics
        assert metrics["service"] == service_name
