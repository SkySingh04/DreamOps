#!/usr/bin/env python3
"""Demo script to show GitHub MCP server in action."""

import asyncio
import json
import os
import subprocess
from typing import Any


class GitHubMCPDemo:
    """Demo client for GitHub MCP server."""

    def __init__(self):
        self.server_process = None
        self.message_id = 1

    async def start_server(self):
        """Start the GitHub MCP server."""
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            print("❌ Error: GITHUB_TOKEN not set!")
            return False

        server_path = "/mnt/c/Users/harsh/OneDrive/Desktop/oncall/github-mcp-server/github-mcp-server"
        if not os.path.exists(server_path):
            print(f"❌ Error: Server not found at {server_path}")
            return False

        print("🚀 Starting GitHub MCP server...")

        env = os.environ.copy()
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = github_token

        self.server_process = subprocess.Popen(
            [server_path, "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )

        # Wait for server to start
        await asyncio.sleep(2)

        if self.server_process.poll() is not None:
            stderr = self.server_process.stderr.read()
            print(f"❌ Server failed to start: {stderr}")
            return False

        print(f"✅ Server started with PID: {self.server_process.pid}")
        return True

    async def send_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Send a message to the server and get response."""
        if not self.server_process:
            return None

        try:
            # Send message
            message_str = json.dumps(message) + "\n"
            self.server_process.stdin.write(message_str)
            self.server_process.stdin.flush()

            # Read response
            response_line = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(self.server_process.stdout.readline)),
                timeout=10.0
            )

            if response_line:
                return json.loads(response_line.strip())
        except Exception as e:
            print(f"❌ Error: {e}")

        return None

    def get_message_id(self) -> int:
        """Get next message ID."""
        current = self.message_id
        self.message_id += 1
        return current

    async def run_demo(self):
        """Run the demo."""
        print("\n📡 Initializing MCP connection...")

        # Initialize
        init_msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "demo-client",
                    "version": "1.0.0"
                }
            }
        }

        response = await self.send_message(init_msg)
        if response and "result" in response:
            print("✅ MCP connection initialized!")
            print(f"   Server: {response['result'].get('serverInfo', {}).get('name', 'Unknown')}")
            print(f"   Version: {response['result'].get('serverInfo', {}).get('version', 'Unknown')}")

        # Get user info
        print("\n👤 Getting current user info...")
        user_msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "get_me",
                "arguments": {}
            }
        }

        response = await self.send_message(user_msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                user_info = json.loads(content[0].get("text", "{}"))
                print(f"   Username: {user_info.get('login', 'Unknown')}")
                print(f"   Name: {user_info.get('name', 'Unknown')}")
                print(f"   Company: {user_info.get('company', 'Unknown')}")
                print(f"   Public repos: {user_info.get('public_repos', 0)}")

        # List some tools
        print("\n🛠️  Listing available tools...")
        tools_msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/list",
            "params": {}
        }

        response = await self.send_message(tools_msg)
        if response and "result" in response:
            tools = response["result"].get("tools", [])
            print(f"   Found {len(tools)} tools available:")
            for tool in tools[:5]:  # Show first 5
                print(f"   - {tool.get('name', 'Unknown')}")

        # Search for popular Python repos
        print("\n🔍 Searching for popular Python repositories...")
        search_msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "search_repositories",
                "arguments": {
                    "query": "language:python stars:>10000",
                    "per_page": 3
                }
            }
        }

        response = await self.send_message(search_msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                repos = json.loads(content[0].get("text", "[]"))
                print(f"   Top {len(repos)} Python repositories:")
                for repo in repos:
                    print(f"   - {repo.get('full_name', 'Unknown')}")
                    print(f"     ⭐ {repo.get('stargazers_count', 0):,} stars")
                    print(f"     📝 {repo.get('description', 'No description')[:60]}...")

        # Get recent commits from a specific repo
        print("\n📝 Getting recent commits from github/docs...")
        commits_msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "list_commits",
                "arguments": {
                    "owner": "github",
                    "repo": "docs",
                    "per_page": 3
                }
            }
        }

        response = await self.send_message(commits_msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                commits = json.loads(content[0].get("text", "[]"))
                print("   Recent commits:")
                for commit in commits:
                    sha = commit.get("sha", "")[:7]
                    message = commit.get("commit", {}).get("message", "").split("\n")[0]
                    author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
                    print(f"   - {sha}: {message[:50]}...")
                    print(f"     Author: {author}")

    async def shutdown(self):
        """Shutdown the server."""
        if self.server_process:
            print("\n🛑 Shutting down server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
            print("✅ Server stopped.")


async def main():
    """Main function."""
    print("="*60)
    print("🚀 GitHub MCP Server Demo")
    print("="*60)

    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()

    demo = GitHubMCPDemo()

    try:
        # Start server
        if await demo.start_server():
            # Run demo
            await demo.run_demo()

            print("\n" + "="*60)
            print("✅ Demo completed successfully!")
            print("="*60)
            print("\nThe GitHub MCP server is fully functional and integrated")
            print("with your oncall agent. It will automatically start when")
            print("the agent runs and needs to fetch GitHub context.")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
    finally:
        await demo.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
