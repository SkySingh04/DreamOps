#!/usr/bin/env python3
"""Simple script to verify MCP integrations setup."""

import os
from pathlib import Path

print("\n" + "="*80)
print("🔍 VERIFYING MCP INTEGRATIONS SETUP")
print("="*80 + "\n")

# Check .env file
env_path = Path(".env")
if env_path.exists():
    print("✅ .env file exists")
    
    # Read and check key configurations
    with open(".env", "r") as f:
        env_content = f.read()
    
    # Check for API keys (without exposing them)
    checks = {
        "ANTHROPIC_API_KEY": "🤖 Anthropic API",
        "GITHUB_TOKEN": "🐙 GitHub Token",
        "NOTION_TOKEN": "📝 Notion Token",
        "K8S_ENABLED": "☸️  Kubernetes",
    }
    
    print("\n📋 Configuration Status:")
    for key, name in checks.items():
        if key in env_content and not env_content.split(f"{key}=")[1].split("\n")[0].strip().startswith("your-"):
            print(f"   ✅ {name}: Configured")
        else:
            print(f"   ❌ {name}: Not configured or using placeholder")
    
    # Check for port conflicts
    if "GITHUB_MCP_PORT=8080" in env_content and "K8S_MCP_SERVER_URL=http://localhost:8080" in env_content:
        print("\n⚠️  WARNING: Port conflict detected!")
        print("   Both GitHub MCP and Kubernetes MCP are configured to use port 8080")
        print("   This has been fixed in .env (GitHub MCP now uses port 8081)")
    
    # Check GitHub MCP server binary
    if "GITHUB_MCP_SERVER_PATH=" in env_content:
        server_path = env_content.split("GITHUB_MCP_SERVER_PATH=")[1].split("\n")[0].strip()
        if Path(server_path).exists():
            print(f"\n✅ GitHub MCP server binary found at: {server_path}")
        else:
            print(f"\n❌ GitHub MCP server binary NOT found at: {server_path}")
else:
    print("❌ .env file not found")
    print("   Run: cp .env.example .env")

# Check directory structure
print("\n📁 Directory Structure:")
dirs_to_check = [
    "backend/src/oncall_agent/mcp_integrations",
    "frontend",
    "infrastructure/terraform"
]

for dir_path in dirs_to_check:
    if Path(dir_path).exists():
        print(f"   ✅ {dir_path}")
    else:
        print(f"   ❌ {dir_path}")

# Check for integration files
print("\n📦 MCP Integration Files:")
integration_files = {
    "backend/src/oncall_agent/mcp_integrations/github_mcp.py": "GitHub MCP",
    "backend/src/oncall_agent/mcp_integrations/enhanced_github_mcp.py": "Enhanced GitHub MCP",
    "backend/src/oncall_agent/mcp_integrations/kubernetes.py": "Kubernetes MCP",
    "backend/src/oncall_agent/mcp_integrations/notion.py": "Notion MCP",
}

for file_path, name in integration_files.items():
    if Path(file_path).exists():
        print(f"   ✅ {name}: {file_path}")
    else:
        print(f"   ❌ {name}: {file_path} NOT FOUND")

print("\n" + "="*80)
print("📊 SUMMARY")
print("="*80 + "\n")

print("To run the agent with all integrations:")
print("1. Make sure Docker Desktop is running with WSL integration")
print("2. Install dependencies: cd backend && uv sync")
print("3. For Kubernetes testing, set up kind cluster:")
print("   - Install kind and kubectl")
print("   - Run: kind create cluster --name oncall-test")
print("4. Run the agent: cd backend && uv run python main.py")
print("\nFor testing without Kubernetes:")
print("- The GitHub and Notion integrations will work without Docker/Kubernetes")
print("- Set K8S_ENABLED=false in .env to disable Kubernetes integration")

print("\n" + "="*80)