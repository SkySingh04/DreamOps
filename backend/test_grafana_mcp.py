#!/usr/bin/env python
"""Test script for Grafana MCP integration."""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oncall_agent.mcp_integrations.grafana_mcp import GrafanaMCPIntegration
from oncall_agent.utils.logger import setup_logging


async def test_grafana_integration():
    """Test the Grafana MCP integration."""
    setup_logging()

    # Check for required environment variables
    grafana_url = os.getenv("GRAFANA_URL")
    grafana_api_key = os.getenv("GRAFANA_API_KEY")

    if not grafana_url:
        print("❌ GRAFANA_URL environment variable is required")
        print("Example: export GRAFANA_URL=https://your-grafana-instance.com")
        return

    if not grafana_api_key:
        print("❌ GRAFANA_API_KEY environment variable is required")
        print("Example: export GRAFANA_API_KEY=your-api-key")
        return

    print(f"🔧 Testing Grafana integration with URL: {grafana_url}")

    # Create integration config
    config = {
        "grafana_url": grafana_url,
        "grafana_api_key": grafana_api_key,
    }

    # Create integration instance
    integration = GrafanaMCPIntegration(config)

    try:
        # Test connection
        print("\n📡 Testing connection...")
        await integration.connect()
        print("✅ Connected successfully!")

        # Test fetching dashboards
        print("\n📊 Fetching dashboards...")
        dashboards = await integration.fetch_context("dashboards")
        if "error" not in dashboards:
            print(f"✅ Found {dashboards.get('count', 0)} dashboards")
            if dashboards.get("dashboards"):
                for i, dash in enumerate(dashboards["dashboards"][:3]):
                    print(f"   - {dash.get('title', 'Untitled')} (UID: {dash.get('uid', 'N/A')})")
                if len(dashboards["dashboards"]) > 3:
                    print(f"   ... and {len(dashboards['dashboards']) - 3} more")
        else:
            print(f"❌ Error fetching dashboards: {dashboards['error']}")

        # Test fetching alerts
        print("\n🚨 Fetching alerts...")
        alerts = await integration.fetch_context("alerts")
        if "error" not in alerts:
            alert_list = alerts.get("alerts", [])
            print(f"✅ Found {len(alert_list)} alerts")
            for i, alert in enumerate(alert_list[:3]):
                print(f"   - {alert.get('name', 'Unnamed')} (State: {alert.get('state', 'unknown')})")
            if len(alert_list) > 3:
                print(f"   ... and {len(alert_list) - 3} more")
        else:
            print(f"❌ Error fetching alerts: {alerts['error']}")

        # Test fetching datasources
        print("\n🔌 Fetching datasources...")
        datasources = await integration.fetch_context("datasources")
        if "error" not in datasources:
            ds_list = datasources.get("datasources", [])
            print(f"✅ Found {len(ds_list)} datasources")
            for ds in ds_list[:3]:
                print(f"   - {ds.get('name', 'Unnamed')} (Type: {ds.get('type', 'unknown')})")
            if len(ds_list) > 3:
                print(f"   ... and {len(ds_list) - 3} more")
        else:
            print(f"❌ Error fetching datasources: {datasources['error']}")

        # Test metrics query (if Prometheus datasource exists)
        print("\n📈 Testing metrics query...")
        test_query = "up"
        metrics = await integration.fetch_context("metrics", query=test_query, start="-5m")
        if "error" not in metrics:
            print(f"✅ Successfully queried metrics with '{test_query}'")
            if "data" in metrics and "result" in metrics["data"]:
                print(f"   Found {len(metrics['data']['result'])} series")
        else:
            print(f"❌ Error querying metrics: {metrics['error']}")

        # Test search functionality
        print("\n🔍 Testing search...")
        search_results = await integration.fetch_context("search", query="")
        if "error" not in search_results:
            results = search_results.get("results", [])
            print(f"✅ Search returned {len(results)} results")
        else:
            print(f"❌ Error searching: {search_results['error']}")

        # Test capabilities
        print("\n🛠️  Getting capabilities...")
        capabilities = await integration.get_capabilities()
        print("✅ Capabilities:")
        for category, items in capabilities.items():
            print(f"   {category}: {', '.join(items[:3])}")
            if len(items) > 3:
                print(f"              ... and {len(items) - 3} more")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Disconnect
        print("\n🔌 Disconnecting...")
        await integration.disconnect()
        print("✅ Disconnected successfully!")


if __name__ == "__main__":
    print("🧪 Grafana MCP Integration Test")
    print("=" * 50)
    asyncio.run(test_grafana_integration())
