#!/usr/bin/env python3
"""Test script for enhanced Kubernetes integration."""

import asyncio
import logging

from src.oncall_agent.mcp_integrations.kubernetes_enhanced import (
    EnhancedKubernetesMCPIntegration,
)
from src.oncall_agent.utils import setup_logging

# Setup logging
setup_logging(level="DEBUG")
logger = logging.getLogger(__name__)


async def test_k8s_integration():
    """Test the enhanced Kubernetes integration."""
    print("🔍 Testing Enhanced Kubernetes Integration\n")

    # Create integration instance
    k8s = EnhancedKubernetesMCPIntegration()

    # 1. Discover contexts
    print("1. Discovering Kubernetes contexts...")
    contexts = await k8s.discover_contexts()

    if not contexts:
        print("❌ No Kubernetes contexts found. Make sure you have a valid kubeconfig.")
        return

    print(f"✅ Found {len(contexts)} context(s):")
    for ctx in contexts:
        prefix = "→ " if ctx['is_current'] else "  "
        print(f"{prefix}{ctx['name']} (cluster: {ctx['cluster']}, namespace: {ctx['namespace']})")
    print()

    # 2. Test connection to first context
    test_context = contexts[0]['name']
    print(f"2. Testing connection to context: {test_context}")
    test_result = await k8s.test_connection(test_context)

    if test_result['success']:
        print("✅ Connection successful!")
        print(f"   - Cluster version: {test_result.get('cluster_version', 'unknown')}")
        print(f"   - Node count: {test_result.get('node_count', 0)}")
        print(f"   - Namespace exists: {test_result.get('namespace_exists', False)}")
        if test_result.get('permissions'):
            print("   - Permissions:")
            for perm, allowed in test_result['permissions'].items():
                status = "✅" if allowed else "❌"
                print(f"     {status} {perm}")
    else:
        print(f"❌ Connection failed: {test_result.get('error', 'unknown error')}")
        return
    print()

    # 3. Get cluster info
    print("3. Getting cluster information...")
    cluster_info = await k8s.get_cluster_info(test_context)

    if cluster_info['success']:
        info = cluster_info['cluster_info']
        print("✅ Cluster information:")
        print(f"   - Nodes: {info['node_count']}")
        print(f"   - Namespaces: {info['namespace_count']}")
        print(f"   - Pods: {info['pod_count']}")
        print(f"   - Services: {info['service_count']}")
        print(f"   - Deployments: {info['deployment_count']}")
        print(f"   - Total CPU: {info['total_cpu_millicores']/1000:.2f} cores")
        print(f"   - Total Memory: {info['total_memory_bytes']/1024/1024/1024:.2f} GB")

        if info['nodes']:
            print("\n   Nodes:")
            for node in info['nodes'][:3]:  # Show first 3 nodes
                print(f"   - {node['name']}: {node['status']} ({node['version']})")
    else:
        print(f"❌ Failed to get cluster info: {cluster_info.get('error', 'unknown error')}")
    print()

    # 4. Test permissions
    print("4. Verifying RBAC permissions...")
    permissions = await k8s.verify_permissions(test_context)

    if 'summary' in permissions:
        summary = permissions['summary']
        print("✅ Permission summary:")
        print(f"   - Can read resources: {'✅' if summary['can_read'] else '❌'}")
        print(f"   - Can write resources: {'✅' if summary['can_write'] else '❌'}")
        print(f"   - Is admin: {'✅' if summary['is_admin'] else '❌'}")

        if permissions.get('errors'):
            print("\n   Missing permissions:")
            for error in permissions['errors']:
                print(f"   - ❌ {error}")
    print()

    # 5. Try to connect (full initialization)
    print("5. Attempting full connection...")
    try:
        await k8s.connect()
        print("✅ Successfully connected to Kubernetes cluster!")
        print(f"   - Current context: {k8s._current_context}")
        print(f"   - Available actions: {', '.join(await k8s.get_capabilities()['actions'][:5])}...")

        # Disconnect
        await k8s.disconnect()
        print("✅ Disconnected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

    print("\n✨ Test completed!")


if __name__ == "__main__":
    asyncio.run(test_k8s_integration())
