#!/usr/bin/env python3
"""Start the GitHub MCP server independently for testing."""

import os
import subprocess
import sys


def start_github_mcp_server():
    """Start the GitHub MCP server."""
    print("🚀 Starting GitHub MCP Server...")

    # Check if GitHub token is set
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ Error: GITHUB_TOKEN environment variable not set!")
        print("Please set it in your .env file or export it:")
        print("export GITHUB_TOKEN=your-github-personal-access-token")
        return

    # Path to the GitHub MCP server binary
    server_path = "/mnt/c/Users/harsh/OneDrive/Desktop/oncall/github-mcp-server/github-mcp-server"

    # Check if the binary exists
    if not os.path.exists(server_path):
        print(f"❌ Error: GitHub MCP server not found at {server_path}")
        return

    # Check if it's executable
    if not os.access(server_path, os.X_OK):
        print("⚠️  Making the binary executable...")
        os.chmod(server_path, 0o755)

    print(f"✅ GitHub MCP server found at: {server_path}")
    print(f"✅ GitHub token configured (length: {len(github_token)})")
    print("📡 Starting server in stdio mode...")
    print("-" * 50)
    print("Server is running. Press Ctrl+C to stop.")
    print("-" * 50)

    # Set up environment with GitHub token
    env = os.environ.copy()
    env["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token

    # Start the server
    process = None
    try:
        process = subprocess.Popen(
            [server_path, "stdio"],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=env
        )

        print(f"✅ Server started with PID: {process.pid}")
        print("\nYou can now send MCP commands to the server via stdin.")
        print("Example initialization message:")
        print('{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}')
        print("\nWaiting for input...\n")

        # Wait for the process to complete
        process.wait()

    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down GitHub MCP server...")
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        print("✅ Server stopped.")
    except Exception as e:
        print(f"❌ Error: {e}")
        if process:
            process.kill()

if __name__ == "__main__":
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()

    start_github_mcp_server()
