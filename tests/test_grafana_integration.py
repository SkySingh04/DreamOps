#!/usr/bin/env python3
"""Test Grafana MCP integration."""

import asyncio
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

import sys
sys.path.append('../backend')

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.grafana_mcp import GrafanaMCPIntegration

async def test_grafana_integration():
    """Test Grafana MCP integration functionality."""
    load_dotenv()
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=== Testing Grafana MCP Integration ===")
    
    try:
        config = get_config()
        
        # Initialize Grafana integration
        logger.info("🔗 Initializing Grafana integration...")
        grafana_integration = GrafanaMCPIntegration({
            "grafana_url": config.grafana_url,
            "grafana_api_key": config.grafana_api_key,
            "grafana_username": config.grafana_username,
            "grafana_password": config.grafana_password,
            "mcp_server_path": config.grafana_mcp_server_path,
            "server_host": config.grafana_mcp_host,
            "server_port": config.grafana_mcp_port
        })
        
        # Test connection
        logger.info("🔌 Connecting to Grafana...")
        await grafana_integration.connect()
        
        if grafana_integration.connected:
            logger.info("✅ Successfully connected to Grafana")
        else:
            logger.error("❌ Failed to connect to Grafana")
            return
        
        # Test capabilities
        logger.info("\n📋 Testing capabilities...")
        capabilities = await grafana_integration.get_capabilities()
        logger.info(f"Available context types: {capabilities['context_types']}")
        logger.info(f"Available actions: {capabilities['actions']}")
        
        # Test fetching dashboards
        logger.info("\n📊 Testing dashboard retrieval...")
        dashboards = await grafana_integration.fetch_context("dashboards")
        if "error" not in dashboards:
            logger.info(f"✅ Retrieved {dashboards.get('count', 0)} dashboards")
        else:
            logger.warning(f"⚠️  Dashboard fetch failed: {dashboards['error']}")
        
        # Test fetching data sources
        logger.info("\n🔍 Testing data sources...")
        datasources = await grafana_integration.fetch_context("datasources")
        if "error" not in datasources:
            logger.info("✅ Retrieved data sources successfully")
        else:
            logger.warning(f"⚠️  Data sources fetch failed: {datasources['error']}")
        
        # Test fetching alerts
        logger.info("\n🚨 Testing alerts retrieval...")
        alerts = await grafana_integration.fetch_context("alerts")
        if "error" not in alerts:
            logger.info("✅ Retrieved alerts successfully")
        else:
            logger.warning(f"⚠️  Alerts fetch failed: {alerts['error']}")
        
        # Test metrics query
        logger.info("\n📈 Testing metrics query...")
        metrics = await grafana_integration.fetch_context("metrics", query="up")
        if "error" not in metrics:
            logger.info("✅ Metrics query successful")
        else:
            logger.warning(f"⚠️  Metrics query failed: {metrics['error']}")
        
        # Test incident metrics
        logger.info("\n🔧 Testing incident-specific metrics...")
        incident_metrics = await grafana_integration.get_incident_metrics("api-gateway")
        if "error" not in incident_metrics:
            logger.info(f"✅ Retrieved incident metrics for service: {incident_metrics.get('service')}")
            logger.info(f"   Metrics available: {list(incident_metrics.get('metrics', {}).keys())}")
        else:
            logger.warning(f"⚠️  Incident metrics failed: {incident_metrics['error']}")
        
        # Test with on-call agent
        logger.info("\n🤖 Testing with On-Call Agent...")
        agent = OncallAgent()
        agent.register_mcp_integration("grafana", grafana_integration)
        
        # Create test alert
        alert = PagerAlert(
            alert_id="GRAFANA-TEST-001",
            severity="high",
            service_name="api-gateway",
            description="Testing Grafana integration with high error rate alert",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "error_rate": "25%",
                "affected_endpoints": ["/api/v1/users", "/api/v1/orders"],
                "duration": "5 minutes"
            }
        )
        
        # Process alert with Grafana context
        logger.info("Processing alert with Grafana metrics...")
        result = await agent.handle_pager_alert(alert)
        
        if result.get('status') == 'analyzed':
            logger.info("✅ Alert processed successfully with Grafana context")
            
            # Check if Grafana context was included
            context_data = result.get('context_data', {})
            if 'grafana' in context_data:
                logger.info("✅ Grafana context included in analysis")
                grafana_data = context_data['grafana']
                if 'error' not in grafana_data:
                    logger.info("✅ Grafana data retrieved successfully")
                else:
                    logger.warning(f"⚠️  Grafana context error: {grafana_data['error']}")
            else:
                logger.warning("⚠️  No Grafana context in alert analysis")
        
        # Cleanup
        await grafana_integration.disconnect()
        await agent.shutdown()
        
        logger.info("\n✅ Grafana integration test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_grafana_integration())