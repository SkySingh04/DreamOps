#!/usr/bin/env python3
"""Test script for GitHub MCP integration."""

import asyncio
import logging
import os
from datetime import datetime, timezone

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import our modules
from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.config import get_config


async def test_github_integration():
    """Test the GitHub MCP integration."""
    print("Testing GitHub MCP Integration")
    print("=" * 50)
    
    # Check configuration
    config = get_config()
    if not config.github_token:
        print("❌ GITHUB_TOKEN not configured. Please set it in .env file.")
        return False
    
    print(f"✓ GitHub token configured: {config.github_token[:4]}...")
    print(f"✓ MCP server path: {config.github_mcp_server_path}")
    print(f"✓ MCP server host:port: {config.github_mcp_host}:{config.github_mcp_port}")
    
    try:
        # Initialize the agent (this should register GitHub integration)
        agent = OncallAgent()
        print(f"✓ Agent initialized with integrations: {list(agent.mcp_integrations.keys())}")
        
        # Connect to integrations
        print("\n🔌 Connecting to integrations...")
        await agent.connect_integrations()
        
        # Check if GitHub integration is connected
        github_integration = agent.mcp_integrations.get("github")
        if not github_integration:
            print("❌ GitHub integration not found")
            return False
        
        print(f"✓ GitHub integration connected: {github_integration.connected}")
        
        # Test health check
        health = await github_integration.health_check()
        print(f"✓ Health check: {health}")
        
        # Test capabilities
        capabilities = await github_integration.get_capabilities()
        print(f"✓ Capabilities: {capabilities}")
        
        # Create a test alert
        test_alert = PagerAlert(
            alert_id="TEST-12345",
            severity="high",
            service_name="api-gateway",
            description="Test alert for GitHub MCP integration",
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata={
                "test": True,
                "integration": "github-mcp"
            }
        )
        
        print(f"\n📋 Processing test alert: {test_alert.alert_id}")
        
        # Process the alert (this should try to gather GitHub context)
        result = await agent.handle_pager_alert(test_alert)
        
        print(f"✓ Alert processed with status: {result.get('status')}")
        if result.get('context_data'):
            print(f"✓ Context data gathered: {list(result['context_data'].keys())}")
        
        # Display the analysis
        if result.get('analysis'):
            print("\n📊 AI Analysis:")
            print("-" * 40)
            print(result['analysis'])
            print("-" * 40)
        
        # Shutdown
        await agent.shutdown()
        print("✓ Agent shutdown complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("GitHub MCP Integration Test")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = ".env"
    if not os.path.exists(env_file):
        print(f"❌ Environment file '{env_file}' not found.")
        print("📝 Please create .env file from .env.example and configure:")
        print("   - ANTHROPIC_API_KEY")
        print("   - GITHUB_TOKEN")
        return
    
    success = await test_github_integration()
    
    if success:
        print("\n🎉 GitHub MCP integration test completed successfully!")
    else:
        print("\n❌ GitHub MCP integration test failed!")


if __name__ == "__main__":
    asyncio.run(main())