#!/usr/bin/env python3
"""Test script for GitHub MCP integration."""

import asyncio
import logging
import os

# Add the src directory to the Python path
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_github_integration():
    """Test the GitHub MCP integration."""
    logger.info("=== Testing GitHub MCP Integration ===")

    # Check if GitHub token is configured
    config = get_config()
    if not config.github_token:
        logger.error("GITHUB_TOKEN not set in environment. Please set it to test GitHub integration.")
        logger.info("Set it in .env file: GITHUB_TOKEN=your-github-personal-access-token")
        return

    # Create the agent
    agent = OncallAgent()

    try:
        # Connect all integrations
        logger.info("Connecting integrations...")
        await agent.connect_integrations()

        # Check which integrations are available
        logger.info(f"Available integrations: {list(agent.mcp_integrations.keys())}")

        if "github" not in agent.mcp_integrations:
            logger.error("GitHub integration not registered!")
            return

        # Test GitHub health check
        github_integration = agent.mcp_integrations["github"]
        health_status = await github_integration.health_check()
        logger.info(f"GitHub integration health check: {'OK' if health_status else 'FAILED'}")

        # Create a test alert
        test_alert = PagerAlert(
            alert_id="test-github-001",
            severity="high",
            service_name="api-gateway",
            description="API Gateway experiencing high error rates (500 errors)",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={
                "error_rate": "15%",
                "affected_endpoints": ["/api/v1/users", "/api/v1/orders"],
                "deployment_id": "deploy-123"
            }
        )

        logger.info("Processing test alert through the agent...")
        result = await agent.handle_pager_alert(test_alert)

        # Display the results
        logger.info("=== Alert Analysis Results ===")
        logger.info(f"Alert ID: {result['alert_id']}")
        logger.info(f"Status: {result['status']}")
        logger.info(f"Available Integrations: {result['available_integrations']}")

        if 'github_context' in result:
            github_context = result['github_context']
            logger.info("\n=== GitHub Context ===")

            if 'repository' in github_context:
                logger.info(f"Repository: {github_context['repository']}")

            if 'recent_commits' in github_context:
                commits = github_context['recent_commits']
                logger.info(f"Recent commits: {commits.get('commit_count', 0)} commits found")

            if 'open_issues' in github_context:
                issues = github_context['open_issues']
                logger.info(f"Open issues: {issues.get('issue_count', 0)} issues found")

            if 'actions_status' in github_context:
                logger.info(f"GitHub Actions status: {github_context['actions_status'].get('message', 'N/A')}")

            if 'recent_pull_requests' in github_context:
                prs = github_context['recent_pull_requests']
                logger.info(f"Recent PRs: {prs.get('pr_count', 0)} merged PRs found")

            if 'error' in github_context:
                logger.error(f"GitHub context error: {github_context['error']}")

        logger.info("\n=== Claude Analysis ===")
        logger.info(result.get('analysis', 'No analysis available')[:500] + "...")

        # Test creating an issue (if you want to test this, uncomment below)
        # logger.info("\n=== Testing Issue Creation ===")
        # issue_params = {
        #     "repository": "myorg/api-gateway",
        #     "title": f"[INCIDENT] High error rate in API Gateway - {test_alert.alert_id}",
        #     "body": f"Alert: {test_alert.description}\n\nSeverity: {test_alert.severity}\n\nAutomatically created by oncall-agent",
        #     "labels": ["incident", "auto-generated", test_alert.severity]
        # }
        # issue_result = await github_integration.execute_action("create_issue", issue_params)
        # logger.info(f"Issue creation result: {issue_result}")

    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)

    finally:
        # Shutdown the agent
        logger.info("Shutting down agent...")
        await agent.shutdown()

    logger.info("=== Test Complete ===")


async def test_standalone_github_mcp():
    """Test the GitHub MCP server directly without the full agent."""
    logger.info("=== Testing Standalone GitHub MCP Server ===")

    config = get_config()
    if not config.github_token:
        logger.error("GITHUB_TOKEN not set. Please configure it first.")
        return

    # Import the GitHub integration directly
    from src.oncall_agent.mcp_integrations.github_mcp import GitHubMCPIntegration

    # Create the integration
    github = GitHubMCPIntegration({
        "github_token": config.github_token,
        "mcp_server_path": config.github_mcp_server_path or "../../github-mcp-server/github-mcp-server",
        "server_host": config.github_mcp_host,
        "server_port": config.github_mcp_port
    })

    try:
        # Connect to the server
        logger.info("Connecting to GitHub MCP server...")
        await github.connect()

        # Test health check
        health = await github.health_check()
        logger.info(f"Health check: {'OK' if health else 'FAILED'}")

        # Test fetching commits (using a public repo for testing)
        logger.info("\nTesting commit fetching...")
        commits_result = await github.fetch_context("recent_commits", repository="github/docs", since_hours=24)
        logger.info(f"Commits result: {commits_result}")

        # Get capabilities
        capabilities = await github.get_capabilities()
        logger.info(f"\nAvailable capabilities: {capabilities}")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

    finally:
        logger.info("Disconnecting...")
        await github.disconnect()


async def main():
    """Main test function."""
    # First test the standalone GitHub MCP
    await test_standalone_github_mcp()

    logger.info("\n" + "="*50 + "\n")

    # Then test the full agent integration
    await test_github_integration()


if __name__ == "__main__":
    asyncio.run(main())
