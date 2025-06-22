#!/usr/bin/env python3
"""Test script to verify YOLO mode configuration and functionality."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.oncall_agent.api.routers.agent import AGENT_CONFIG
from src.oncall_agent.api.schemas import AIMode
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)


def check_configuration():
    """Check if YOLO mode is properly configured."""
    print("🔍 Checking YOLO Mode Configuration")
    print("=" * 50)

    config = get_config()
    issues = []

    # Check K8S_ENABLE_DESTRUCTIVE_OPERATIONS
    if not config.k8s_enable_destructive_operations:
        issues.append("❌ K8S_ENABLE_DESTRUCTIVE_OPERATIONS is False (must be True for YOLO mode)")
        print(f"   Current value: {config.k8s_enable_destructive_operations}")
    else:
        print("✅ K8S_ENABLE_DESTRUCTIVE_OPERATIONS is True")

    # Check K8S_ENABLED
    if not config.k8s_enabled:
        issues.append("❌ K8S_ENABLED is False (must be True)")
        print(f"   Current value: {config.k8s_enabled}")
    else:
        print("✅ K8S_ENABLED is True")

    # Check ANTHROPIC_API_KEY
    if not config.anthropic_api_key or config.anthropic_api_key == "your-api-key-here":
        issues.append("❌ ANTHROPIC_API_KEY not set properly")
    else:
        print("✅ ANTHROPIC_API_KEY is configured")

    # Check current AI mode
    print(f"\n📊 Current AI Mode: {AGENT_CONFIG.mode.value}")

    if AGENT_CONFIG.mode != AIMode.YOLO:
        print("   ⚠️  Note: AI mode is not set to YOLO. Set it via the frontend or API")

    print("\n" + "=" * 50)

    if issues:
        print("❌ Configuration Issues Found:")
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 Fix: Run ./enable_yolo_mode.sh to configure YOLO mode")
        return False
    else:
        print("✅ YOLO Mode is properly configured!")
        print("\n🚀 Next Steps:")
        print("   1. Start the API server: uv run python api_server.py")
        print("   2. In the frontend, toggle AI Mode to 'YOLO'")
        print("   3. Send test alerts to see auto-remediation in action")
        return True


async def test_agent_creation():
    """Test creating an enhanced agent with YOLO mode."""
    print("\n🧪 Testing Enhanced Agent Creation")
    print("=" * 50)

    try:
        from src.oncall_agent.agent_enhanced import EnhancedOncallAgent

        # Create agent with YOLO mode
        agent = EnhancedOncallAgent(ai_mode=AIMode.YOLO)
        print(f"✅ Created EnhancedOncallAgent with mode: {agent.ai_mode.value}")

        # Check if K8s MCP is available
        if agent.k8s_mcp:
            print("✅ Kubernetes MCP integration initialized")
        else:
            print("❌ Kubernetes MCP integration not available")

        # Check if executor is available
        if agent.agent_executor:
            print("✅ Agent executor initialized (can execute commands)")
        else:
            print("❌ Agent executor not available")

        await agent.connect_integrations()
        print("✅ Successfully connected integrations")

        return True

    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        return False


async def main():
    """Main test function."""
    print("🚀 YOLO Mode Configuration Test")
    print("=" * 50)

    # Check basic configuration
    config_ok = check_configuration()

    if config_ok:
        # Test agent creation
        agent_ok = await test_agent_creation()

        if agent_ok:
            print("\n✅ All tests passed! YOLO mode is ready to use.")
        else:
            print("\n❌ Agent creation test failed.")
    else:
        print("\n❌ Configuration check failed. Please fix the issues above.")

    print("\n📚 Documentation:")
    print("   - YOLO mode auto-executes remediation commands")
    print("   - Only commands with confidence ≥ 0.8 are executed")
    print("   - High-risk commands still require manual approval")
    print("   - Monitor logs to see command execution in real-time")


if __name__ == "__main__":
    asyncio.run(main())
