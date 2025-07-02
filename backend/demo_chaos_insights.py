#!/usr/bin/env python3
"""Demo: Chaos Engineering → Notion Documentation → AI Insights"""

import asyncio

from src.oncall_agent.agent_commands import AgentCommands


async def demo_chaos_insights():
    """Demonstrate the complete chaos to insights flow."""
    print("🎯 DreamOps Chaos → Insights Demo")
    print("=" * 50)
    print("\nThis demo will:")
    print("1. Analyze recent Kubernetes chaos")
    print("2. Provide infrastructure health insights")
    print("3. Generate actionable recommendations")
    print("\n" + "="*50)

    # Step 1: Analyze recent chaos
    print("\n📊 Analyzing Recent Chaos Engineering Results...")
    chaos_result = await AgentCommands.analyze_recent_chaos()
    print(chaos_result["response"])

    # Step 2: Get recommendations
    print("\n" + "="*50)
    print("\n💡 Getting Infrastructure Recommendations...")
    recommendations = await AgentCommands.get_actionable_recommendations()
    print(recommendations["response"])

    # Step 3: Analyze specific service if chaos created incidents
    if chaos_result["success"] and chaos_result["data"]["services_affected"]:
        service = chaos_result["data"]["services_affected"][0]
        if service and service != "unknown":
            print("\n" + "="*50)
            print(f"\n🔍 Deep Dive: Analyzing '{service}' Service...")
            service_analysis = await AgentCommands.analyze_service_reliability(service)
            print(service_analysis["response"])

    # Step 4: Show how to get full report
    print("\n" + "="*50)
    print("\n📄 To get a full infrastructure health report, I can run:")
    print("   await AgentCommands.get_infrastructure_health_report()")
    print("\nThis generates a comprehensive markdown report with:")
    print("   - Incident trends and patterns")
    print("   - Service reliability metrics")
    print("   - Prioritized recommendations")
    print("   - Historical incident links")

    print("\n✅ Demo Complete!")
    print("\n🎯 Key Takeaways:")
    print("1. All chaos incidents are automatically documented in Notion")
    print("2. The AI agent analyzes patterns across all incidents")
    print("3. Actionable recommendations are generated based on real data")
    print("4. Service-specific insights help prioritize improvements")


if __name__ == "__main__":
    asyncio.run(demo_chaos_insights())
