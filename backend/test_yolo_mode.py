#!/usr/bin/env python3
"""Test script for YOLO mode execution with the enhanced agent."""

import asyncio
import logging
import sys
from datetime import datetime

from src.oncall_agent.agent import PagerAlert
from src.oncall_agent.agent_enhanced import EnhancedOncallAgent
from src.oncall_agent.api.schemas import AIMode
from src.oncall_agent.config import get_config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_yolo_mode():
    """Test the enhanced agent in YOLO mode with different scenarios."""
    
    print("\n" + "="*80)
    print("🚀 TESTING ENHANCED ONCALL AGENT - YOLO MODE 🚀")
    print("="*80 + "\n")
    
    # Create agent in YOLO mode
    agent = EnhancedOncallAgent(ai_mode=AIMode.YOLO)
    
    try:
        # Connect integrations
        print("Connecting to Kubernetes...")
        await agent.connect_integrations()
        print("✅ Connected successfully\n")
        
        # Test scenarios
        scenarios = [
            {
                "name": "Pod CrashLoopBackOff",
                "alert": PagerAlert(
                    alert_id="test-001",
                    severity="high",
                    service_name="payment-service",
                    description="Pod payment-service-7d9f8b6c5-x2n4m is in CrashLoopBackOff state",
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "pod_name": "payment-service-7d9f8b6c5-x2n4m",
                        "namespace": "fuck-kubernetes-test",
                        "restart_count": 5
                    }
                )
            },
            {
                "name": "Service Down - No Endpoints",
                "alert": PagerAlert(
                    alert_id="test-002",
                    severity="critical",
                    service_name="api-gateway",
                    description="Service api-gateway is down - no endpoints available",
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "service_name": "api-gateway",
                        "namespace": "fuck-kubernetes-test",
                        "endpoint_count": 0
                    }
                )
            },
            {
                "name": "High Memory Usage",
                "alert": PagerAlert(
                    alert_id="test-003",
                    severity="high",
                    service_name="analytics-service",
                    description="Memory usage above threshold (90%) for analytics-service",
                    timestamp=datetime.utcnow().isoformat(),
                    metadata={
                        "deployment_name": "analytics-service",
                        "namespace": "fuck-kubernetes-test",
                        "memory_usage_percent": 92
                    }
                )
            }
        ]
        
        # Process each scenario
        for i, scenario in enumerate(scenarios):
            print(f"\n{'='*60}")
            print(f"📋 Scenario {i+1}: {scenario['name']}")
            print(f"{'='*60}\n")
            
            # Handle the alert
            result = await agent.handle_pager_alert(
                scenario['alert'],
                auto_remediate=True  # Force auto-remediation for testing
            )
            
            # Display results
            print(f"\n🔍 Alert Analysis:")
            print(f"- Alert Type: {result.get('k8s_alert_type', 'Unknown')}")
            print(f"- AI Mode: {result['ai_mode']}")
            print(f"- Auto-remediation: {'Enabled' if result.get('auto_remediation_enabled') else 'Disabled'}")
            
            if result.get('resolution_actions'):
                print(f"\n📋 Proposed Actions ({len(result['resolution_actions'])} total):")
                for action in result['resolution_actions']:
                    print(f"  - {action['action_type']}: {action['description']}")
                    print(f"    Confidence: {action['confidence']:.2f}, Risk: {action['risk_level']}")
            
            if result.get('execution_results'):
                exec_results = result['execution_results']
                print(f"\n🤖 Execution Results:")
                print(f"- Actions Executed: {exec_results['actions_executed']}")
                print(f"- Successful: {exec_results['actions_successful']}")
                print(f"- Failed: {exec_results['actions_failed']}")
                
                if exec_results.get('execution_details'):
                    print(f"\n📝 Execution Details:")
                    for detail in exec_results['execution_details']:
                        action = detail['action']
                        if detail.get('executed'):
                            status = "✅ SUCCESS" if detail['result']['success'] else "❌ FAILED"
                            print(f"  - {action.action_type}: {status}")
                            if detail.get('verification'):
                                verified = "✓" if detail['verification']['verified'] else "✗"
                                print(f"    Verification: {verified} - {detail['verification'].get('details', '')}")
                        else:
                            print(f"  - {action.action_type}: ⏭️ SKIPPED ({detail.get('reason', 'Unknown')})")
            
            # Small delay between scenarios
            if i < len(scenarios) - 1:
                print("\nWaiting 5 seconds before next scenario...")
                await asyncio.sleep(5)
        
        # Test mode switching
        print(f"\n\n{'='*60}")
        print("🔄 Testing Mode Switching")
        print(f"{'='*60}\n")
        
        # Switch to APPROVAL mode
        await agent.set_ai_mode(AIMode.APPROVAL)
        print("Switched to APPROVAL mode")
        
        # Test with approval mode
        result = await agent.handle_pager_alert(scenarios[0]['alert'])
        print(f"- Actions requiring approval: {sum(1 for a in result.get('resolution_actions', []) if a['risk_level'] != 'low')}")
        
        # Switch to PLAN mode
        await agent.set_ai_mode(AIMode.PLAN)
        print("\nSwitched to PLAN mode")
        
        # Test with plan mode
        result = await agent.handle_pager_alert(scenarios[0]['alert'])
        if result.get('command_preview'):
            print("- Command Preview:")
            for preview in result['command_preview']:
                print(f"  {preview['command']} (would execute: {preview['would_execute']})")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n\nShutting down agent...")
        await agent.shutdown()
        print("✅ Test complete")

async def test_with_fuck_kubernetes():
    """Test with actual Kubernetes issues created by fuck_kubernetes.sh."""
    
    print("\n" + "="*80)
    print("🔥 TESTING WITH FUCK_KUBERNETES.SH ISSUES 🔥")
    print("="*80 + "\n")
    
    print("Prerequisites:")
    print("1. Run: ./fuck_kubernetes.sh 1  (to create pod crash)")
    print("2. Wait for pods to be in CrashLoopBackOff state")
    print("3. This test will detect and auto-fix the issues\n")
    
    input("Press Enter when ready to continue...")
    
    # Create agent in YOLO mode
    agent = EnhancedOncallAgent(ai_mode=AIMode.YOLO)
    
    try:
        await agent.connect_integrations()
        
        # Check for issues in the test namespace
        if agent.k8s_mcp:
            print("\n🔍 Checking for Kubernetes issues...")
            
            # Get pods in test namespace
            result = await agent.k8s_mcp.execute_kubectl_command(
                ["get", "pods", "-n", "fuck-kubernetes-test", "-o", "json"],
                auto_approve=True
            )
            
            if result['success']:
                import json
                pods_data = json.loads(result['output'])
                problematic_pods = [
                    pod for pod in pods_data.get('items', [])
                    if pod['status']['phase'] != 'Running' or 
                    any(cs.get('state', {}).get('waiting', {}).get('reason') in 
                        ['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull']
                        for cs in pod['status'].get('containerStatuses', []))
                ]
                
                print(f"Found {len(problematic_pods)} problematic pods")
                
                # Create alerts for each problematic pod
                for pod in problematic_pods:
                    pod_name = pod['metadata']['name']
                    namespace = pod['metadata']['namespace']
                    
                    # Determine issue type
                    issue_type = "Unknown"
                    for cs in pod['status'].get('containerStatuses', []):
                        if cs.get('state', {}).get('waiting', {}).get('reason') == 'CrashLoopBackOff':
                            issue_type = "CrashLoopBackOff"
                        elif cs.get('state', {}).get('waiting', {}).get('reason') in ['ImagePullBackOff', 'ErrImagePull']:
                            issue_type = "ImagePullBackOff"
                    
                    print(f"\n🚨 Processing: {pod_name} ({issue_type})")
                    
                    alert = PagerAlert(
                        alert_id=f"k8s-{pod_name}",
                        severity="high",
                        service_name=pod_name.split('-')[0],
                        description=f"Pod {pod_name} is in {issue_type} state",
                        timestamp=datetime.utcnow().isoformat(),
                        metadata={
                            "pod_name": pod_name,
                            "namespace": namespace,
                            "issue_type": issue_type
                        }
                    )
                    
                    # Let the agent handle it
                    result = await agent.handle_pager_alert(alert, auto_remediate=True)
                    
                    if result.get('execution_results'):
                        print(f"✅ Remediation attempted: {result['execution_results']['actions_successful']} successful actions")
                    
                    # Small delay between fixes
                    await asyncio.sleep(3)
            
            # Final status check
            print("\n📊 Final Status Check:")
            final_result = await agent.k8s_mcp.execute_kubectl_command(
                ["get", "pods", "-n", "fuck-kubernetes-test"],
                auto_approve=True
            )
            if final_result['success']:
                print(final_result['output'])
                
    finally:
        await agent.shutdown()

def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--fuck-kubernetes":
        asyncio.run(test_with_fuck_kubernetes())
    else:
        asyncio.run(test_yolo_mode())

if __name__ == "__main__":
    main()