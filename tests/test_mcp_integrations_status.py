#!/usr/bin/env python3
"""
Test the status of all MCP integrations individually.
"""

import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
import httpx

import sys
sys.path.append('../backend')

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config


async def test_notion_integration(agent):
    """Test Notion MCP integration."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== TESTING NOTION INTEGRATION ===")
    
    if "notion" in agent.mcp_integrations:
        notion = agent.mcp_integrations["notion"]
        if notion.connected:
            logger.info("✅ Notion connected successfully")
            
            # Test creating a simple page
            try:
                result = await notion.create_incident_documentation({
                    "alert_id": "NOTION-TEST-001",
                    "service_name": "test-service",
                    "severity": "info",
                    "description": "Testing Notion integration",
                    "metadata": {"test": True}
                })
                
                if result.get('success'):
                    logger.info(f"✅ Created test page: {result.get('url')}")
                else:
                    logger.warning(f"⚠️ Page creation failed: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"❌ Notion test failed: {e}")
        else:
            logger.warning("⚠️ Notion not connected")
    else:
        logger.error("❌ Notion integration not registered")


async def test_grafana_integration(agent):
    """Test Grafana MCP integration."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== TESTING GRAFANA INTEGRATION ===")
    
    config = get_config()
    logger.info(f"Grafana URL: {config.grafana_url}")
    logger.info(f"API Key configured: {'Yes' if config.grafana_api_key and config.grafana_api_key != 'paste-your-service-account-token-here' else 'No'}")
    
    if "grafana" in agent.mcp_integrations:
        grafana = agent.mcp_integrations["grafana"]
        
        # Test direct API connection
        if config.grafana_url and config.grafana_api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{config.grafana_url}/api/org",
                        headers={"Authorization": f"Bearer {config.grafana_api_key}"},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        org_data = response.json()
                        logger.info(f"✅ Grafana API working - Organization: {org_data.get('name', 'Unknown')}")
                    elif response.status_code == 401:
                        logger.warning("⚠️ Grafana API key is invalid or expired")
                    else:
                        logger.warning(f"⚠️ Grafana API returned: {response.status_code}")
                        
            except Exception as e:
                logger.error(f"❌ Grafana API test failed: {e}")
        
        if grafana.connected:
            logger.info("✅ Grafana MCP integration connected")
        else:
            logger.warning("⚠️ Grafana MCP not connected (expected if binary not built)")
    else:
        logger.error("❌ Grafana integration not registered")


async def test_kubernetes_integration(agent):
    """Test Kubernetes MCP integration."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== TESTING KUBERNETES INTEGRATION ===")
    
    if "kubernetes" in agent.mcp_integrations:
        k8s = agent.mcp_integrations["kubernetes"]
        if k8s.connected:
            logger.info("✅ Kubernetes connected")
            
            # Test basic functionality
            try:
                result = await k8s.fetch_context("pod_list", namespace="default")
                if result and not result.get('error'):
                    logger.info("✅ Can fetch Kubernetes resources")
                else:
                    logger.warning(f"⚠️ Kubernetes fetch failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.warning(f"⚠️ Kubernetes test failed (expected in WSL): {e}")
        else:
            logger.warning("⚠️ Kubernetes not connected (kubectl not available)")
    else:
        logger.error("❌ Kubernetes integration not registered")


async def test_github_integration(agent):
    """Test GitHub MCP integration."""
    logger = logging.getLogger(__name__)
    logger.info("\n=== TESTING GITHUB INTEGRATION ===")
    
    config = get_config()
    logger.info(f"GitHub Token configured: {'Yes' if config.github_token else 'No'}")
    
    if "github" in agent.mcp_integrations:
        github = agent.mcp_integrations["github"]
        if github.connected:
            logger.info("✅ GitHub connected")
        else:
            logger.warning("⚠️ GitHub not connected")
    else:
        if not config.github_token:
            logger.info("ℹ️ GitHub integration not registered (no token configured)")
        else:
            logger.warning("⚠️ GitHub integration not auto-registered despite token")


async def main():
    """Run all integration tests."""
    load_dotenv()
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("🧪 Testing All MCP Integrations Status")
    logger.info("=" * 50)
    
    try:
        # Initialize agent
        agent = OncallAgent()
        
        # Show registered integrations
        logger.info(f"\nRegistered integrations: {list(agent.mcp_integrations.keys())}")
        
        # Connect all integrations
        logger.info("\n🔌 Connecting to integrations...")
        await agent.connect_integrations()
        
        # Test each integration
        await test_notion_integration(agent)
        await test_kubernetes_integration(agent)
        await test_grafana_integration(agent)
        await test_github_integration(agent)
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 INTEGRATION SUMMARY")
        logger.info("=" * 50)
        
        connected_count = 0
        for name, integration in agent.mcp_integrations.items():
            status = "✅ Connected" if integration.connected else "⚠️ Not connected"
            logger.info(f"{name.capitalize()}: {status}")
            if integration.connected:
                connected_count += 1
        
        logger.info(f"\nTotal: {connected_count}/{len(agent.mcp_integrations)} integrations connected")
        
        # Test a full alert processing
        logger.info("\n🚨 Testing Full Alert Processing...")
        test_alert = PagerAlert(
            alert_id="FULL-TEST-001",
            severity="medium",
            service_name="test-service",
            description="Testing all integrations together",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={"test": True}
        )
        
        result = await agent.handle_pager_alert(test_alert)
        
        if result.get('analysis'):
            logger.info("✅ AI analysis generated successfully")
        else:
            logger.error("❌ AI analysis failed")
            
        if result.get('available_integrations'):
            logger.info(f"✅ Available integrations during processing: {result['available_integrations']}")
        
        # Cleanup
        await agent.shutdown()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    logger.info("\n🏁 Integration status check completed")


if __name__ == "__main__":
    asyncio.run(main())