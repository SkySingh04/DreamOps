#!/usr/bin/env python3
"""Test all three MCP integrations: Notion, GitHub, and Kubernetes."""

import asyncio
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration
from src.oncall_agent.mcp_integrations.github_mcp import GitHubMCPIntegration

async def main():
    """Test all three integrations together."""
    load_dotenv()
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=== Testing All Three MCP Integrations ===")
    
    try:
        # Initialize agent
        agent = OncallAgent()
        config = get_config()
        
        # Manually register GitHub integration
        if config.github_token:
            logger.info("🐙 Registering GitHub integration...")
            github_integration = GitHubMCPIntegration({
                "github_token": config.github_token,
                "mcp_server_path": config.github_mcp_server_path,
                "server_host": config.github_mcp_host,
                "server_port": config.github_mcp_port
            })
            agent.register_mcp_integration("github", github_integration)
        
        # Register Notion integration
        if config.notion_token:
            logger.info("📝 Registering Notion integration...")
            notion_integration = NotionDirectIntegration({
                "notion_token": config.notion_token,
                "database_id": config.notion_database_id,
                "notion_version": config.notion_version
            })
            agent.register_mcp_integration("notion", notion_integration)
        
        logger.info(f"📋 Registered integrations: {list(agent.mcp_integrations.keys())}")
        
        # Connect all
        await agent.connect_integrations()
        
        # Create test alert
        alert = PagerAlert(
            alert_id="THREE-MCP-TEST",
            severity="high",
            service_name="api-gateway",
            description="Testing all three MCP integrations together",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "test": "true",
                "integrations": ["notion", "github", "kubernetes"]
            }
        )
        
        # Process alert
        logger.info("🤖 Processing alert...")
        result = await agent.handle_pager_alert(alert)
        
        # Show results
        logger.info("\n✅ === RESULTS ===")
        logger.info(f"Available integrations: {result.get('available_integrations', [])}")
        
        # Create Notion documentation
        if "notion" in result.get('available_integrations', []):
            logger.info("\n📝 Creating Notion page...")
            notion_int = agent.mcp_integrations["notion"]
            doc = await notion_int.create_incident_documentation({
                "alert_id": alert.alert_id,
                "service_name": alert.service_name,
                "severity": alert.severity,
                "description": alert.description,
                "integrations_tested": result.get('available_integrations', [])
            })
            if doc.get('success'):
                logger.info(f"✅ Notion page created: {doc.get('url')}")
        
        await agent.shutdown()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())