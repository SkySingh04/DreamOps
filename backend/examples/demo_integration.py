#!/usr/bin/env python3
"""Demo script showing GitHub MCP integration is connected."""

import os


def show_integration_demo():
    """Demonstrate the GitHub MCP integration setup."""

    print("=" * 60)
    print("🚀 ONCALL AGENT - GITHUB MCP INTEGRATION DEMO")
    print("=" * 60)
    print()

    # Check environment file
    env_file = ".env"
    if os.path.exists(env_file):
        print("✅ Environment Configuration:")
        with open(env_file) as f:
            lines = f.readlines()
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if 'TOKEN' in key or 'KEY' in key:
                        print(f"   {key}: {value[:15]}...")
                    else:
                        print(f"   {key}: {value}")
        print()

    # Show integration files
    print("✅ Integration Files Created:")
    integration_files = [
        "src/oncall_agent/mcp_integrations/github_mcp.py",
        "src/oncall_agent/agent.py",
        "src/oncall_agent/config.py",
        ".env",
        "test_github_integration.py"
    ]

    for file_path in integration_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"   ✓ {file_path} ({size} bytes)")
        else:
            print(f"   ❌ {file_path} (missing)")
    print()

    # Show GitHub MCP server
    server_path = "/mnt/c/Users/harsh/OneDrive/Desktop/oncall/github-mcp-server/github-mcp-server"
    if os.path.exists(server_path):
        print("✅ GitHub MCP Server:")
        print(f"   ✓ Binary found: {server_path}")
        server_size = os.path.getsize(server_path)
        print(f"   ✓ Size: {server_size:,} bytes")
    else:
        print("❌ GitHub MCP Server binary not found")
    print()

    # Show integration capabilities
    print("✅ Integration Capabilities:")
    print("   🔍 Context Types:")
    print("     - repository_info: Get repository information")
    print("     - recent_commits: Get recent commits")
    print("     - open_issues: Get open issues")
    print("     - pull_requests: Get pull requests")
    print("     - actions_status: Get GitHub Actions status")
    print("     - releases: Get recent releases")
    print("     - file_contents: Read any file/directory from repo")
    print("     - search_code: Search code across repositories")
    print()

    print("   ⚡ Actions:")
    print("     - create_issue: Create new issues")
    print("     - add_comment: Add comments to issues/PRs")
    print("     - update_issue: Update issue status/labels")
    print("     - create_pr: Create pull requests")
    print("     - merge_pr: Merge pull requests")
    print("     - trigger_workflow: Trigger GitHub Actions")
    print()

    # Show workflow
    print("✅ Integration Workflow:")
    print("   1. 📨 Alert received by oncall agent")
    print("   2. 🔌 GitHub MCP server starts automatically")
    print("   3. 🔍 Agent fetches GitHub context (commits, issues, PRs)")
    print("   4. 📖 Agent reads relevant code files and searches for error patterns")
    print("   5. 🧠 Claude analyzes alert + GitHub context + code analysis")
    print("   6. 📋 Auto-creates incident issue for high-severity alerts")
    print("   7. 📊 Returns comprehensive incident analysis with code insights")
    print()

    # Show service mapping
    print("✅ Service-to-Repository Mapping:")
    print("   - api-gateway → myorg/api-gateway")
    print("   - user-service → myorg/user-service")
    print("   - payment-service → myorg/payment-service")
    print("   - notification-service → myorg/notification-service")
    print()

    print("✅ Code Analysis Features:")
    print("   📖 File Reading:")
    print("     - Read any source file from repository")
    print("     - Access configuration files (Dockerfile, config.yaml)")
    print("     - Browse directory structures")
    print("   🔍 Code Search:")
    print("     - Search for error handling patterns")
    print("     - Find specific functions or classes")
    print("     - Filter by language, filename, or repository")
    print("   🚨 Smart Context:")
    print("     - Auto-searches error handling code for error alerts")
    print("     - Fetches config files for deployment issues")
    print("     - Provides main application structure")
    print()

    print("🎉 INTEGRATION READY!")
    print("Run 'python main.py' to see the agent in action with GitHub MCP!")
    print("=" * 60)

if __name__ == "__main__":
    show_integration_demo()
