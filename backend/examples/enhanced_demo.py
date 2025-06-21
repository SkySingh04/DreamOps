#!/usr/bin/env python3
"""Enhanced demo showing complete repository access and intelligent incident analysis."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import our enhanced modules
try:
    from src.oncall_agent.config import get_config
    from src.oncall_agent.enhanced_agent import EnhancedOncallAgent, EnhancedPagerAlert
except ImportError as e:
    print(f"Import error: {e}")
    print("This demo requires the enhanced agent modules to be available.")
    exit(1)


async def demonstrate_enhanced_capabilities():
    """Demonstrate the enhanced oncall agent capabilities."""

    print("🚀 ENHANCED ONCALL AGENT - COMPLETE REPOSITORY ACCESS DEMO")
    print("=" * 80)
    print()

    # Check configuration
    config = get_config()
    if not config.github_token:
        print("❌ GITHUB_TOKEN not configured.")
        return False

    print("✅ Configuration verified")
    print(f"   - GitHub token: {config.github_token[:15]}...")
    print(f"   - Claude model: {config.claude_model}")
    print()

    try:
        # Initialize enhanced agent
        print("🔧 Initializing Enhanced Oncall Agent...")
        agent = EnhancedOncallAgent()
        print(f"✅ Enhanced integrations registered: {list(agent.mcp_integrations.keys())}")

        # Connect to integrations
        print("\n🔌 Connecting to enhanced integrations...")
        await agent.connect_integrations()
        print("✅ All enhanced integrations connected")

        # Create a realistic incident scenario
        incident_time = datetime.now(UTC) - timedelta(minutes=45)

        enhanced_alert = EnhancedPagerAlert(
            alert_id="ENHANCED-INCIDENT-001",
            severity="critical",
            service_name="api-gateway",
            description="API Gateway experiencing 25% error rate with database connection timeouts",
            timestamp=datetime.now(UTC).isoformat(),
            incident_start_time=incident_time.isoformat(),
            detection_delay=15,  # Detected 15 minutes after it started
            metadata={
                "error_rate": "25%",
                "primary_error": "database_connection_timeout",
                "affected_endpoints": ["/api/v1/users", "/api/v1/orders", "/api/v1/payments"],
                "region": "us-east-1",
                "load_balancer_status": "healthy",
                "database_status": "degraded"
            }
        )

        print("\n📋 Processing Enhanced Incident Alert:")
        print(f"   - Alert ID: {enhanced_alert.alert_id}")
        print(f"   - Service: {enhanced_alert.service_name}")
        print(f"   - Severity: {enhanced_alert.severity}")
        print(f"   - Incident Start: {enhanced_alert.incident_start_time}")
        print(f"   - Detection Delay: {enhanced_alert.detection_delay} minutes")
        print()

        # Perform comprehensive incident analysis
        print("🧠 Starting Comprehensive Incident Analysis...")
        print("   This will:")
        print("   📁 Clone/update complete repository")
        print("   📊 Analyze commit history and timeline")
        print("   🚀 Review deployment changes")
        print("   🔍 Search for error patterns in code")
        print("   📦 Analyze dependencies")
        print("   🤖 Generate AI-powered insights")
        print()

        result = await agent.handle_enhanced_incident(enhanced_alert)

        if result.get("status") == "error":
            print(f"❌ Analysis failed: {result.get('error')}")
            return False

        # Display results
        print("✅ COMPREHENSIVE ANALYSIS COMPLETE")
        print("=" * 50)

        # Repository Analysis Summary
        repo_analysis = result.get("repository_analysis", {})
        if repo_analysis.get("repository_data"):
            repo_data = repo_analysis["repository_data"]
            print("\n📁 REPOSITORY ANALYSIS:")
            print(f"   - Repository: {repo_data.get('repository', 'Unknown')}")
            print(f"   - Last Updated: {repo_data.get('last_updated', 'Unknown')}")
            if repo_data.get("file_structure"):
                structure = repo_data["file_structure"]
                print(f"   - Total Files: {structure.get('total_files', 0):,}")
                print(f"   - Key Files: {', '.join(structure.get('key_files', [])[:3])}")
                print(f"   - Languages: {dict(list(structure.get('languages', {}).items())[:3])}")

        # Commit Timeline Analysis
        if repo_analysis.get("commit_timeline"):
            timeline = repo_analysis["commit_timeline"]
            timeline_analysis = timeline.get("analysis", {})
            print("\n📊 COMMIT TIMELINE ANALYSIS:")
            print(f"   - Commits in timeframe: {timeline_analysis.get('total_commits', 0)}")
            print(f"   - Commit frequency: {timeline_analysis.get('commit_frequency', 0):.2f} commits/hour")
            print(f"   - Active authors: {', '.join(timeline_analysis.get('authors', []))}")

            if timeline_analysis.get("fix_commits"):
                print(f"   - Recent fix commits: {len(timeline_analysis['fix_commits'])}")
                for commit in timeline_analysis["fix_commits"][:2]:
                    print(f"     * {commit.get('hash', '')[:8]}: {commit.get('message', '')[:60]}")

        # Code Changes Analysis
        if repo_analysis.get("recent_code_changes"):
            changes = repo_analysis["recent_code_changes"]
            changes_analysis = changes.get("analysis", {})
            print("\n🔧 RECENT CODE CHANGES:")
            print(f"   - Files changed: {changes_analysis.get('total_files_changed', 0)}")
            print(f"   - Risk assessment: {changes_analysis.get('risk_assessment', 'Unknown')}")

            if changes_analysis.get("critical_files_changed"):
                print("   - Critical files modified:")
                for file in changes_analysis["critical_files_changed"][:3]:
                    print(f"     * {file}")

        # Problem Detection
        if repo_analysis.get("problem_detection"):
            problems = repo_analysis["problem_detection"]
            print("\n🚨 INTELLIGENT PROBLEM DETECTION:")

            if problems.get("high_probability"):
                print("   HIGH PROBABILITY ISSUES:")
                for problem in problems["high_probability"]:
                    print(f"     - {problem.get('type', '')}: {problem.get('description', '')}")

            if problems.get("medium_probability"):
                print("   MEDIUM PROBABILITY ISSUES:")
                for problem in problems["medium_probability"][:2]:
                    print(f"     - {problem.get('type', '')}: {problem.get('description', '')}")

        # AI Insights
        insights = result.get("intelligent_insights", {})
        if insights.get("claude_analysis"):
            print("\n🤖 AI-POWERED INSIGHTS:")
            print(f"   - Analysis Confidence: {insights.get('analysis_confidence', 'unknown').upper()}")
            print(f"   - Evidence Strength: {insights.get('evidence_strength', 'unknown').upper()}")
            print(f"   - Recommended Priority: {insights.get('recommended_priority', 'unknown').upper()}")
            print("\n   Claude Analysis (first 500 chars):")
            print(f"   {insights['claude_analysis'][:500]}...")

        # Immediate Actions
        if result.get("immediate_actions"):
            print("\n⚡ IMMEDIATE ACTIONS:")
            for action in result["immediate_actions"][:5]:
                print(f"   {action}")

        # Investigation Steps
        if result.get("investigation_steps"):
            print("\n🔬 INVESTIGATION STEPS:")
            for step in result["investigation_steps"][:3]:
                print(f"   {step}")

        # Incident Issue
        if result.get("incident_issue"):
            issue = result["incident_issue"]
            print("\n📋 INCIDENT ISSUE CREATED:")
            print(f"   - Title: {issue.get('title', 'Unknown')[:80]}...")
            print(f"   - Labels: {', '.join(issue.get('labels', []))}")

        print("\n🎯 ANALYSIS SUMMARY:")
        print(f"   - Status: {result.get('status', 'unknown').upper()}")
        print(f"   - Repository: {result.get('repository', 'unknown')}")
        print(f"   - Analysis Time: {result.get('analysis_timestamp', 'unknown')}")

        # Shutdown
        await agent.shutdown()
        print("\n✅ Enhanced agent shutdown complete")

        return True

    except Exception as e:
        print(f"\n❌ Error during enhanced demo: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_enhanced_capabilities():
    """Show the enhanced capabilities overview."""
    print("🎯 ENHANCED ONCALL AGENT CAPABILITIES")
    print("=" * 50)
    print()

    print("📁 COMPLETE REPOSITORY ACCESS:")
    print("   ✓ Automatic repository cloning/updating")
    print("   ✓ Full codebase analysis and search")
    print("   ✓ Configuration file analysis")
    print("   ✓ Dependency tracking")
    print()

    print("📊 INTELLIGENT TIMELINE ANALYSIS:")
    print("   ✓ Commit history correlation with incidents")
    print("   ✓ Deployment timeline tracking")
    print("   ✓ Author and change frequency analysis")
    print("   ✓ Hot file identification")
    print()

    print("🧠 AI-POWERED PROBLEM DETECTION:")
    print("   ✓ Pattern matching with alert descriptions")
    print("   ✓ Risk assessment of recent changes")
    print("   ✓ Critical file change detection")
    print("   ✓ Deployment correlation analysis")
    print()

    print("🚨 COMPREHENSIVE INCIDENT RESPONSE:")
    print("   ✓ Complete context gathering")
    print("   ✓ Intelligent root cause analysis")
    print("   ✓ Code-level problem identification")
    print("   ✓ Automated incident documentation")
    print()

    print("⚡ ENHANCED FEATURES:")
    print("   ✓ Server outage analysis (even when offline)")
    print("   ✓ Historical change correlation")
    print("   ✓ Intelligent priority escalation")
    print("   ✓ Prevention measure recommendations")
    print()


async def main():
    """Main demo function."""
    show_enhanced_capabilities()

    print("\n" + "="*80)
    print("STARTING ENHANCED INCIDENT ANALYSIS DEMO")
    print("="*80)

    success = await demonstrate_enhanced_capabilities()

    if success:
        print("\n🎉 ENHANCED CAPABILITIES DEMONSTRATION COMPLETE!")
        print("\nYour agent now has:")
        print("✅ Complete repository access and analysis")
        print("✅ Intelligent problem detection and correlation")
        print("✅ AI-powered incident analysis with full context")
        print("✅ Comprehensive incident response capabilities")
    else:
        print("\n❌ Enhanced capabilities demonstration failed")
        print("Check the logs above for specific issues")


if __name__ == "__main__":
    asyncio.run(main())
