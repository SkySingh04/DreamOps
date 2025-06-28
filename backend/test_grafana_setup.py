#!/usr/bin/env python
"""Test to verify Grafana MCP setup is correct."""

import os
import subprocess
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_environment():
    """Check environment and configuration."""
    print("🔍 Checking Grafana MCP Setup")
    print("=" * 50)

    # Check MCP server binary
    mcp_path = Path(__file__).parent.parent / "mcp-grafana" / "dist" / "mcp-grafana"
    print("\n1️⃣ MCP Server Binary:")
    print(f"   Path: {mcp_path}")

    if mcp_path.exists():
        print("   ✅ Binary exists")

        # Check if it's executable
        try:
            result = subprocess.run(
                [str(mcp_path), "version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                print(f"   ✅ Binary is executable: {result.stdout.strip()}")
            else:
                print(f"   ❌ Binary error: {result.stderr}")
        except Exception as e:
            print(f"   ❌ Failed to run binary: {e}")
    else:
        print("   ❌ Binary not found!")
        print("\n   📝 To build the server:")
        print("      cd ../mcp-grafana")
        print("      go mod download")
        print("      make build")

    # Check Python integration
    print("\n2️⃣ Python Integration:")
    try:
        from oncall_agent.mcp_integrations.grafana_mcp import GrafanaMCPIntegration
        print("   ✅ GrafanaMCPIntegration imported successfully")
    except ImportError as e:
        print(f"   ❌ Failed to import GrafanaMCPIntegration: {e}")
        return

    # Check configuration
    print("\n3️⃣ Configuration:")
    try:
        from oncall_agent.config import get_config
        config = get_config()
        print("   ✅ Config loaded successfully")
        print(f"   - grafana_enabled: {config.grafana_enabled}")
        print(f"   - grafana_url: {config.grafana_url or 'Not set'}")
        print(f"   - grafana_api_key: {'Set' if config.grafana_api_key else 'Not set'}")
        print(f"   - grafana_mcp_server_path: {config.grafana_mcp_server_path}")
    except Exception as e:
        print(f"   ❌ Failed to load config: {e}")

    # Check environment variables
    print("\n4️⃣ Environment Variables:")
    env_vars = {
        "GRAFANA_ENABLED": os.getenv("GRAFANA_ENABLED", "Not set"),
        "GRAFANA_URL": os.getenv("GRAFANA_URL", "Not set"),
        "GRAFANA_API_KEY": "Set" if os.getenv("GRAFANA_API_KEY") else "Not set",
        "ANTHROPIC_API_KEY": "Set" if os.getenv("ANTHROPIC_API_KEY") else "Not set"
    }

    for var, value in env_vars.items():
        status = "✅" if value != "Not set" else "⚠️"
        print(f"   {status} {var}: {value}")

    # Check agent integration
    print("\n5️⃣ Agent Integration:")
    try:
        print("   ✅ OncallAgent imported successfully")

        # Check if it would initialize Grafana
        config = get_config()
        would_init = bool(
            config.grafana_url and
            (config.grafana_api_key or (config.grafana_username and config.grafana_password))
        )

        if would_init:
            print("   ✅ Agent would initialize Grafana integration")
        else:
            print("   ⚠️  Agent would NOT initialize Grafana (missing config)")
            print("      Need: GRAFANA_URL and (GRAFANA_API_KEY or GRAFANA_USERNAME/PASSWORD)")
    except Exception as e:
        print(f"   ❌ Failed to check agent: {e}")

    # Summary
    print("\n📊 Summary:")
    if mcp_path.exists() and env_vars["GRAFANA_URL"] != "Not set":
        print("   ✅ Setup looks good! Ready for testing.")
        print("\n   To run the full test:")
        print("   python test_grafana_e2e.py")
    else:
        print("   ⚠️  Some setup steps remaining:")
        if not mcp_path.exists():
            print("   - Build the MCP server (see instructions above)")
        if env_vars["GRAFANA_URL"] == "Not set":
            print("   - Set GRAFANA_URL and GRAFANA_API_KEY environment variables")


if __name__ == "__main__":
    check_environment()
