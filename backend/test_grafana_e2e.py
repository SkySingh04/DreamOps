#!/usr/bin/env python
"""End-to-end test for Grafana MCP integration with the OnCall Agent."""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oncall_agent.agent import OncallAgent, PagerAlert
from oncall_agent.config import get_config
from oncall_agent.utils.logger import setup_logging


async def test_grafana_with_agent():
    """Test the full integration of Grafana MCP with the agent."""
    setup_logging()
    
    print("🧪 End-to-End Grafana MCP Integration Test")
    print("=" * 60)
    
    # Check environment
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY is required for the agent")
        return
    
    if not os.getenv("GRAFANA_URL"):
        print("❌ GRAFANA_URL is required")
        return
    
    if not os.getenv("GRAFANA_API_KEY"):
        print("❌ GRAFANA_API_KEY is required")
        return
    
    print("✅ Environment variables configured")
    print(f"   GRAFANA_URL: {os.getenv('GRAFANA_URL')}")
    print(f"   ANTHROPIC_API_KEY: {'*' * 20}...")
    print(f"   GRAFANA_API_KEY: {'*' * 20}...")
    
    # Get config and enable Grafana
    config = get_config()
    config.grafana_enabled = True
    config.grafana_url = os.getenv("GRAFANA_URL")
    config.grafana_api_key = os.getenv("GRAFANA_API_KEY")
    
    # Create agent
    print("\n📡 Initializing OnCall Agent...")
    agent = OncallAgent(config)
    
    try:
        # Initialize agent (this will connect integrations)
        print("🔧 Connecting integrations...")
        await agent.connect_integrations()
        
        # Check if Grafana is connected
        if "grafana" in agent.mcp_integrations:
            grafana = agent.mcp_integrations["grafana"]
            print("✅ Grafana integration registered")
            
            # Test health check
            print("\n🏥 Testing Grafana health check...")
            health = await grafana.health_check()
            if health:
                print("✅ Grafana is healthy")
            else:
                print("❌ Grafana health check failed")
        else:
            print("❌ Grafana integration not found in agent")
            return
        
        # Create a test alert that would benefit from Grafana context
        print("\n🚨 Creating test alert...")
        test_alert = PagerAlert(
            alert_id="test-grafana-001",
            service_name="api-gateway",
            severity="high",
            description="High error rate detected on api-gateway service. HTTP 5xx errors increased by 300% in the last 10 minutes.",
            source="CloudWatch",
            timestamp=datetime.now(),
            metadata={
                "metric": "http_errors_5xx",
                "threshold": "100",
                "current_value": "350",
                "namespace": "production"
            }
        )
        
        print(f"📋 Alert Details:")
        print(f"   Service: {test_alert.service_name}")
        print(f"   Severity: {test_alert.severity}")
        print(f"   Description: {test_alert.description[:80]}...")
        
        # Test individual Grafana operations first
        print("\n🔍 Testing Grafana operations directly...")
        
        # Test dashboard search
        print("\n1️⃣ Searching for dashboards...")
        dashboards = await grafana.fetch_context("search", query=test_alert.service_name)
        if "error" not in dashboards:
            results = dashboards.get("results", [])
            print(f"   ✅ Found {len(results)} related dashboards")
            for dash in results[:3]:
                print(f"      - {dash.get('title', 'Untitled')}")
        else:
            print(f"   ❌ Dashboard search failed: {dashboards.get('error')}")
        
        # Test metrics query
        print("\n2️⃣ Querying metrics...")
        metrics_result = await grafana.fetch_context(
            "metrics", 
            query=f'rate(http_requests_total{{service="{test_alert.service_name}",status=~"5.."}}[5m])',
            start="-15m"
        )
        if "error" not in metrics_result:
            print("   ✅ Successfully queried error rate metrics")
            if "data" in metrics_result and "result" in metrics_result.get("data", {}):
                series_count = len(metrics_result["data"]["result"])
                print(f"      Found {series_count} time series")
        else:
            print(f"   ❌ Metrics query failed: {metrics_result.get('error')}")
        
        # Test alerts fetch
        print("\n3️⃣ Fetching current alerts...")
        alerts = await grafana.fetch_context("alerts")
        if "error" not in alerts:
            alert_list = alerts.get("alerts", [])
            print(f"   ✅ Found {len(alert_list)} alerts in Grafana")
            active_alerts = [a for a in alert_list if a.get("state") == "alerting"]
            print(f"      {len(active_alerts)} are currently firing")
        else:
            print(f"   ❌ Alert fetch failed: {alerts.get('error')}")
        
        # Now test the full agent flow
        print("\n🤖 Testing full agent alert handling...")
        print("   This will:")
        print("   - Gather context from all integrations")
        print("   - Query Grafana for relevant metrics and dashboards")
        print("   - Generate an analysis using Claude")
        print("   - Provide resolution recommendations")
        
        input("\n⏸️  Press Enter to continue with full agent test...")
        
        # Handle the alert with the agent
        print("\n🚀 Processing alert with agent...")
        result = await agent.handle_pager_alert(test_alert)
        
        # Check results
        print("\n📊 Results:")
        if result.get("success"):
            print("✅ Alert processed successfully!")
            
            # Check if Grafana context was included
            context = result.get("context", {})
            if "grafana" in context:
                print("\n📈 Grafana context included:")
                grafana_context = context["grafana"]
                
                if "dashboards" in grafana_context:
                    dash_count = grafana_context["dashboards"].get("count", 0)
                    print(f"   - Found {dash_count} relevant dashboards")
                
                if "metrics" in grafana_context:
                    print("   - Metrics data included")
                
                if "service" in grafana_context:
                    print(f"   - Service context: {grafana_context['service']}")
            else:
                print("⚠️  No Grafana context in response")
            
            # Show analysis
            if "analysis" in result:
                print("\n🔍 Agent Analysis:")
                analysis = result["analysis"]
                print(f"   Summary: {analysis.get('summary', 'N/A')[:100]}...")
                
                if "recommended_actions" in analysis:
                    print("\n   Recommended Actions:")
                    for i, action in enumerate(analysis["recommended_actions"][:3], 1):
                        print(f"   {i}. {action}")
        else:
            print("❌ Alert processing failed")
            if "error" in result:
                print(f"   Error: {result['error']}")
        
        # Test incident metrics feature
        print("\n📊 Testing incident metrics collection...")
        incident_metrics = await grafana.get_incident_metrics(
            service_name=test_alert.service_name,
            time_range="-30m"
        )
        
        if "error" not in incident_metrics:
            print("✅ Successfully collected incident metrics:")
            metrics = incident_metrics.get("metrics", {})
            for metric_name, data in metrics.items():
                if isinstance(data, dict) and "data" in data:
                    print(f"   - {metric_name}: {len(data.get('data', {}).get('result', []))} series")
        else:
            print(f"❌ Failed to collect incident metrics: {incident_metrics.get('error')}")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        if "grafana" in agent.mcp_integrations:
            await agent.mcp_integrations["grafana"].disconnect()
        print("✅ Test completed")


async def quick_mcp_test():
    """Quick test to verify MCP server is working."""
    print("\n🔧 Quick MCP Server Test")
    print("-" * 40)
    
    # Check if binary exists
    mcp_path = Path(__file__).parent.parent / "mcp-grafana" / "dist" / "mcp-grafana"
    
    if not mcp_path.exists():
        print(f"❌ MCP server binary not found at: {mcp_path}")
        print("\n📝 To build the server:")
        print("   cd ../mcp-grafana")
        print("   go mod download")
        print("   make build")
        return False
    
    print(f"✅ MCP server binary found: {mcp_path}")
    
    # Try to run it
    import subprocess
    try:
        result = subprocess.run(
            [str(mcp_path), "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print(f"✅ MCP server version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ MCP server error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to run MCP server: {e}")
        return False


if __name__ == "__main__":
    # First do a quick MCP test
    asyncio.run(quick_mcp_test())
    
    # Then run the full test
    print("\n" + "=" * 60)
    asyncio.run(test_grafana_with_agent())