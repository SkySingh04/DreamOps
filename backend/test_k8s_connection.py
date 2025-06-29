#!/usr/bin/env python3
"""
Test script for Kubernetes connection with improved integration.
"""

import asyncio
import base64
import json
from pathlib import Path

from src.oncall_agent.mcp_integrations.kubernetes_mcp_stdio import (
    KubernetesMCPStdioIntegration,
)
from src.oncall_agent.utils.logger import get_logger

logger = get_logger(__name__)


async def test_local_kubeconfig():
    """Test connection using local kubeconfig."""
    print("\n" + "="*60)
    print("TEST: Local Kubeconfig Connection")
    print("="*60)

    # Create integration
    k8s = KubernetesMCPStdioIntegration(
        namespace="default",
        context=None,  # Use current context
        enable_destructive_operations=False
    )

    try:
        # Discover contexts
        print("Discovering contexts...")
        contexts = await k8s.discover_contexts()

        if not contexts:
            print("No contexts found. Make sure kubectl is configured.")
            return False

        print(f"Found {len(contexts)} context(s):")
        for ctx in contexts:
            current = " (current)" if ctx.is_current else ""
            print(f"  - {ctx.name} (cluster: {ctx.cluster}){current}")

        # Use current context
        current_ctx = next((ctx for ctx in contexts if ctx.is_current), contexts[0])
        print(f"\nUsing context: {current_ctx.name}")

        # Connect
        print("Connecting to Kubernetes...")
        connected = await k8s.connect()

        if not connected:
            print("❌ Failed to connect to Kubernetes")
            return False

        print("✅ Connected successfully")

        # Test connection
        print("\nTesting connection...")
        test_result = await k8s.test_connection(current_ctx.name)
        print(f"Test result: {json.dumps(test_result, indent=2)}")

        # Get some pods
        print("\nFetching pods...")
        pods_result = await k8s.fetch_context({"type": "pods", "namespace": "default"})

        if "error" in pods_result:
            print(f"Error fetching pods: {pods_result['error']}")
        else:
            pods = pods_result.get("pods", [])
            print(f"Found {len(pods)} pod(s) in default namespace")

        # Disconnect
        await k8s.disconnect()
        print("\nDisconnected from Kubernetes")

        return True

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")
        return False


async def test_kubeconfig_upload():
    """Test connection using uploaded kubeconfig."""
    print("\n" + "="*60)
    print("TEST: Kubeconfig Upload Simulation")
    print("="*60)

    # Check if local kubeconfig exists
    kubeconfig_path = Path.home() / ".kube" / "config"

    if not kubeconfig_path.exists():
        print("No local kubeconfig found to simulate upload")
        return False

    # Read and encode kubeconfig
    print("Reading local kubeconfig...")
    kubeconfig_content = kubeconfig_path.read_text()
    encoded_content = base64.b64encode(kubeconfig_content.encode()).decode()

    print(f"Kubeconfig encoded (length: {len(encoded_content)})")

    # Simulate API request
    from src.oncall_agent.api.routers.user_integrations import (
        test_kubernetes_integration,
    )

    config = {
        "context": "default",
        "namespace": "kube-system",
        "kubeconfig_content": encoded_content
    }

    print("\nTesting Kubernetes integration with uploaded kubeconfig...")
    result = await test_kubernetes_integration(config)

    print(f"\nResult: {json.dumps(result, indent=2)}")

    return result.get("success", False)


async def test_stdio_mcp_server():
    """Test if kubernetes-mcp-server works in STDIO mode."""
    print("\n" + "="*60)
    print("TEST: STDIO MCP Server")
    print("="*60)

    import subprocess

    # Check if kubernetes-mcp-server is available
    mcp_commands = [
        ["npx", "@modelcontextprotocol/server-kubernetes", "--help"],
        ["kubernetes-mcp-server", "--help"],
        ["java", "-jar", "kubernetes-mcp-server.jar", "--help"]
    ]

    mcp_available = False
    for cmd in mcp_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ Found MCP server: {' '.join(cmd[:2])}")
                mcp_available = True
                break
        except:
            continue

    if not mcp_available:
        print("❌ No kubernetes-mcp-server found. Install with:")
        print("   npm install -g @modelcontextprotocol/server-kubernetes")
        return False

    return True


async def main():
    """Run all tests."""
    print("🚀 Kubernetes Connection Tests")

    # Test 1: Check MCP server availability
    mcp_available = await test_stdio_mcp_server()

    # Test 2: Local kubeconfig
    if mcp_available:
        local_success = await test_local_kubeconfig()
    else:
        local_success = False

    # Test 3: Kubeconfig upload simulation
    upload_success = await test_kubeconfig_upload()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"MCP Server Available: {'✅' if mcp_available else '❌'}")
    print(f"Local Kubeconfig Test: {'✅' if local_success else '❌'}")
    print(f"Kubeconfig Upload Test: {'✅' if upload_success else '❌'}")


if __name__ == "__main__":
    asyncio.run(main())
