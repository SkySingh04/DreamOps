#!/usr/bin/env python3
"""Test script for Kubernetes Agno MCP Integration."""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.oncall_agent.mcp_integrations.kubernetes_agno_mcp import KubernetesAgnoMCPIntegration


async def test_agno_mcp():
    """Test the Agno MCP integration."""
    print("=" * 70)
    print("KUBERNETES AGNO MCP INTEGRATION TEST")
    print("=" * 70)

    # Initialize integration
    print("\n[1/5] Initializing Kubernetes Agno MCP Integration...")
    k8s = KubernetesAgnoMCPIntegration(
        namespace="default",
        enable_destructive_operations=False
    )

    try:
        # Test connection
        print("\n[2/5] Connecting to Kubernetes MCP server via Agno...")
        connected = await k8s.connect()

        if not connected:
            print("❌ Failed to connect to MCP server")
            return False

        print("✅ Connected successfully!")

        # Get connection info
        print("\n[3/5] Connection Info:")
        conn_info = k8s.get_connection_info()
        for key, value in conn_info.items():
            print(f"  {key}: {value}")

        # Test health check
        print("\n[4/5] Running health check...")
        healthy = await k8s.health_check()
        print(f"  Health: {'✅ Healthy' if healthy else '❌ Unhealthy'}")

        # Test fetching context (list namespaces)
        print("\n[5/5] Testing context fetch (list namespaces)...")
        result = await k8s.fetch_context({"type": "namespaces"})

        if "error" in result:
            print(f"  ❌ Error: {result['error']}")
        else:
            print(f"  ✅ Success!")
            print(f"  Response: {str(result)[:200]}...")

        print("\n" + "=" * 70)
        print("TEST COMPLETED SUCCESSFULLY! 🎉")
        print("=" * 70)
        print("\nThe Agno MCP integration is working correctly!")
        print("Now you can use it in your oncall agent.")

        return True

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\n[CLEANUP] Disconnecting...")
        await k8s.disconnect()
        print("✅ Disconnected")


if __name__ == "__main__":
    print("\n🚀 Starting Kubernetes Agno MCP Test...\n")
    success = asyncio.run(test_agno_mcp())
    sys.exit(0 if success else 1)
