#!/usr/bin/env python3
"""Test the complete integration flow end-to-end."""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.oncall_agent.agent import OncallAgent, PagerAlert
from src.oncall_agent.frontend_integration import send_incident_to_dashboard, send_ai_action_to_dashboard
from src.oncall_agent.config import get_config


async def test_complete_flow():
    """Test the complete flow from alert to dashboard."""
    print("=" * 80)
    print("🧪 Testing Complete OnCall Agent Flow")
    print("=" * 80)
    
    # Step 1: Create a test alert
    print("\n1️⃣ Creating test alert...")
    alert = PagerAlert(
        alert_id=f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        severity="critical",
        service_name="test-service",
        description="Pod test-deployment-abc123 is in CrashLoopBackOff state",
        timestamp=datetime.now().isoformat(),
        metadata={
            "namespace": "default",
            "pod_name": "test-deployment-abc123",
            "alert_type": "pod_crash"
        }
    )
    print(f"   ✅ Alert created: {alert.alert_id}")
    
    # Step 2: Test direct dashboard integration
    print("\n2️⃣ Testing direct dashboard integration...")
    try:
        # Test incident creation
        incident_result = await send_incident_to_dashboard({
            "alert_name": alert.service_name,
            "description": alert.description,
            "alert_type": "pod_crash",
            "resource_id": alert.alert_id,
            "severity": alert.severity,
            "metadata": alert.metadata
        })
        
        if incident_result and incident_result.get('id'):
            print(f"   ✅ Incident created in dashboard with ID: {incident_result['id']}")
            incident_id = incident_result['id']
        else:
            print("   ❌ Failed to create incident in dashboard")
            incident_id = None
            
        # Test AI action recording
        ai_action_result = await send_ai_action_to_dashboard(
            action="test_action",
            description="Testing AI action recording",
            incident_id=incident_id
        )
        
        if ai_action_result:
            print("   ✅ AI action recorded successfully")
        else:
            print("   ❌ Failed to record AI action")
            
    except Exception as e:
        print(f"   ❌ Dashboard integration error: {e}")
        return False
    
    # Step 3: Test full agent flow
    print("\n3️⃣ Testing full agent flow...")
    try:
        # Initialize agent
        agent = OncallAgent()
        await agent.connect_integrations()
        print("   ✅ Agent initialized and integrations connected")
        
        # Process alert
        print("   🔄 Processing alert through agent...")
        result = await agent.handle_pager_alert(alert)
        
        if result.get('status') == 'analyzed':
            print("   ✅ Alert processed successfully")
            print(f"   📊 Context gathered from: {list(result.get('context_gathered', {}).keys())}")
        else:
            print(f"   ❌ Alert processing failed: {result}")
            
        # Shutdown agent
        await agent.shutdown()
        print("   ✅ Agent shutdown complete")
        
    except Exception as e:
        print(f"   ❌ Agent processing error: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("✅ Complete flow test finished!")
    print("=" * 80)
    print("\n📝 Next steps:")
    print("1. Check the dashboard at http://localhost:3000/dashboard")
    print("2. You should see the test incident and AI actions")
    print("3. Run './fuck_kubernetes.sh 1' to test with real Kubernetes alerts")
    
    return True


async def main():
    """Run the complete flow test."""
    # Check if required services are configured
    config = get_config()
    
    print("🔍 Checking configuration...")
    print(f"   - Anthropic API Key: {'✅ Set' if config.anthropic_api_key else '❌ Missing'}")
    print(f"   - Kubernetes enabled: {'✅ Yes' if config.k8s_enabled else '❌ No'}")
    print(f"   - PagerDuty enabled: {'✅ Yes' if config.pagerduty_enabled else '❌ No'}")
    
    if not config.anthropic_api_key:
        print("\n❌ Please set ANTHROPIC_API_KEY in your .env file")
        return
    
    # Run the test
    success = await test_complete_flow()
    
    if not success:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())