#!/usr/bin/env python3
"""Interactive GitHub MCP server client for testing."""

import asyncio
import json
import os
import subprocess
from typing import Any


class GitHubMCPClient:
    """Interactive client for GitHub MCP server."""

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

        # Initialize MCP connection
        await self.initialize()
        return True

    async def initialize(self):
        """Initialize MCP connection."""
        print("📡 Initializing MCP connection...")

        init_msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "interactive-client",
                    "version": "1.0.0"
                }
            }
        }

        response = await self.send_message(init_msg)
        if response and "result" in response:
            print("✅ MCP connection initialized!")
            print(f"Server info: {response['result'].get('serverInfo', {})}")
        else:
            print("❌ Failed to initialize MCP connection")

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

    async def list_tools(self):
        """List available tools."""
        print("\n📋 Listing available tools...")

        msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/list",
            "params": {}
        }

        response = await self.send_message(msg)
        if response and "result" in response:
            tools = response["result"].get("tools", [])
            print(f"\nFound {len(tools)} tools:")
            for tool in tools[:10]:  # Show first 10
                print(f"  - {tool.get('name', 'Unknown')}: {tool.get('description', '')[:60]}...")

    async def get_user_info(self):
        """Get current user information."""
        print("\n👤 Getting user info...")

        msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "get_me",
                "arguments": {}
            }
        }

        response = await self.send_message(msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                user_info = json.loads(content[0].get("text", "{}"))
                print(f"  Username: {user_info.get('login', 'Unknown')}")
                print(f"  Name: {user_info.get('name', 'Unknown')}")
                print(f"  Company: {user_info.get('company', 'Unknown')}")
                print(f"  Public repos: {user_info.get('public_repos', 0)}")

    async def list_repos(self, owner: str):
        """List repositories for an owner."""
        print(f"\n📦 Listing repos for {owner}...")

        msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "search_repositories",
                "arguments": {
                    "query": f"user:{owner}",
                    "per_page": 5
                }
            }
        }

        response = await self.send_message(msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                repos = json.loads(content[0].get("text", "[]"))
                print(f"\nFound {len(repos)} repositories:")
                for repo in repos:
                    print(f"  - {repo.get('full_name', 'Unknown')}")
                    print(f"    ⭐ {repo.get('stargazers_count', 0)} stars")
                    print(f"    📝 {repo.get('description', 'No description')[:60]}...")

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

    async def interactive_menu(self):
        """Show interactive menu."""
        while True:
            print("\n" + "="*50)
            print("GitHub MCP Server - Interactive Menu")
            print("="*50)
            print("1. List available tools")
            print("2. Get current user info")
            print("3. List repositories for a user")
            print("4. Search for repositories")
            print("5. List recent commits")
            print("6. Create an issue (test)")
            print("0. Exit")
            print("-"*50)

            choice = input("Select an option: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                await self.list_tools()
            elif choice == "2":
                await self.get_user_info()
            elif choice == "3":
                owner = input("Enter GitHub username/org: ").strip()
                if owner:
                    await self.list_repos(owner)
            elif choice == "4":
                query = input("Enter search query: ").strip()
                if query:
                    await self.search_repos(query)
            elif choice == "5":
                repo = input("Enter repository (owner/repo): ").strip()
                if repo and "/" in repo:
                    await self.list_commits(repo)
            elif choice == "6":
                print("⚠️  Issue creation is a test feature")
                repo = input("Enter repository (owner/repo): ").strip()
                if repo and "/" in repo:
                    await self.create_test_issue(repo)

            input("\nPress Enter to continue...")

    async def search_repos(self, query: str):
        """Search for repositories."""
        print(f"\n🔍 Searching for: {query}")

        msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "search_repositories",
                "arguments": {
                    "query": query,
                    "per_page": 5
                }
            }
        }

        response = await self.send_message(msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                repos = json.loads(content[0].get("text", "[]"))
                print(f"\nFound {len(repos)} repositories:")
                for repo in repos:
                    print(f"  - {repo.get('full_name', 'Unknown')}")
                    print(f"    ⭐ {repo.get('stargazers_count', 0)} | 🍴 {repo.get('forks_count', 0)}")

    async def list_commits(self, repo: str):
        """List recent commits."""
        print(f"\n📝 Recent commits for {repo}")

        owner, name = repo.split("/")
        msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "list_commits",
                "arguments": {
                    "owner": owner,
                    "repo": name,
                    "per_page": 5
                }
            }
        }

        response = await self.send_message(msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                commits = json.loads(content[0].get("text", "[]"))
                print(f"\nShowing {len(commits)} recent commits:")
                for commit in commits:
                    sha = commit.get("sha", "")[:7]
                    message = commit.get("commit", {}).get("message", "").split("\n")[0]
                    author = commit.get("commit", {}).get("author", {}).get("name", "Unknown")
                    print(f"  - {sha}: {message[:50]}... (by {author})")

    async def create_test_issue(self, repo: str):
        """Create a test issue."""
        print(f"\n📝 Creating test issue in {repo}")

        owner, name = repo.split("/")
        title = input("Issue title: ").strip() or "Test Issue from MCP"
        body = input("Issue body: ").strip() or "This is a test issue created via GitHub MCP server"

        msg = {
            "jsonrpc": "2.0",
            "id": self.get_message_id(),
            "method": "tools/call",
            "params": {
                "name": "create_issue",
                "arguments": {
                    "owner": owner,
                    "repo": name,
                    "title": title,
                    "body": body,
                    "labels": ["test", "mcp-generated"]
                }
            }
        }

        response = await self.send_message(msg)
        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and isinstance(content[0], dict):
                issue = json.loads(content[0].get("text", "{}"))
                print("\n✅ Issue created successfully!")
                print(f"   URL: {issue.get('html_url', 'Unknown')}")
                print(f"   Number: #{issue.get('number', 'Unknown')}")


async def main():
    """Main function."""
    print("🚀 GitHub MCP Interactive Client")
    print("="*50)

    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()

    client = GitHubMCPClient()

    try:
        # Start server
        if await client.start_server():
            # Run interactive menu
            await client.interactive_menu()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        await client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
