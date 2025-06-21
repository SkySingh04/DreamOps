#!/usr/bin/env python3
"""Test script to verify all MCP integrations (Notion, GitHub, Kubernetes) are working together."""

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
from src.oncall_agent.mcp_integrations.kubernetes import KubernetesMCPIntegration


async def test_all_integrations():
    """Test all three MCP integrations with a comprehensive scenario."""
    load_dotenv()
    
    # Set up logging
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=== Starting Multi-Integration Test ===")
    logger.info("Testing: Notion, GitHub, and Kubernetes MCP integrations")
    
    try:
        # Initialize the agent
        agent = OncallAgent()
        
        # Register all integrations
        config = get_config()
        
        # 1. Notion Integration
        if config.notion_token:
            logger.info("📝 Registering Notion integration...")
            notion_integration = NotionDirectIntegration({
                "notion_token": config.notion_token,
                "database_id": config.notion_database_id,
                "notion_version": config.notion_version
            })
            agent.register_mcp_integration("notion", notion_integration)
        
        # 2. GitHub Integration
        if config.github_token:
            logger.info("🐙 Registering GitHub integration...")
            github_integration = GitHubMCPIntegration({
                "github_token": config.github_token,
                "mcp_server_path": config.github_mcp_server_path,
                "server_host": config.github_mcp_host,
                "server_port": config.github_mcp_port
            })
            agent.register_mcp_integration("github", github_integration)
        
        # 3. Kubernetes Integration
        logger.info("☸️  Registering Kubernetes integration...")
        k8s_integration = KubernetesMCPIntegration({
            "kubeconfig_path": os.getenv("KUBECONFIG"),
            "namespace": "default"
        })
        agent.register_mcp_integration("kubernetes", k8s_integration)
        
        # Connect all integrations
        logger.info("\n🔌 Connecting to all integrations...")
        await agent.connect_integrations()
        
        # Create a comprehensive test alert that would benefit from all integrations
        logger.info("\n🚨 Creating test alert that requires all integrations...")
        test_alert = PagerAlert(
            alert_id="MULTI-TEST-001",
            severity="high",
            service_name="api-gateway",
            description="API Gateway pods are crashing with 'connection refused' errors to database after recent deployment",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "error_type": "DatabaseConnectionError",
                "pod_name": "api-gateway-7d9f8b6c5-x2n4m",
                "namespace": "production",
                "deployment_version": "v2.3.1",
                "error_count": "247",
                "duration": "15 minutes",
                "affected_endpoints": ["/api/v1/users", "/api/v1/orders"],
                "last_deployment": "2 hours ago",
                "deployment_commit": "a1b2c3d4"
            }
        )
        
        logger.info(f"Alert: {test_alert.alert_id} - {test_alert.description}")
        
        # Process the alert
        logger.info("\n🤖 Processing alert with Claude AI...")
        result = await agent.handle_pager_alert(test_alert)
        
        # Display the results
        logger.info("\n📊 === INTEGRATION TEST RESULTS ===")
        logger.info(f"Status: {result.get('status')}")
        logger.info(f"Available integrations: {', '.join(result.get('available_integrations', []))}")
        
        # Check Kubernetes context
        if 'kubernetes' in result.get('context_data', {}):
            k8s_data = result['context_data']['kubernetes']
            logger.info("\n☸️  Kubernetes Context:")
            if 'error' in k8s_data:
                logger.warning(f"  - Error: {k8s_data['error']}")
            else:
                logger.info("  - Pod status retrieved")
                logger.info("  - Logs fetched")
                logger.info("  - Events collected")
        
        # Check GitHub context
        if 'github' in result.get('context_data', {}):
            github_data = result['context_data']['github']
            logger.info("\n🐙 GitHub Context:")
            if 'error' in github_data:
                logger.warning(f"  - Error: {github_data['error']}")
            else:
                if 'recent_commits' in github_data:
                    logger.info("  - Recent commits retrieved")
                if 'open_issues' in github_data:
                    logger.info("  - Open issues fetched")
                if 'actions_status' in github_data:
                    logger.info("  - GitHub Actions status checked")
        
        # Display AI Analysis
        if result.get('analysis'):
            logger.info("\n🧠 === AI ANALYSIS ===")
            print(result['analysis'])
            logger.info("=" * 60)
        
        # Create documentation in Notion
        if "notion" in result.get('available_integrations', []):
            logger.info("\n📝 Creating incident documentation in Notion...")
            try:
                notion_integration = agent.mcp_integrations["notion"]
                doc_result = await notion_integration.create_incident_documentation({
                    "alert_id": test_alert.alert_id,
                    "service_name": test_alert.service_name,
                    "severity": test_alert.severity,
                    "description": test_alert.description,
                    "metadata": test_alert.metadata,
                    "analysis": result.get('analysis', 'No analysis available'),
                    "github_context": result.get('context_data', {}).get('github', {}),
                    "kubernetes_context": result.get('context_data', {}).get('kubernetes', {})
                })
                
                if doc_result.get('success'):
                    logger.info("✅ Notion documentation created successfully")
                    logger.info(f"   Page ID: {doc_result.get('page_id')}")
                    logger.info(f"   Page URL: {doc_result.get('url')}")
                else:
                    logger.error(f"❌ Failed to create Notion documentation: {doc_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error creating Notion documentation: {e}")
        
        # Test automated actions
        if result.get('automated_actions'):
            logger.info(f"\n🤖 Automated actions available: {len(result['automated_actions'])}")
            for action in result['automated_actions']:
                logger.info(f"  - {action.get('description', 'Unknown action')}")
        
        logger.info("\n✅ === MULTI-INTEGRATION TEST COMPLETE ===")
        logger.info("Summary:")
        logger.info(f"  - Notion: {'✓' if 'notion' in result.get('available_integrations', []) else '✗'}")
        logger.info(f"  - GitHub: {'✓' if 'github' in result.get('available_integrations', []) else '✗'}")
        logger.info(f"  - Kubernetes: {'✓' if 'kubernetes' in result.get('available_integrations', []) else '✗'}")
        logger.info(f"  - AI Analysis: {'✓' if result.get('analysis') else '✗'}")
        
        # Shutdown the agent
        await agent.shutdown()
        
    except Exception as e:
        logger.error(f"Error during integration test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("\n🔚 Test completed")


if __name__ == "__main__":
    asyncio.run(test_all_integrations())