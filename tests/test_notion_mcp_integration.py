#!/usr/bin/env python3
"""
Test the Notion MCP integration to ensure AI agent is talking to the Notion MCP server.
"""

import asyncio
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

import sys
sys.path.append('../backend')

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config


async def test_notion_mcp_integration():
    """Test that the AI agent uses the Notion MCP server."""
    load_dotenv()
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=== Testing Notion MCP Integration ===")
    logger.info("Verifying AI agent communicates with Notion MCP server")
    
    try:
        config = get_config()
        
        # Check configuration
        if not config.notion_token:
            logger.error("❌ NOTION_TOKEN not found in .env file")
            return
            
        logger.info(f"✅ NOTION_TOKEN configured")
        logger.info(f"📊 Database ID: {config.notion_database_id or 'Not set (will use workspace)'}")
        
        # Initialize agent (should auto-register Notion MCP integration)
        logger.info("🤖 Initializing AI agent...")
        agent = OncallAgent()
        
        # Check if Notion integration was registered
        if "notion" in agent.mcp_integrations:
            logger.info("✅ Notion MCP integration registered automatically")
            notion_integration = agent.mcp_integrations["notion"]
            logger.info(f"   Integration type: {type(notion_integration).__name__}")
        else:
            logger.error("❌ Notion MCP integration not registered")
            return
        
        # Connect to integrations
        logger.info("🔌 Connecting to MCP integrations...")
        await agent.connect_integrations()
        
        # Check connection status
        if notion_integration.connected:
            logger.info("✅ Successfully connected to Notion MCP server")
            logger.info(f"   Connected at: {notion_integration.connection_time}")
        else:
            logger.warning("⚠️ Notion MCP server connection failed, will use fallback")
        
        # Create a test alert for EKS incident
        logger.info("\n🚨 Creating test alert for EKS pod crash...")
        test_alert = PagerAlert(
            alert_id="MCP-TEST-001",
            severity="high", 
            service_name="payment-service",
            description="Pod payment-service-7d9f8b6c5-x2n4m is in CrashLoopBackOff state with 6 restarts",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "namespace": "production",
                "pod_name": "payment-service-7d9f8b6c5-x2n4m",
                "restart_count": 6,
                "error_message": "Configuration file /config/app.conf not found",
                "cluster": "production-eks",
                "region": "us-west-2",
                "mcp_test": True
            }
        )
        
        logger.info(f"   Alert ID: {test_alert.alert_id}")
        logger.info(f"   Service: {test_alert.service_name}")
        logger.info(f"   Description: {test_alert.description}")
        
        # Process alert through full agent
        logger.info("\n🤖 Processing alert through AI agent...")
        result = await agent.handle_pager_alert(test_alert)
        
        # Analyze results
        logger.info("\n📊 === PROCESSING RESULTS ===")
        available_integrations = result.get('available_integrations', [])
        
        if "notion" in available_integrations:
            logger.info("✅ Notion integration participated in alert processing")
        else:
            logger.warning("⚠️ Notion integration was not available during processing")
        
        # Check if AI analysis was generated
        if result.get('analysis'):
            logger.info("✅ AI analysis generated successfully")
            analysis_preview = result['analysis'][:300] + "..." if len(result['analysis']) > 300 else result['analysis']
            logger.info(f"   Preview: {analysis_preview}")
        else:
            logger.warning("⚠️ No AI analysis generated")
        
        # Test direct incident documentation creation
        logger.info("\n📝 Testing direct incident documentation creation...")
        try:
            alert_data = {
                "alert_id": test_alert.alert_id,
                "service_name": test_alert.service_name,
                "severity": test_alert.severity,
                "description": test_alert.description,
                "metadata": test_alert.metadata,
                "timestamp": test_alert.timestamp
            }
            
            doc_result = await notion_integration.create_incident_documentation(alert_data)
            
            if doc_result.get('success'):
                logger.info("✅ Incident documentation created successfully")
                logger.info(f"   Page ID: {doc_result.get('page_id')}")
                logger.info(f"   Page URL: {doc_result.get('url')}")
                logger.info(f"   Created via: {doc_result.get('created_via')}")
                
                if doc_result.get('created_via') == 'mcp_server':
                    logger.info("🎉 SUCCESS: Using actual Notion MCP server!")
                elif doc_result.get('created_via') == 'mock':
                    logger.warning("⚠️ Using mock fallback (MCP server not working)")
                else:
                    logger.info("ℹ️ Using alternative method")
                    
            else:
                logger.error(f"❌ Failed to create documentation: {doc_result.get('error')}")
                
        except Exception as e:
            logger.error(f"❌ Documentation creation failed: {e}")
        
        # Test MCP capabilities
        logger.info("\n🔧 Testing MCP capabilities...")
        try:
            capabilities = await notion_integration.get_capabilities()
            logger.info("✅ Retrieved MCP capabilities:")
            for category, items in capabilities.items():
                logger.info(f"   {category}: {items}")
        except Exception as e:
            logger.error(f"❌ Failed to get capabilities: {e}")
        
        # Summary
        logger.info("\n📋 === TEST SUMMARY ===")
        
        checks = [
            ("Notion token configured", bool(config.notion_token)),
            ("Notion integration registered", "notion" in agent.mcp_integrations),
            ("MCP server connection", notion_integration.connected),
            ("AI agent processing", bool(result.get('analysis'))),
            ("Incident documentation", doc_result.get('success', False) if 'doc_result' in locals() else False)
        ]
        
        passed = sum(1 for _, status in checks if status)
        total = len(checks)
        
        logger.info(f"Test results: {passed}/{total} checks passed")
        
        for check_name, status in checks:
            status_icon = "✅" if status else "❌"
            logger.info(f"   {status_icon} {check_name}")
        
        if notion_integration.connected:
            logger.info("\n🎉 SUCCESS: AI agent is communicating with Notion MCP server!")
        else:
            logger.info("\n⚠️ PARTIAL: AI agent has Notion integration but MCP server connection failed")
            logger.info("   Check if Node.js is installed and Notion MCP server is accessible")
        
        # Cleanup
        await agent.shutdown()
        logger.info("🔚 Test completed")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_notion_mcp_integration())