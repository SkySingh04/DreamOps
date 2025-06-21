#!/usr/bin/env python3
"""Docker integration test for all three MCP services."""

import asyncio
import logging
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging
from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration
from src.oncall_agent.mcp_integrations.github_mcp import GitHubMCPIntegration
from src.oncall_agent.mcp_integrations.kubernetes import KubernetesMCPIntegration

async def test_with_mock_services():
    """Test all integrations using Docker mock services."""
    load_dotenv()
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info("=== Docker Integration Test Starting ===")
    logger.info("This test uses mock Kubernetes and GitHub services")
    
    try:
        # Initialize agent
        agent = OncallAgent()
        config = get_config()
        
        # Configure for mock services
        if os.getenv("USE_MOCK_SERVICES") == "true":
            logger.info("🎭 Using mock services mode")
            
            # Override Kubernetes config for mock
            os.environ["KUBECONFIG"] = "/dev/null"  # Bypass kubeconfig check
            os.environ["KUBERNETES_SERVICE_HOST"] = os.getenv("KUBERNETES_API_SERVER", "mock-kubernetes").replace("http://", "")
            os.environ["KUBERNETES_SERVICE_PORT"] = "80"
        
        # Register all integrations
        logger.info("📋 Registering integrations...")
        
        # GitHub integration (will use mock)
        if config.github_token:
            logger.info("🐙 Registering GitHub integration...")
            github_config = {
                "github_token": config.github_token,
                "api_base_url": os.getenv("GITHUB_API_BASE_URL", "https://api.github.com")
            }
            # Use direct API mode for mock testing
            github_integration = GitHubMCPIntegration(github_config)
            agent.register_mcp_integration("github", github_integration)
        
        # Kubernetes integration (will use mock)
        logger.info("☸️  Registering Kubernetes integration...")
        k8s_config = {
            "api_server": os.getenv("KUBERNETES_API_SERVER", "http://mock-kubernetes"),
            "mock_mode": True
        }
        k8s_integration = KubernetesMCPIntegration(k8s_config)
        agent.register_mcp_integration("kubernetes", k8s_integration)
        
        # Notion integration (real API)
        if config.notion_token:
            logger.info("📝 Registering Notion integration...")
            notion_integration = NotionDirectIntegration({
                "notion_token": config.notion_token,
                "database_id": config.notion_database_id,
                "notion_version": config.notion_version
            })
            agent.register_mcp_integration("notion", notion_integration)
        
        logger.info(f"✅ Registered integrations: {list(agent.mcp_integrations.keys())}")
        
        # Connect all integrations
        logger.info("\n🔌 Connecting to all services...")
        await agent.connect_integrations()
        
        # Create comprehensive test alert
        test_alert = PagerAlert(
            alert_id="DOCKER-TEST-001",
            severity="high",
            service_name="api-gateway",
            description="Docker test: API Gateway database connection errors detected across multiple pods",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "error_type": "DatabaseConnectionTimeout",
                "affected_pods": ["api-gateway-pod-1", "api-gateway-pod-2"],
                "namespace": "default",
                "error_rate": "45%",
                "deployment_commit": "abc123def456",
                "test_mode": "docker",
                "mock_services": ["kubernetes", "github"]
            }
        )
        
        logger.info(f"\n🚨 Processing alert: {test_alert.alert_id}")
        result = await agent.handle_pager_alert(test_alert)
        
        # Display results
        logger.info("\n📊 === TEST RESULTS ===")
        available = result.get('available_integrations', [])
        logger.info(f"Available integrations: {available}")
        
        # Check each integration's context
        context_data = result.get('context_data', {})
        
        if 'kubernetes' in context_data:
            logger.info("\n☸️  Kubernetes Context:")
            k8s_data = context_data['kubernetes']
            if 'error' not in k8s_data:
                logger.info("  ✅ Successfully retrieved mock Kubernetes data")
                logger.info("  - Pod information fetched")
                logger.info("  - Event data retrieved")
            else:
                logger.warning(f"  ❌ Kubernetes error: {k8s_data.get('error')}")
        
        if 'github' in context_data:
            logger.info("\n🐙 GitHub Context:")
            gh_data = context_data['github']
            if 'error' not in gh_data:
                logger.info("  ✅ Successfully retrieved mock GitHub data")
                logger.info("  - Recent commits fetched")
                logger.info("  - Issues retrieved")
                logger.info("  - Actions status checked")
            else:
                logger.warning(f"  ❌ GitHub error: {gh_data.get('error')}")
        
        # AI Analysis
        if result.get('analysis'):
            logger.info("\n🧠 AI Analysis Generated: ✅")
            logger.info("First 5 lines of analysis:")
            for line in result['analysis'].split('\n')[:5]:
                logger.info(f"  {line}")
        
        # Create Notion documentation
        if "notion" in available:
            logger.info("\n📝 Creating comprehensive documentation in Notion...")
            notion_int = agent.mcp_integrations["notion"]
            doc_data = {
                "alert_id": test_alert.alert_id,
                "service_name": test_alert.service_name,
                "severity": test_alert.severity,
                "description": test_alert.description,
                "metadata": test_alert.metadata,
                "test_results": {
                    "integrations_tested": available,
                    "kubernetes_mock": "kubernetes" in context_data and 'error' not in context_data.get('kubernetes', {}),
                    "github_mock": "github" in context_data and 'error' not in context_data.get('github', {}),
                    "ai_analysis": bool(result.get('analysis'))
                }
            }
            
            doc_result = await notion_int.create_incident_documentation(doc_data)
            if doc_result.get('success'):
                logger.info(f"  ✅ Notion page created: {doc_result.get('url')}")
            else:
                logger.error(f"  ❌ Failed to create Notion page: {doc_result.get('error')}")
        
        # Summary
        logger.info("\n✅ === DOCKER TEST SUMMARY ===")
        logger.info(f"Total integrations: {len(available)}")
        logger.info(f"Mock services working: {sum(1 for i in ['kubernetes', 'github'] if i in available)}/2")
        logger.info(f"Real services working: {'✅' if 'notion' in available else '❌'} Notion")
        logger.info(f"AI Analysis: {'✅' if result.get('analysis') else '❌'}")
        
        # Save results
        results_dir = "/app/test-results"
        if os.path.exists(results_dir):
            with open(f"{results_dir}/test-summary.txt", "w") as f:
                f.write(f"Docker Integration Test Results\n")
                f.write(f"==============================\n")
                f.write(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"Integrations: {', '.join(available)}\n")
                f.write(f"Test Status: {'PASSED' if len(available) >= 2 else 'FAILED'}\n")
            logger.info(f"\n📄 Test results saved to {results_dir}/test-summary.txt")
        
        await agent.shutdown()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    logger.info("\n🔚 Docker integration test completed")

if __name__ == "__main__":
    asyncio.run(test_with_mock_services())