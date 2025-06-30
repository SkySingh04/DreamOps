#!/usr/bin/env python3
"""Test script for GitHub MCP Server with Agno integration."""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Two options to test:
# 1. Direct Agno agent (standalone)
# 2. MCP integration for oncall agent

async def test_direct_agno_agent():
    """Test the direct Agno agent implementation."""
    print("=" * 70)
    print("🧪 TESTING DIRECT AGNO AGENT WITH GITHUB MCP")
    print("=" * 70)
    
    from src.oncall_agent.agno_github_agent import create_github_agno_agent
    
    try:
        # Create agent
        print("🚀 Creating GitHub Agno agent...")
        agent = await create_github_agno_agent()
        print("✅ Agent created successfully!")
        
        # Test queries
        queries = [
            "Search for 'authentication' in kubernetes/kubernetes repo",
            "Show me the last 5 commits in kubernetes/kubernetes",
            "Get the README.md file from kubernetes/kubernetes"
        ]
        
        for query in queries:
            print(f"\n📝 Query: {query}")
            print("-" * 60)
            try:
                result = await agent.run(query)
                print(f"✅ Result:\n{result}")
            except Exception as e:
                print(f"❌ Error: {e}")
            print("-" * 60)
        
        # Cleanup
        await agent.cleanup()
        print("\n✅ Agent cleaned up successfully!")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()


async def test_mcp_integration():
    """Test the MCP integration for oncall agent."""
    print("\n" + "=" * 70)
    print("🧪 TESTING MCP INTEGRATION WITH AGNO")
    print("=" * 70)
    
    from src.oncall_agent.mcp_integrations.github_agno_mcp import GitHubAgnoMCPIntegration
    
    try:
        # Create integration
        print("🚀 Creating GitHub Agno MCP integration...")
        integration = GitHubAgnoMCPIntegration()
        
        # Connect
        print("🔌 Connecting to GitHub MCP server...")
        connected = await integration.connect()
        print(f"✅ Connection status: {connected}")
        
        if connected:
            # Test health check
            print("\n🩺 Testing health check...")
            health = await integration.health_check()
            print(f"✅ Health status: {health}")
            
            # Test capabilities
            print("\n🛠️ Getting capabilities...")
            capabilities = await integration.get_capabilities()
            print(f"✅ Capabilities: {capabilities}")
            
            # Test context fetch
            print("\n🔍 Testing context fetch...")
            context_result = await integration.fetch_context({
                'query': 'find information about pods',
                'repo': 'kubernetes/kubernetes'
            })
            print(f"✅ Context result: {context_result}")
            
            # Test action execution
            print("\n🎯 Testing action execution...")
            action_result = await integration.execute_action('search_code', {
                'query': 'deployment',
                'repo': 'kubernetes/kubernetes'
            })
            print(f"✅ Action result: {action_result}")
            
            # Disconnect
            print("\n🔌 Disconnecting...")
            await integration.disconnect()
            print("✅ Disconnected successfully!")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("🎯 GitHub MCP Server + Agno Integration Test Suite")
    print("=" * 70)
    
    # Check if Agno is installed
    try:
        import agno
        print("✅ Agno is installed")
    except ImportError:
        print("❌ Agno is not installed. Please run: uv add agno")
        return
    
    # Check environment
    if not os.getenv('GITHUB_TOKEN'):
        print("❌ GITHUB_TOKEN not set in environment")
        return
    
    if not os.getenv('ANTHROPIC_API_KEY') and not os.getenv('OPENAI_API_KEY'):
        print("❌ Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set")
        return
    
    print("✅ Environment configured correctly")
    print()
    
    # Run tests
    # await test_direct_agno_agent()
    await test_mcp_integration()


if __name__ == "__main__":
    asyncio.run(main())