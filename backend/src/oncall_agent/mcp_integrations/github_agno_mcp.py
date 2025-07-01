"""GitHub MCP integration using Agno framework."""

import os
from typing import Any

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools

from ..config import get_config
from ..utils import get_logger
from .base import MCPIntegration


class GitHubAgnoMCPIntegration(MCPIntegration):
    """GitHub integration using Agno MCP framework."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize GitHub Agno MCP integration."""
        super().__init__(config)
        self.logger = get_logger(__name__)
        self.global_config = get_config()

        # Override with global config if not provided
        if not self.config.get('github_token'):
            self.config['github_token'] = self.global_config.github_token
        if not self.config.get('mcp_server_path'):
            self.config['mcp_server_path'] = self.global_config.github_mcp_server_path
        if not self.config.get('server_port'):
            self.config['server_port'] = self.global_config.github_mcp_port

        self.mcp_tools = None
        self.agent = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to GitHub MCP server using Agno."""
        try:
            self.logger.info("🚀 GITHUB AGNO: Initializing GitHub MCP with Agno...")

            # Prepare environment with GitHub token
            env = os.environ.copy()
            # GitHub MCP server expects GITHUB_PERSONAL_ACCESS_TOKEN
            env['GITHUB_PERSONAL_ACCESS_TOKEN'] = self.config['github_token']

            # Command to run GitHub MCP server
            # MCPTools expects the command as a string
            server_path = self.config['mcp_server_path']
            # GitHub MCP server uses stdio transport
            # Quote the path to handle spaces
            command = f'"{server_path}" stdio'

            self.logger.info(f"📡 GITHUB AGNO: Starting MCP server: {command}")

            # Initialize MCP tools
            self.mcp_tools = MCPTools(command, env=env)
            await self.mcp_tools.__aenter__()

            # Create Agno agent with Claude or GPT-4
            model = None
            if self.global_config.anthropic_api_key:
                model = Claude(
                    api_key=self.global_config.anthropic_api_key,
                    id=self.global_config.claude_model
                )
            elif os.getenv('OPENAI_API_KEY'):
                model = OpenAIChat(id="gpt-4")
            else:
                raise ValueError("No AI model API key found (Anthropic or OpenAI)")

            self.agent = Agent(
                name="GitHub Operations Agent",
                role="AI assistant for GitHub repository operations and incident response",
                model=model,
                tools=[self.mcp_tools],
                instructions='''
You are a GitHub operations assistant helping with incident response.
Available tools:
- search_code: Search for code patterns across repositories
- fetch_recent_commits: Get recent commits to understand changes
- fetch_open_issues: View open issues that might be related
- fetch_github_actions_status: Check CI/CD pipeline status
- fetch_pull_requests: List pull requests
- create_issue: Create new issues for tracking incidents
- add_comment: Add comments to existing issues
- get_file_contents: Read specific files

When investigating incidents:
1. Search for relevant code changes or patterns
2. Check recent commits that might have caused issues
3. Look for related open issues
4. Verify CI/CD status
5. Create or update issues to track the incident
'''
            )

            self._connected = True
            self.logger.info("✅ GITHUB AGNO: Successfully connected to GitHub MCP via Agno!")
            return True

        except Exception as e:
            self.logger.error(f"❌ GITHUB AGNO: Failed to connect: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from GitHub MCP server."""
        try:
            if self.mcp_tools:
                await self.mcp_tools.__aexit__(None, None, None)
                self.logger.info("✅ GITHUB AGNO: Disconnected from GitHub MCP")
        except Exception as e:
            self.logger.error(f"❌ GITHUB AGNO: Error during disconnect: {e}")
        finally:
            self._connected = False
            self.mcp_tools = None
            self.agent = None

    async def health_check(self) -> bool:
        """Check if the integration is healthy."""
        return self._connected and self.agent is not None

    async def fetch_context(self, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch context using natural language queries via Agno agent."""
        if not self._connected or not self.agent:
            return {"error": "Not connected to GitHub MCP"}

        try:
            # Extract the query from params
            query = params.get('query', '')
            repo = params.get('repo', '')

            # Build a natural language query for the agent
            if repo:
                full_query = f"In the {repo} repository, {query}"
            else:
                full_query = query

            self.logger.info(f"🔍 GITHUB AGNO: Processing query: {full_query}")

            # Run the query through Agno agent
            result = await self.agent.run(full_query)

            return {
                "success": True,
                "query": full_query,
                "result": result
            }

        except Exception as e:
            self.logger.error(f"❌ GITHUB AGNO: Error fetching context: {e}")
            return {"error": str(e)}

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute GitHub actions via Agno agent."""
        if not self._connected or not self.agent:
            return {"error": "Not connected to GitHub MCP"}

        try:
            # Map actions to natural language queries
            action_queries = {
                'search_code': f"Search for code: {params.get('query', '')} in {params.get('repo', 'all repositories')}",
                'fetch_recent_commits': f"Show the last {params.get('limit', 10)} commits in {params.get('repo', '')}",
                'fetch_open_issues': f"List open issues in {params.get('repo', '')}",
                'fetch_github_actions_status': f"Check GitHub Actions status for {params.get('repo', '')}",
                'fetch_pull_requests': f"List pull requests in {params.get('repo', '')}",
                'create_issue': f"Create a new issue in {params.get('repo', '')} with title '{params.get('title', '')}' and body '{params.get('body', '')}'",
                'add_comment': f"Add comment to issue #{params.get('issue_number', '')} in {params.get('repo', '')}: {params.get('comment', '')}",
                'get_file_contents': f"Get contents of {params.get('path', '')} from {params.get('repo', '')}"
            }

            query = action_queries.get(action)
            if not query:
                # Fallback: try to interpret the action directly
                query = f"{action} with parameters: {params}"

            self.logger.info(f"🎯 GITHUB AGNO: Executing action '{action}' via query: {query}")

            # Execute via Agno agent
            result = await self.agent.run(query)

            return {
                "success": True,
                "action": action,
                "result": result
            }

        except Exception as e:
            self.logger.error(f"❌ GITHUB AGNO: Error executing action '{action}': {e}")
            return {"error": str(e)}

    def get_capabilities(self) -> list[str]:
        """Return list of capabilities."""
        return [
            'search_code',
            'fetch_recent_commits',
            'fetch_open_issues',
            'fetch_github_actions_status',
            'fetch_pull_requests',
            'create_issue',
            'add_comment',
            'get_file_contents'
        ]

    async def get_capabilities(self) -> dict[str, Any]:
        """Get available capabilities from the GitHub MCP server."""
        return {
            "actions": self.get_capabilities(),
            "description": "GitHub operations via Agno MCP integration",
            "features": [
                "Natural language queries",
                "Code search across repositories",
                "Issue and PR management",
                "CI/CD status monitoring",
                "File content retrieval"
            ]
        }
