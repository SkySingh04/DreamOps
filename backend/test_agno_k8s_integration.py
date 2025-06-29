#!/usr/bin/env python3
"""
Test script for Agno Kubernetes MCP integration.

This script tests:
1. Basic Agno agent initialization with MCP tools
2. Kubernetes MCP server connectivity
3. Remote cluster connection without local kubeconfig
4. Incident response workflow
"""

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.oncall_agent.agno_kubernetes_agent import DreamOpsK8sAgent
from src.oncall_agent.services.kubernetes_auth import AuthMethod, K8sCredentials
from src.oncall_agent.utils.logger import get_logger

# Load environment variables
load_dotenv(".env.local")

logger = get_logger(__name__)


async def test_basic_mcp_connection():
    """Test 1: Basic MCP server connection with local kubeconfig."""
    print("\n" + "="*60)
    print("TEST 1: Basic MCP Server Connection")
    print("="*60)
    
    agent = DreamOpsK8sAgent()
    
    try:
        # Initialize with default local MCP server
        initialized = await agent.initialize_with_mcp()
        
        if initialized:
            print("✅ Successfully initialized Agno agent with K8s MCP tools")
            
            # Test the integration
            test_result = await agent.test_mcp_integration()
            print(f"\nMCP Integration Test Results:")
            print(json.dumps(test_result, indent=2))
            
            return True
        else:
            print("❌ Failed to initialize Agno agent")
            return False
            
    except Exception as e:
        print(f"❌ Error during basic MCP connection test: {e}")
        return False
    finally:
        await agent.cleanup()


async def test_remote_cluster_connection():
    """Test 2: Remote cluster connection with credentials."""
    print("\n" + "="*60)
    print("TEST 2: Remote Cluster Connection (Without Local Kubeconfig)")
    print("="*60)
    
    # Example: Service Account authentication
    credentials = K8sCredentials(
        auth_method=AuthMethod.SERVICE_ACCOUNT,
        cluster_endpoint="https://your-k8s-cluster.example.com:6443",
        cluster_name="remote-production",
        service_account_token=os.getenv("K8S_SERVICE_ACCOUNT_TOKEN", "dummy-token"),
        ca_certificate=os.getenv("K8S_CA_CERTIFICATE", "dummy-ca-cert"),
        namespace="default",
        verify_ssl=True
    )
    
    agent = DreamOpsK8sAgent()
    
    try:
        print(f"Attempting to connect to remote cluster: {credentials.cluster_name}")
        print(f"Endpoint: {credentials.cluster_endpoint}")
        print(f"Auth method: {credentials.auth_method.value}")
        
        # Connect to remote cluster
        result = await agent.connect_remote_cluster(
            user_id=1,  # Test user ID
            credentials=credentials
        )
        
        if result.get("connected"):
            print("✅ Successfully connected to remote cluster")
            print(f"Cluster version: {result.get('cluster_version')}")
            print(f"Platform: {result.get('platform')}")
            print(f"Agent initialized: {result.get('agent_initialized')}")
            print(f"MCP tools available: {result.get('mcp_tools_available')}")
            return True
        else:
            print(f"❌ Failed to connect: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during remote cluster connection: {e}")
        return False
    finally:
        await agent.cleanup()


async def test_incident_response():
    """Test 3: Simulate incident response workflow."""
    print("\n" + "="*60)
    print("TEST 3: Incident Response Workflow")
    print("="*60)
    
    # Create test alert
    test_alert = {
        "alert_id": "test-123",
        "title": "Pod CrashLoopBackOff in production",
        "description": "Pod app-service-7b9c5d4f6-xz9kl is in CrashLoopBackOff state",
        "severity": "high",
        "timestamp": datetime.now(UTC).isoformat(),
        "metadata": {
            "cluster": "production",
            "namespace": "default",
            "deployment": "app-service",
            "pod": "app-service-7b9c5d4f6-xz9kl",
            "service": "app-service"
        }
    }
    
    agent = DreamOpsK8sAgent()
    
    try:
        print("Processing test alert:")
        print(json.dumps(test_alert, indent=2))
        
        # Handle the alert
        response = await agent.handle_pagerduty_alert(test_alert)
        
        print("\nAgent Response:")
        print(json.dumps(response, indent=2, default=str))
        
        if response.get("status") == "success":
            print("\n✅ Incident response successful")
            print(f"Actions taken: {response.get('actions_taken', [])}")
            return True
        else:
            print(f"\n❌ Incident response failed: {response.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during incident response: {e}")
        return False
    finally:
        await agent.cleanup()


async def test_yolo_mode():
    """Test 4: YOLO mode automated remediation."""
    print("\n" + "="*60)
    print("TEST 4: YOLO Mode Automated Remediation")
    print("="*60)
    
    # Enable YOLO mode
    os.environ["K8S_ENABLE_DESTRUCTIVE_OPERATIONS"] = "true"
    
    agent = DreamOpsK8sAgent()
    
    # OOM Kill alert
    oom_alert = {
        "alert_id": "oom-456",
        "title": "Pod OOMKilled - memory exhausted",
        "description": "Pod backend-api-5f9c8d7b6-abc123 was OOMKilled due to memory exhaustion",
        "severity": "critical",
        "timestamp": datetime.now(UTC).isoformat(),
        "metadata": {
            "cluster": "production",
            "namespace": "api",
            "deployment": "backend-api",
            "pod": "backend-api-5f9c8d7b6-abc123"
        }
    }
    
    try:
        print(f"YOLO Mode Enabled: {agent.enable_yolo_mode}")
        print("\nProcessing OOM alert with automated remediation:")
        print(json.dumps(oom_alert, indent=2))
        
        response = await agent.handle_pagerduty_alert(oom_alert)
        
        print("\nYOLO Mode Response:")
        print(json.dumps(response, indent=2, default=str))
        
        if response.get("yolo_mode"):
            print("\n✅ YOLO mode executed automated remediation")
            return True
        else:
            print("\n❌ YOLO mode not active")
            return False
            
    except Exception as e:
        print(f"❌ Error during YOLO mode test: {e}")
        return False
    finally:
        await agent.cleanup()
        # Reset YOLO mode
        os.environ["K8S_ENABLE_DESTRUCTIVE_OPERATIONS"] = "false"


async def test_multi_cluster_support():
    """Test 5: Multi-cluster support."""
    print("\n" + "="*60)
    print("TEST 5: Multi-Cluster Support")
    print("="*60)
    
    agent = DreamOpsK8sAgent()
    
    try:
        # List available clusters
        clusters = await agent.list_available_clusters(user_id=1)
        
        print(f"Available clusters: {len(clusters)}")
        for cluster in clusters:
            print(f"\n- {cluster['name']} ({cluster['type']})")
            print(f"  Status: {cluster.get('connection_status', 'unknown')}")
            print(f"  Namespace: {cluster.get('namespace', 'default')}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error listing clusters: {e}")
        return False
    finally:
        await agent.cleanup()


async def main():
    """Run all tests."""
    print("🚀 Starting Agno Kubernetes MCP Integration Tests")
    print(f"Timestamp: {datetime.now(UTC).isoformat()}")
    
    # Check environment
    print("\nEnvironment Check:")
    print(f"- ANTHROPIC_API_KEY: {'✅ Set' if os.getenv('ANTHROPIC_API_KEY') else '❌ Not set'}")
    print(f"- K8S_ENABLED: {os.getenv('K8S_ENABLED', 'false')}")
    print(f"- K8S_MCP_SERVER_URL: {os.getenv('K8S_MCP_SERVER_URL', 'Not set')}")
    print(f"- K8S_ENABLE_DESTRUCTIVE_OPERATIONS: {os.getenv('K8S_ENABLE_DESTRUCTIVE_OPERATIONS', 'false')}")
    
    # Run tests
    tests = [
        ("Basic MCP Connection", test_basic_mcp_connection),
        ("Remote Cluster Connection", test_remote_cluster_connection),
        ("Incident Response", test_incident_response),
        ("YOLO Mode", test_yolo_mode),
        ("Multi-Cluster Support", test_multi_cluster_support)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(1 for _, result in results if result)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Agno K8s MCP integration is working correctly.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} tests failed. Please check the logs above.")


if __name__ == "__main__":
    asyncio.run(main())