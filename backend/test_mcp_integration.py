#!/usr/bin/env python3
"""Test script to verify kubernetes-mcp-server integration."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.oncall_agent.mcp_integrations.kubernetes_manusa_mcp import (
    KubernetesManusaMCPIntegration,
)
from src.oncall_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def test_mcp_integration():
    """Test the MCP integration with kubernetes-mcp-server."""
    print("\n🧪 Testing Kubernetes MCP Integration (manusa/kubernetes-mcp-server)\n")

    # Create integration
    k8s = KubernetesManusaMCPIntegration(
        namespace="default",
        enable_destructive_operations=False
    )

    # Test connection
    print("1️⃣ Testing connection to MCP server...")
    connected = await k8s.connect()
    if connected:
        print("✅ Successfully connected to MCP server")
        print(f"   Server URL: {k8s.mcp_server_url}")
        print(f"   Available tools: {len(k8s._available_tools)}")
    else:
        print("❌ Failed to connect to MCP server")
        print("   Make sure kubernetes-mcp-server is running on port 8080")
        return

    # Test health check
    print("\n2️⃣ Testing health check...")
    healthy = await k8s.health_check()
    print(f"✅ Health check: {'healthy' if healthy else 'unhealthy'}")

    # Test capabilities
    print("\n3️⃣ Getting capabilities...")
    capabilities = k8s.get_capabilities()
    print(f"✅ Available capabilities: {len(capabilities)}")
    for cap in capabilities[:5]:  # Show first 5
        print(f"   - {cap}")
    if len(capabilities) > 5:
        print(f"   ... and {len(capabilities) - 5} more")

    # Test fetching namespaces
    print("\n4️⃣ Testing namespace list...")
    try:
        result = await k8s.fetch_context({"type": "namespaces"})
        if "error" in result:
            print(f"⚠️  Error fetching namespaces: {result['error']}")
        else:
            namespaces = result.get("namespaces", [])
            print(f"✅ Found {len(namespaces)} namespaces")
            for ns in namespaces[:3]:  # Show first 3
                if isinstance(ns, dict):
                    print(f"   - {ns.get('metadata', {}).get('name', 'unknown')}")
                else:
                    print(f"   - {ns}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test fetching pods
    print("\n5️⃣ Testing pod list...")
    try:
        result = await k8s.fetch_context({"type": "pods", "namespace": "default"})
        if "error" in result:
            print(f"⚠️  Error fetching pods: {result['error']}")
        else:
            pods = result.get("pods", [])
            print(f"✅ Found {len(pods)} pods in default namespace")
            for pod in pods[:3]:  # Show first 3
                if isinstance(pod, dict):
                    print(f"   - {pod.get('metadata', {}).get('name', 'unknown')}")
                else:
                    print(f"   - {pod}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test connection info
    print("\n6️⃣ Connection info:")
    conn_info = k8s.get_connection_info()
    print("✅ Connection details:")
    print(f"   - Namespace: {conn_info['namespace']}")
    print(f"   - Destructive ops: {conn_info['destructive_operations_enabled']}")
    print(f"   - MCP mode: {conn_info['mcp_mode']}")
    print(f"   - MCP server: {conn_info['mcp_server']}")
    print(f"   - Available tools: {conn_info['available_tools']}")

    # Disconnect
    print("\n7️⃣ Disconnecting...")
    await k8s.disconnect()
    print("✅ Disconnected from MCP server")

    print("\n✨ All tests completed!\n")


if __name__ == "__main__":
    asyncio.run(test_mcp_integration())
