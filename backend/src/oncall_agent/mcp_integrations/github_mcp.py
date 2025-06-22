"""GitHub MCP integration for the oncall agent."""

import asyncio
import json
import os
import subprocess
from datetime import datetime
from typing import Any

from .base import MCPIntegration


class GitHubMCPIntegration(MCPIntegration):
    """GitHub MCP integration that automatically manages the GitHub MCP server."""

    def __init__(self, config: dict[str, Any]):
        """Initialize the GitHub MCP integration.
        
        Args:
            config: Configuration dictionary with:
                - github_token: GitHub personal access token
                - mcp_server_path: Path to GitHub MCP server binary
                - server_host: Host for MCP server (default: localhost)
                - server_port: Port for MCP server (default: 8081)
        """
        super().__init__("github", config)
        self.github_token = config.get("github_token")
        # Use the path relative to the oncall-agent backend directory
        self.mcp_server_path = config.get("mcp_server_path", "../../github-mcp-server/github-mcp-server")
        self.server_host = config.get("server_host", "localhost")
        self.server_port = config.get("server_port", 8081)
        self.server_process = None
        self.connected = False

        # Service to repository mapping
        self.service_repo_mapping = {
            "api-gateway": "myorg/api-gateway",
            "user-service": "myorg/user-service",
            "payment-service": "myorg/payment-service",
            "notification-service": "myorg/notification-service",
            "auth-service": "myorg/auth-service",
            "order-service": "myorg/order-service",
            "inventory-service": "myorg/inventory-service"
        }

    async def connect(self) -> None:
        """Connect to the GitHub MCP server by starting it as a subprocess."""
        print("🚀 GITHUB MCP: Initializing GitHub MCP integration...")
        self.logger.info("🚀 Initializing GitHub MCP integration...")

        if self.connected:
            print("✅ GITHUB MCP: GitHub MCP integration already connected")
            self.logger.info("✅ GitHub MCP integration already connected")
            return

        try:
            # Validate configuration
            self.logger.info("🔍 Validating GitHub MCP configuration...")
            if not self.github_token:
                self.logger.error("❌ GitHub token not configured. Set GITHUB_TOKEN in .env")
                raise ValueError("GitHub token not configured. Set GITHUB_TOKEN in .env")

            self.logger.info(f"✅ GitHub token configured (length: {len(self.github_token)})")

            # Convert relative path to absolute path
            if not os.path.isabs(self.mcp_server_path):
                # Get the directory of this file
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # Navigate to the mcp_server_path from current directory
                self.mcp_server_path = os.path.abspath(os.path.join(current_dir, self.mcp_server_path))

            # Check if server binary exists
            self.logger.info(f"🔍 Checking for GitHub MCP server at: {self.mcp_server_path}")
            if not os.path.exists(self.mcp_server_path):
                self.logger.error(f"❌ GitHub MCP server not found at {self.mcp_server_path}")
                raise FileNotFoundError(f"GitHub MCP server not found at {self.mcp_server_path}")

            self.logger.info("✅ GitHub MCP server binary found")

            # Start the GitHub MCP server subprocess
            self.logger.info("🚀 Starting GitHub MCP server subprocess...")

            # Set up environment with GitHub token
            env = os.environ.copy()
            env["GITHUB_PERSONAL_ACCESS_TOKEN"] = self.github_token

            # Start the server process
            self.logger.info("📡 Launching GitHub MCP server process...")
            self.server_process = subprocess.Popen(
                [self.mcp_server_path, "stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            self.logger.info(f"🔄 GitHub MCP server process launched with PID: {self.server_process.pid}")

            # Wait for server to start
            self.logger.info("⏳ Waiting for GitHub MCP server to initialize (2 seconds)...")
            await asyncio.sleep(2)

            # Check if process is still running
            if self.server_process.poll() is not None:
                stdout, stderr = self.server_process.communicate()
                self.logger.error(f"❌ GitHub MCP server failed to start. Exit code: {self.server_process.returncode}")
                self.logger.error(f"❌ STDERR: {stderr}")
                raise RuntimeError(f"GitHub MCP server failed to start. Exit code: {self.server_process.returncode}\nSTDERR: {stderr}")

            print(f"✅ GITHUB MCP: GitHub MCP server is running with PID {self.server_process.pid}")
            self.logger.info(f"✅ GitHub MCP server is running with PID {self.server_process.pid}")

            # Initialize MCP connection
            print("🤝 GITHUB MCP: Initializing MCP protocol connection...")
            self.logger.info("🤝 Initializing MCP protocol connection...")
            await self._initialize_mcp_connection()

            print("🎉 GITHUB MCP: GitHub MCP integration connected successfully!")
            self.logger.info("🎉 GitHub MCP integration connected successfully!")
            self.connected = True
            self.connection_time = datetime.now()

        except Exception as e:
            self.logger.error(f"❌ Failed to connect to GitHub MCP: {e}")
            await self.disconnect()
            raise

    async def _initialize_mcp_connection(self) -> None:
        """Initialize the MCP protocol connection."""
        try:
            self.logger.info("📨 Sending MCP initialization message...")
            # Send MCP initialization message
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "oncall-agent",
                        "version": "1.0.0"
                    }
                }
            }

            await self._send_mcp_message(init_message)
            self.logger.info("✅ MCP initialization message sent")

            # Wait for initialization response
            self.logger.info("⏳ Waiting for MCP initialization response...")
            response = await self._read_mcp_response()
            if response and "result" in response:
                self.logger.info("✅ MCP connection initialized successfully")
                server_info = response['result'].get('serverInfo', {})
                server_name = server_info.get('name', 'Unknown')
                server_version = server_info.get('version', 'Unknown')
                self.logger.info(f"🔗 Connected to GitHub MCP server: {server_name} v{server_version}")
                self.logger.debug(f"Server capabilities: {response['result'].get('capabilities', {})}")
            else:
                self.logger.error("❌ No valid response received from MCP server")
                raise RuntimeError("Failed to initialize MCP connection")

        except Exception as e:
            self.logger.error(f"❌ MCP initialization failed: {e}")
            raise

    async def _send_mcp_message(self, message: dict[str, Any]) -> None:
        """Send a message to the MCP server."""
        if not self.server_process or self.server_process.poll() is not None:
            raise RuntimeError("GitHub MCP server is not running")

        try:
            message_str = json.dumps(message) + "\n"
            self.server_process.stdin.write(message_str)
            self.server_process.stdin.flush()
            self.logger.debug(f"Sent MCP message: {message}")
        except Exception as e:
            self.logger.error(f"Failed to send MCP message: {e}")
            raise

    async def _read_mcp_response(self, timeout: float = 5.0) -> dict[str, Any] | None:
        """Read a response from the MCP server."""
        if not self.server_process:
            return None

        try:
            # Use asyncio to read with timeout
            line = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(self.server_process.stdout.readline)),
                timeout=timeout
            )

            if line:
                response = json.loads(line.strip())
                self.logger.debug(f"Received MCP response: {response}")
                return response
            return None
        except TimeoutError:
            self.logger.warning("Timeout reading MCP response")
            return None
        except Exception as e:
            self.logger.error(f"Error reading MCP response: {e}")
            return None

    async def disconnect(self) -> None:
        """Disconnect from the GitHub MCP server."""
        if self.server_process:
            try:
                self.logger.info("🛑 Shutting down GitHub MCP server...")
                # Terminate the process gracefully
                self.server_process.terminate()
                self.logger.info("📡 Sent termination signal to GitHub MCP server")

                # Wait for process to terminate
                try:
                    self.server_process.wait(timeout=5)
                    self.logger.info("✅ GitHub MCP server terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    self.logger.warning("⚠️  GitHub MCP server didn't terminate gracefully, force killing...")
                    self.server_process.kill()
                    self.server_process.wait()
                    self.logger.info("🔪 GitHub MCP server force killed")

                self.logger.info("✅ GitHub MCP server stopped successfully")
            except Exception as e:
                self.logger.error(f"❌ Error stopping GitHub MCP server: {e}")
            finally:
                self.server_process = None
                self.connected = False
                self.logger.info("🔌 GitHub MCP integration disconnected")

    async def fetch_context(self, context_type: str, **params) -> dict[str, Any]:
        """Fetch context from GitHub based on the alert.
        
        Args:
            context_type: Type of context to fetch
            **params: Additional parameters for the context
            
        Returns:
            Dictionary containing the requested context
        """
        if not self.connected:
            raise RuntimeError("GitHub MCP integration not connected")

        try:
            if context_type == "recent_commits":
                return await self._fetch_recent_commits(params.get("repository"), params.get("since_hours", 24))
            elif context_type == "open_issues":
                return await self._fetch_open_issues(params.get("repository"), params.get("labels", []))
            elif context_type == "github_actions_status":
                return await self._fetch_actions_status(params.get("repository"))
            elif context_type == "pull_requests":
                return await self._fetch_pull_requests(params.get("repository"), params.get("state", "open"))
            else:
                return {"error": f"Unknown context type: {context_type}"}

        except Exception as e:
            self.logger.error(f"Error fetching GitHub context: {e}")
            return {"error": str(e)}

    async def _fetch_recent_commits(self, repository: str, since_hours: int) -> dict[str, Any]:
        """Fetch recent commits from a repository."""
        message_id = self._generate_message_id()

        # Send tool call message
        tool_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {
                "name": "list_commits",
                "arguments": {
                    "owner": repository.split("/")[0],
                    "repo": repository.split("/")[1],
                    "per_page": 20
                }
            }
        }

        await self._send_mcp_message(tool_message)
        response = await self._read_mcp_response(timeout=10)

        if response and "result" in response:
            commits = response["result"].get("content", [])
            return {
                "repository": repository,
                "commit_count": len(commits),
                "commits": commits,
                "since_hours": since_hours
            }
        else:
            return {"error": "Failed to fetch commits", "repository": repository}

    async def _fetch_open_issues(self, repository: str, labels: list[str]) -> dict[str, Any]:
        """Fetch open issues from a repository."""
        message_id = self._generate_message_id()

        # Send tool call message
        tool_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {
                "name": "list_issues",
                "arguments": {
                    "owner": repository.split("/")[0],
                    "repo": repository.split("/")[1],
                    "state": "open",
                    "labels": ",".join(labels) if labels else None,
                    "per_page": 10
                }
            }
        }

        await self._send_mcp_message(tool_message)
        response = await self._read_mcp_response(timeout=10)

        if response and "result" in response:
            issues = response["result"].get("content", [])
            return {
                "repository": repository,
                "issue_count": len(issues),
                "issues": issues,
                "labels": labels
            }
        else:
            return {"error": "Failed to fetch issues", "repository": repository}

    async def _fetch_actions_status(self, repository: str) -> dict[str, Any]:
        """Fetch GitHub Actions status for a repository."""
        # For now, return a placeholder
        # The actual implementation would use the GitHub MCP server's workflow tools
        return {
            "repository": repository,
            "actions_status": "placeholder",
            "message": "GitHub Actions status check would be implemented here"
        }

    async def _fetch_pull_requests(self, repository: str, state: str) -> dict[str, Any]:
        """Fetch pull requests from a repository."""
        message_id = self._generate_message_id()

        # Send tool call message
        tool_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {
                "name": "list_pull_requests",
                "arguments": {
                    "owner": repository.split("/")[0],
                    "repo": repository.split("/")[1],
                    "state": state,
                    "per_page": 10
                }
            }
        }

        await self._send_mcp_message(tool_message)
        response = await self._read_mcp_response(timeout=10)

        if response and "result" in response:
            prs = response["result"].get("content", [])
            return {
                "repository": repository,
                "pr_count": len(prs),
                "pull_requests": prs,
                "state": state
            }
        else:
            return {"error": "Failed to fetch pull requests", "repository": repository}

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an action via the GitHub MCP server.
        
        Args:
            action: Action to execute (e.g., 'create_issue', 'add_comment')
            params: Parameters for the action
            
        Returns:
            Result of the action
        """
        if not self.connected:
            raise RuntimeError("GitHub MCP integration not connected")

        try:
            if action == "create_issue":
                return await self._create_issue(params)
            elif action == "add_comment":
                return await self._add_comment(params)
            else:
                return {"error": f"Unknown action: {action}"}

        except Exception as e:
            self.logger.error(f"Error executing GitHub action: {e}")
            return {"error": str(e)}

    async def _create_issue(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a GitHub issue."""
        message_id = self._generate_message_id()

        repository = params.get("repository", "")
        if "/" not in repository:
            return {"error": "Invalid repository format. Use owner/repo"}

        # Send tool call message
        tool_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {
                "name": "create_issue",
                "arguments": {
                    "owner": repository.split("/")[0],
                    "repo": repository.split("/")[1],
                    "title": params.get("title", "Incident Report"),
                    "body": params.get("body", ""),
                    "labels": params.get("labels", ["incident", "auto-generated"])
                }
            }
        }

        await self._send_mcp_message(tool_message)
        response = await self._read_mcp_response(timeout=10)

        if response and "result" in response:
            return {
                "success": True,
                "issue": response["result"].get("content", {}),
                "repository": repository
            }
        else:
            return {"error": "Failed to create issue", "repository": repository}

    async def _add_comment(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add a comment to an issue or PR."""
        message_id = self._generate_message_id()

        repository = params.get("repository", "")
        if "/" not in repository:
            return {"error": "Invalid repository format. Use owner/repo"}

        # Send tool call message
        tool_message = {
            "jsonrpc": "2.0",
            "id": message_id,
            "method": "tools/call",
            "params": {
                "name": "add_issue_comment",
                "arguments": {
                    "owner": repository.split("/")[0],
                    "repo": repository.split("/")[1],
                    "issue_number": params.get("issue_number"),
                    "body": params.get("body", "")
                }
            }
        }

        await self._send_mcp_message(tool_message)
        response = await self._read_mcp_response(timeout=10)

        if response and "result" in response:
            return {
                "success": True,
                "comment": response["result"].get("content", {}),
                "repository": repository
            }
        else:
            return {"error": "Failed to add comment", "repository": repository}

    async def get_capabilities(self) -> dict[str, list[str]]:
        """Get the list of capabilities provided by this integration."""
        capabilities = {
            "actions": [
                "fetch_recent_commits",
                "fetch_open_issues",
                "fetch_github_actions_status",
                "fetch_pull_requests",
                "create_issue",
                "add_comment",
                "search_code",
                "get_file_contents"
            ]
        }
        self.logger.debug(f"🛠️  GitHub MCP capabilities requested: {len(capabilities['actions'])} actions available")
        return capabilities

    async def health_check(self) -> bool:
        """Check if the GitHub MCP integration is healthy."""
        if not self.connected or not self.server_process:
            return False

        # Check if process is still running
        if self.server_process.poll() is not None:
            self.connected = False
            return False

        # Try a simple MCP ping
        try:
            message_id = self._generate_message_id()
            ping_message = {
                "jsonrpc": "2.0",
                "id": message_id,
                "method": "ping",
                "params": {}
            }

            await self._send_mcp_message(ping_message)
            response = await self._read_mcp_response(timeout=2)

            return response is not None
        except Exception:
            return False

    def _generate_message_id(self) -> int:
        """Generate a unique message ID for MCP communication."""
        # Simple incrementing ID (in production, use UUID or better strategy)
        if not hasattr(self, '_message_counter'):
            self._message_counter = 1
        else:
            self._message_counter += 1
        return self._message_counter

    def get_repository_for_service(self, service_name: str) -> str | None:
        """Get the GitHub repository for a given service name."""
        return self.service_repo_mapping.get(service_name)
