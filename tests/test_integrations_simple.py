#!/usr/bin/env python3
"""Simple test script to verify all MCP integrations without Docker."""

import asyncio
import logging
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration

async def test_integrations():
    """Test all available integrations with a comprehensive scenario."""
    load_dotenv()
    
    # Set up logging
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=== Starting Integration Test ===")
    logger.info("This test will check all configured integrations")
    
    try:
        # Initialize the agent
        agent = OncallAgent()
        
        # Register Notion integration manually (since GitHub is auto-registered)
        config = get_config()
        
        if config.notion_token:
            logger.info("📝 Registering Notion integration...")
            notion_integration = NotionDirectIntegration({
                "notion_token": config.notion_token,
                "database_id": config.notion_database_id,
                "notion_version": config.notion_version
            })
            agent.register_mcp_integration("notion", notion_integration)
        
        # Check what integrations are registered
        logger.info(f"\n📋 Registered integrations: {list(agent.mcp_integrations.keys())}")
        
        # Connect all integrations
        logger.info("\n🔌 Connecting to all integrations...")
        await agent.connect_integrations()
        
        # Create a test alert that would benefit from multiple integrations
        logger.info("\n🚨 Creating comprehensive test alert...")
        test_alert = PagerAlert(
            alert_id="INTEGRATION-TEST-001",
            severity="high",
            service_name="api-gateway",
            description="API Gateway experiencing database connection errors after deployment",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "error_type": "DatabaseConnectionTimeout",
                "error_rate": "35%",
                "deployment_id": "deploy-123",
                "git_commit": "abc123def",
                "affected_pods": ["api-gateway-pod-1", "api-gateway-pod-2"],
                "duration": "10 minutes",
                "region": "us-east-1"
            }
        )
        
        logger.info(f"Alert: {test_alert.alert_id} - {test_alert.description}")
        
        # Process the alert
        logger.info("\n🤖 Processing alert with AI analysis...")
        result = await agent.handle_pager_alert(test_alert)
        
        # Display integration status
        logger.info("\n📊 === INTEGRATION STATUS ===")
        available_integrations = result.get('available_integrations', [])
        
        # Check each integration
        integrations_status = {
            "notion": "✅" if "notion" in available_integrations else "❌",
            "github": "✅" if "github" in available_integrations else "❌",
            "kubernetes": "✅" if "kubernetes" in available_integrations else "❌"
        }
        
        for integration, status in integrations_status.items():
            logger.info(f"{status} {integration.capitalize()}")
        
        # Show context data gathered
        context_data = result.get('context_data', {})
        logger.info("\n📁 === CONTEXT DATA GATHERED ===")
        
        for integration_name, data in context_data.items():
            logger.info(f"\n{integration_name.upper()}:")
            if isinstance(data, dict) and 'error' in data:
                logger.warning(f"  Error: {data['error']}")
            else:
                logger.info(f"  Data retrieved successfully")
                if integration_name == "github" and isinstance(data, dict):
                    if 'recent_commits' in data:
                        logger.info("  - Recent commits fetched")
                    if 'open_issues' in data:
                        logger.info("  - Open issues retrieved")
                    if 'actions_status' in data:
                        logger.info("  - GitHub Actions status checked")
        
        # Display AI Analysis snippet
        if result.get('analysis'):
            logger.info("\n🧠 === AI ANALYSIS (snippet) ===")
            analysis_lines = result['analysis'].split('\n')[:10]
            for line in analysis_lines:
                print(line)
            print("... [truncated]")
        
        # Create documentation in Notion
        if "notion" in available_integrations:
            logger.info("\n📝 Creating comprehensive incident documentation in Notion...")
            try:
                notion_integration = agent.mcp_integrations["notion"]
                
                # Enhance the incident data with all context
                enhanced_alert_data = {
                    "alert_id": test_alert.alert_id,
                    "service_name": test_alert.service_name,
                    "severity": test_alert.severity,
                    "description": test_alert.description,
                    "metadata": test_alert.metadata,
                    "timestamp": test_alert.timestamp,
                    "analysis_summary": result.get('analysis', '').split('\n')[0:5],  # First 5 lines
                    "integrations_used": available_integrations,
                    "github_context": context_data.get('github', {}) if 'github' in context_data else None,
                    "kubernetes_context": context_data.get('kubernetes', {}) if 'kubernetes' in context_data else None
                }
                
                doc_result = await notion_integration.create_incident_documentation(enhanced_alert_data)
                
                if doc_result.get('success'):
                    logger.info("✅ Notion documentation created successfully")
                    logger.info(f"   Page ID: {doc_result.get('page_id')}")
                    logger.info(f"   Page URL: {doc_result.get('url')}")
                else:
                    logger.error(f"❌ Failed to create documentation: {doc_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error creating Notion documentation: {e}")
        
        # Summary
        logger.info("\n✅ === TEST SUMMARY ===")
        working_integrations = [k for k, v in integrations_status.items() if v == "✅"]
        failed_integrations = [k for k, v in integrations_status.items() if v == "❌"]
        
        logger.info(f"Working integrations: {', '.join(working_integrations) if working_integrations else 'None'}")
        logger.info(f"Failed integrations: {', '.join(failed_integrations) if failed_integrations else 'None'}")
        logger.info(f"AI Analysis: {'✅ Generated' if result.get('analysis') else '❌ Failed'}")
        
        # Provide setup instructions for failed integrations
        if failed_integrations:
            logger.info("\n📋 === SETUP INSTRUCTIONS FOR FAILED INTEGRATIONS ===")
            if "github" in failed_integrations:
                logger.info("\nGitHub Integration:")
                logger.info("1. Ensure GITHUB_TOKEN is set in .env")
                logger.info("2. Check if github-mcp-server is installed")
                logger.info("3. Verify the token has appropriate permissions")
            
            if "kubernetes" in failed_integrations:
                logger.info("\nKubernetes Integration:")
                logger.info("1. Install kubectl: https://kubernetes.io/docs/tasks/tools/")
                logger.info("2. Set KUBECONFIG environment variable")
                logger.info("3. Ensure you have cluster access")
        
        # Shutdown
        await agent.shutdown()
        
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("\n🔚 Integration test completed")


if __name__ == "__main__":
    asyncio.run(test_integrations())