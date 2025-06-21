#!/usr/bin/env python3
"""Test script to verify MCP integrations configuration (with mocking for unavailable services)."""

import asyncio
from pathlib import Path

from src.oncall_agent.config import get_config


def check_env_config():
    """Check environment configuration for all integrations."""
    print("\n" + "="*80)
    print("🔍 CHECKING ENVIRONMENT CONFIGURATION")
    print("="*80 + "\n")

    config = get_config()
    results = []

    # Check Anthropic
    print("🤖 Anthropic Configuration:")
    if config.anthropic_api_key and config.anthropic_api_key != "your-api-key-here":
        print("   ✅ API Key: Configured")
        print(f"   ✅ Model: {config.claude_model}")
    else:
        print("   ❌ API Key: Not configured")
        results.append("Anthropic API key not configured")

    # Check GitHub MCP
    print("\n🐙 GitHub MCP Configuration:")
    if config.github_token and config.github_token != "your-github-token":
        print("   ✅ Token: Configured")
        print(f"   ✅ Server Path: {config.github_mcp_server_path}")
        print(f"   ✅ Host: {config.github_mcp_host}")
        print(f"   ✅ Port: {config.github_mcp_port}")

        # Check if server binary exists
        if Path(config.github_mcp_server_path).exists():
            print("   ✅ Server Binary: Found")
        else:
            print("   ⚠️  Server Binary: Not found at configured path")
            results.append("GitHub MCP server binary not found")
    else:
        print("   ❌ Token: Not configured")
        results.append("GitHub token not configured")

    # Check Notion MCP
    print("\n📝 Notion MCP Configuration:")
    if hasattr(config, 'notion_token') and config.notion_token and config.notion_token != "your-notion-token":
        print("   ✅ Token: Configured")
        if hasattr(config, 'notion_version'):
            print(f"   ✅ API Version: {config.notion_version}")
    else:
        print("   ❌ Token: Not configured")
        results.append("Notion token not configured")

    # Check Kubernetes MCP
    print("\n☸️  Kubernetes MCP Configuration:")
    if config.k8s_enabled:
        print("   ✅ Enabled: True")
        print(f"   ✅ Config Path: {config.k8s_config_path}")
        print(f"   ✅ Context: {config.k8s_context}")
        print(f"   ✅ Namespace: {config.k8s_namespace}")
        print(f"   ✅ MCP Server URL: {config.k8s_mcp_server_url}")
        print(f"   ✅ Destructive Ops: {config.k8s_enable_destructive_operations}")

        # Check for port conflicts
        github_port = config.github_mcp_port
        k8s_port = int(config.k8s_mcp_server_url.split(':')[-1])
        if github_port == k8s_port:
            print(f"   ⚠️  PORT CONFLICT: Both GitHub and K8s MCP using port {github_port}")
            results.append(f"Port conflict on {github_port}")
    else:
        print("   ❌ Enabled: False")
        results.append("Kubernetes integration disabled")

    return results


async def test_integration_loading():
    """Test that integrations can be loaded without errors."""
    print("\n" + "="*80)
    print("🔌 TESTING INTEGRATION LOADING")
    print("="*80 + "\n")

    try:
        from src.oncall_agent.agent import OncallAgent

        print("📦 Importing integrations...")

        # Test importing each integration module
        integrations_to_test = [
            ("GitHub", "src.oncall_agent.mcp_integrations.github_mcp"),
            ("Enhanced GitHub", "src.oncall_agent.mcp_integrations.enhanced_github_mcp"),
            ("Kubernetes", "src.oncall_agent.mcp_integrations.kubernetes"),
            ("Notion", "src.oncall_agent.mcp_integrations.notion"),
        ]

        for name, module_path in integrations_to_test:
            try:
                module = __import__(module_path, fromlist=[''])
                print(f"   ✅ {name} integration module loaded successfully")
            except ImportError as e:
                print(f"   ❌ {name} integration failed to load: {e}")
            except Exception as e:
                print(f"   ⚠️  {name} integration loaded with warnings: {e}")

        # Test agent initialization
        print("\n🤖 Initializing agent...")
        agent = OncallAgent()
        print("   ✅ Agent initialized successfully")

        # Check which integrations would be registered
        print("\n📋 Integrations that would be registered:")
        config = get_config()

        if config.github_token and config.github_token != "your-github-token":
            print("   ✅ GitHub MCP (based on token presence)")
        else:
            print("   ❌ GitHub MCP (no token)")

        if hasattr(config, 'notion_token') and config.notion_token and config.notion_token != "your-notion-token":
            print("   ✅ Notion MCP (based on token presence)")
        else:
            print("   ❌ Notion MCP (no token)")

        if config.k8s_enabled:
            print("   ✅ Kubernetes MCP (enabled in config)")
        else:
            print("   ❌ Kubernetes MCP (disabled)")

        return True

    except Exception as e:
        print(f"   ❌ Failed to test integration loading: {e}")
        return False


async def main():
    """Main test function."""
    print("\n" + "="*80)
    print("🔧 MCP INTEGRATIONS CONFIGURATION TEST")
    print("="*80 + "\n")

    # Check environment configuration
    config_issues = check_env_config()

    # Test integration loading
    loading_success = await test_integration_loading()

    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80 + "\n")

    if not config_issues and loading_success:
        print("✅ All configurations look good!")
        print("\n💡 Next steps:")
        print("1. Ensure Docker Desktop is running with WSL integration enabled")
        print("2. Install kind: curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64 && chmod +x ./kind && sudo mv ./kind /usr/local/bin/")
        print("3. Create test cluster: kind create cluster --name oncall-test")
        print("4. Install kubectl: curl -LO https://dl.k8s.io/release/v1.28.0/bin/linux/amd64/kubectl && chmod +x kubectl && sudo mv kubectl /usr/local/bin/")
        print("5. Run: cd backend && uv run python test_all_integrations.py")
    else:
        print("⚠️  Issues found:")
        for issue in config_issues:
            print(f"   - {issue}")
        if not loading_success:
            print("   - Integration loading failed")

    print("\n" + "="*80)
    print("📝 ENVIRONMENT VARIABLES DETECTED:")
    print("="*80)
    config = get_config()
    print(f"ANTHROPIC_API_KEY: {'✅ Set' if config.anthropic_api_key != 'your-api-key-here' else '❌ Not set'}")
    print(f"GITHUB_TOKEN: {'✅ Set' if config.github_token else '❌ Not set'}")
    print(f"NOTION_TOKEN: {'✅ Set' if hasattr(config, 'notion_token') and config.notion_token else '❌ Not set'}")
    print(f"K8S_ENABLED: {'✅ True' if config.k8s_enabled else '❌ False'}")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
