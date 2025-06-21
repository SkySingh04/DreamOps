#!/usr/bin/env python3
"""Test script to verify all MCP integrations work together."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.utils import setup_logging


async def test_notion_integration(agent: OncallAgent) -> dict[str, Any]:
    """Test Notion MCP integration."""
    print("\n📝 Testing Notion MCP Integration...")
    
    if "notion" not in agent.mcp_integrations:
        return {"status": "error", "message": "Notion integration not registered"}
    
    notion = agent.mcp_integrations["notion"]
    
    try:
        # Test health check
        is_healthy = await notion.health_check()
        if not is_healthy:
            return {"status": "error", "message": "Notion health check failed"}
        
        # Test fetching context (e.g., list databases)
        context = await notion.fetch_context("list_databases")
        
        return {
            "status": "success",
            "message": "Notion integration working",
            "sample_data": context.get("databases", [])[:2] if "databases" in context else None
        }
    except Exception as e:
        return {"status": "error", "message": f"Notion test failed: {str(e)}"}


async def test_github_integration(agent: OncallAgent) -> dict[str, Any]:
    """Test GitHub MCP integration."""
    print("\n🐙 Testing GitHub MCP Integration...")
    
    if "github" not in agent.mcp_integrations:
        return {"status": "error", "message": "GitHub integration not registered"}
    
    github = agent.mcp_integrations["github"]
    
    try:
        # Test health check
        is_healthy = await github.health_check()
        if not is_healthy:
            return {"status": "error", "message": "GitHub health check failed"}
        
        # Test fetching context (e.g., repository info)
        # Using a public repo for testing
        context = await github.fetch_context("repository_info", repository="octocat/Hello-World")
        
        return {
            "status": "success",
            "message": "GitHub integration working",
            "sample_data": {
                "repo": context.get("name"),
                "stars": context.get("stargazers_count")
            } if "name" in context else None
        }
    except Exception as e:
        return {"status": "error", "message": f"GitHub test failed: {str(e)}"}


async def test_kubernetes_integration(agent: OncallAgent) -> dict[str, Any]:
    """Test Kubernetes MCP integration."""
    print("\n☸️  Testing Kubernetes MCP Integration...")
    
    if "kubernetes" not in agent.mcp_integrations:
        return {"status": "error", "message": "Kubernetes integration not registered"}
    
    k8s = agent.mcp_integrations["kubernetes"]
    
    try:
        # Test health check
        is_healthy = await k8s.health_check()
        if not is_healthy:
            return {"status": "error", "message": "Kubernetes health check failed"}
        
        # Test fetching context (e.g., list pods)
        pods = await k8s.list_pods("default")
        
        return {
            "status": "success",
            "message": "Kubernetes integration working",
            "sample_data": {
                "pod_count": len(pods.get("pods", [])),
                "sample_pods": [p["name"] for p in pods.get("pods", [])[:3]]
            } if "pods" in pods else None
        }
    except Exception as e:
        return {"status": "error", "message": f"Kubernetes test failed: {str(e)}"}


async def test_integrated_alert_handling(agent: OncallAgent) -> dict[str, Any]:
    """Test handling an alert that uses all three integrations."""
    print("\n🚨 Testing Integrated Alert Handling...")
    
    # Create a test alert
    alert = PagerAlert(
        alert_id="TEST-INTEGRATION-001",
        severity="high",
        service_name="payment-service",
        description="High error rate detected in payment processing",
        timestamp=datetime.now(UTC).isoformat(),
        metadata={
            "error_rate": "15%",
            "affected_users": "500",
            "cluster": "kind-oncall-test",
            "namespace": "default"
        }
    )
    
    try:
        # Process the alert
        result = await agent.handle_pager_alert(alert)
        
        # Check if all integrations provided context
        contexts_gathered = []
        if "github_context" in result:
            contexts_gathered.append("GitHub")
        if "k8s_context" in result:
            contexts_gathered.append("Kubernetes")
        if "notion_context" in result:
            contexts_gathered.append("Notion")
        
        return {
            "status": "success",
            "message": "Integrated alert handling successful",
            "contexts_gathered": contexts_gathered,
            "analysis_preview": result.get("analysis", "")[:200] + "..." if result.get("analysis") else None
        }
    except Exception as e:
        return {"status": "error", "message": f"Integrated test failed: {str(e)}"}


async def main():
    """Main test function."""
    # Set up logging
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*80)
    print("🔧 TESTING ALL MCP INTEGRATIONS")
    print("="*80 + "\n")
    
    # Initialize the agent
    print("🚀 Initializing AI Agent...")
    agent = OncallAgent()
    
    # Connect all integrations
    print("🔌 Connecting integrations...")
    await agent.connect_integrations()
    
    print(f"\n✅ Connected integrations: {list(agent.mcp_integrations.keys())}")
    
    # Test each integration individually
    results = {}
    
    # Test Notion
    results["notion"] = await test_notion_integration(agent)
    
    # Test GitHub
    results["github"] = await test_github_integration(agent)
    
    # Test Kubernetes
    results["kubernetes"] = await test_kubernetes_integration(agent)
    
    # Test integrated functionality
    results["integrated"] = await test_integrated_alert_handling(agent)
    
    # Display results summary
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80 + "\n")
    
    all_passed = True
    for integration, result in results.items():
        status_icon = "✅" if result["status"] == "success" else "❌"
        print(f"{status_icon} {integration.upper()}: {result['message']}")
        if result.get("sample_data"):
            print(f"   Sample data: {result['sample_data']}")
        if result["status"] != "success":
            all_passed = False
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL TESTS PASSED! All integrations are working correctly.")
    else:
        print("❌ SOME TESTS FAILED! Check the logs above for details.")
    print("="*80 + "\n")
    
    # Cleanup
    await agent.shutdown()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)