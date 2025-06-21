#!/usr/bin/env python3
"""Test all four MCP integrations: Notion, GitHub, Kubernetes, and Grafana."""

import asyncio
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

import sys
sys.path.append('../backend')

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration
from src.oncall_agent.mcp_integrations.grafana_mcp import GrafanaMCPIntegration

async def main():
    """Test all four integrations working together."""
    load_dotenv()
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=== Testing All Four MCP Integrations ===")
    logger.info("Testing: Notion, GitHub, Kubernetes, and Grafana")
    
    try:
        # Initialize agent (auto-registers Kubernetes and Grafana if configured)
        agent = OncallAgent()
        config = get_config()
        
        # Manually register Notion integration
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
        
        # Create a comprehensive test alert that would benefit from all integrations
        logger.info("\n🚨 Creating comprehensive test alert...")
        test_alert = PagerAlert(
            alert_id="ALL-INTEGRATIONS-TEST",
            severity="high",
            service_name="api-gateway",
            description="API Gateway pods experiencing high error rates and database connection timeouts after deployment",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "error_type": "DatabaseConnectionTimeout",
                "error_rate": "45%",
                "affected_pods": ["api-gateway-pod-1", "api-gateway-pod-2"],
                "namespace": "production",
                "deployment_commit": "abc123def",
                "duration": "12 minutes",
                "region": "us-east-1",
                "metrics_available": True,
                "dashboards": ["API Gateway Performance", "Database Connections"]
            }
        )
        
        logger.info(f"Alert: {test_alert.alert_id} - {test_alert.description}")
        
        # Process the alert
        logger.info("\n🤖 Processing alert with AI analysis...")
        result = await agent.handle_pager_alert(test_alert)
        
        # Display integration status
        logger.info("\n📊 === INTEGRATION STATUS ===")
        available_integrations = result.get('available_integrations', [])
        
        integrations_status = {
            "notion": "✅" if "notion" in available_integrations else "❌",
            "github": "✅" if "github" in available_integrations else "❌", 
            "kubernetes": "✅" if "kubernetes" in available_integrations else "❌",
            "grafana": "✅" if "grafana" in available_integrations else "❌"
        }
        
        for integration, status in integrations_status.items():
            logger.info(f"{status} {integration.capitalize()}")
        
        # Show context data gathered from each integration
        context_data = result.get('context_data', {})
        logger.info("\n📁 === CONTEXT DATA GATHERED ===")
        
        for integration_name, data in context_data.items():
            logger.info(f"\n{integration_name.upper()}:")
            if isinstance(data, dict) and 'error' in data:
                logger.warning(f"  ❌ Error: {data['error']}")
            else:
                logger.info(f"  ✅ Data retrieved successfully")
                
                # Show specific context for each integration
                if integration_name == "kubernetes" and isinstance(data, dict):
                    if 'pods' in data:
                        logger.info("  - Pod information fetched")
                    if 'events' in data:
                        logger.info("  - Kubernetes events retrieved")
                    if 'logs' in data:
                        logger.info("  - Container logs accessed")
                
                elif integration_name == "grafana" and isinstance(data, dict):
                    if 'dashboards' in data:
                        logger.info("  - Dashboards listed")
                    if 'metrics' in data:
                        logger.info("  - Metrics data retrieved")
                    if 'alerts' in data:
                        logger.info("  - Grafana alerts checked")
                
                elif integration_name == "github" and isinstance(data, dict):
                    if 'recent_commits' in data:
                        logger.info("  - Recent commits fetched")
                    if 'open_issues' in data:
                        logger.info("  - Open issues retrieved")
                    if 'actions_status' in data:
                        logger.info("  - GitHub Actions checked")
        
        # Display AI Analysis snippet
        if result.get('analysis'):
            logger.info("\n🧠 === AI ANALYSIS (first 10 lines) ===")
            analysis_lines = result['analysis'].split('\n')[:10]
            for line in analysis_lines:
                print(line)
            print("... [truncated]")
        
        # Create comprehensive documentation in Notion
        if "notion" in available_integrations:
            logger.info("\n📝 Creating comprehensive incident documentation...")
            try:
                notion_integration = agent.mcp_integrations["notion"]
                
                # Enhanced alert data with all integration context
                enhanced_data = {
                    "alert_id": test_alert.alert_id,
                    "service_name": test_alert.service_name,
                    "severity": test_alert.severity,
                    "description": test_alert.description,
                    "metadata": test_alert.metadata,
                    "timestamp": test_alert.timestamp,
                    "integrations_used": available_integrations,
                    "context_summary": {
                        "kubernetes": "Pod status and logs" if "kubernetes" in context_data else "Not available",
                        "grafana": "Metrics and dashboards" if "grafana" in context_data else "Not available", 
                        "github": "Recent commits and issues" if "github" in context_data else "Not available"
                    },
                    "ai_analysis_preview": result.get('analysis', '').split('\n')[0:3] if result.get('analysis') else []
                }
                
                doc_result = await notion_integration.create_incident_documentation(enhanced_data)
                
                if doc_result.get('success'):
                    logger.info("✅ Comprehensive documentation created in Notion")
                    logger.info(f"   Page ID: {doc_result.get('page_id')}")
                    logger.info(f"   Page URL: {doc_result.get('url')}")
                else:
                    logger.error(f"❌ Failed to create documentation: {doc_result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error creating Notion documentation: {e}")
        
        # Summary
        logger.info("\n✅ === COMPREHENSIVE TEST SUMMARY ===")
        working_count = sum(1 for status in integrations_status.values() if status == "✅")
        total_count = len(integrations_status)
        
        logger.info(f"Working integrations: {working_count}/{total_count}")
        logger.info(f"Integration details:")
        for integration, status in integrations_status.items():
            logger.info(f"  - {integration.capitalize()}: {status}")
        
        logger.info(f"AI Analysis: {'✅ Generated' if result.get('analysis') else '❌ Failed'}")
        logger.info(f"Notion Documentation: {'✅ Created' if 'notion' in available_integrations else '❌ Skipped'}")
        
        # Provide setup guidance for missing integrations
        missing_integrations = [k for k, v in integrations_status.items() if v == "❌"]
        if missing_integrations:
            logger.info(f"\n📋 === SETUP GUIDANCE ===")
            logger.info(f"Missing integrations: {', '.join(missing_integrations)}")
            
            if "grafana" in missing_integrations:
                logger.info("\nGrafana Integration Setup:")
                logger.info("1. Set GRAFANA_URL in .env (e.g., http://localhost:3000)")
                logger.info("2. Set GRAFANA_API_KEY in .env")
                logger.info("3. Ensure mcp-grafana server is built and accessible")
            
            if "github" in missing_integrations:
                logger.info("\nGitHub Integration Setup:")
                logger.info("1. Ensure GITHUB_TOKEN is set in .env")
                logger.info("2. Check if github-mcp-server is available")
            
            if "kubernetes" in missing_integrations:
                logger.info("\nKubernetes Integration Setup:")
                logger.info("1. Install kubectl")
                logger.info("2. Configure KUBECONFIG")
                logger.info("3. Ensure cluster access")
        
        # Performance metrics
        logger.info(f"\n⏱️  === PERFORMANCE ===")
        logger.info(f"Alert processed in: ~{(datetime.now() - datetime.fromisoformat(test_alert.timestamp.replace('Z', '+00:00'))).total_seconds():.1f}s")
        logger.info(f"Integrations connected: {working_count}")
        logger.info(f"Context sources: {len(context_data)}")
        
        # Cleanup
        await agent.shutdown()
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("\n🔚 Comprehensive integration test completed")

if __name__ == "__main__":
    asyncio.run(main())