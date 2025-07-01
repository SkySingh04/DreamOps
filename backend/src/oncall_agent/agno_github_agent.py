"""Agno agent implementation with GitHub MCP Server integration."""

import asyncio
import os
from pathlib import Path

from agno.agent import Agent
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.mcp import MCPTools

from .config import get_config


class AgnoGitHubAgent:
    """Agno agent that uses GitHub MCP Server for repository operations."""

    def __init__(self):
        self.config = get_config()
        self.agent = None
        self.mcp_tools = None

    async def initialize(self):
        """Initialize the Agno agent with GitHub MCP Server."""
        # Get the GitHub MCP server path from config
        github_mcp_path = self.config.github_mcp_server_path

        if not github_mcp_path or not Path(github_mcp_path).exists():
            raise ValueError(f"GitHub MCP server not found at: {github_mcp_path}")

        # Command to run the GitHub MCP server
        # The server expects GITHUB_PERSONAL_ACCESS_TOKEN env var
        env = os.environ.copy()
        env['GITHUB_PERSONAL_ACCESS_TOKEN'] = self.config.github_token

        # Launch GitHub MCP server as subprocess
        command = f'"{github_mcp_path}" stdio'

        # Initialize MCP tools with the GitHub server
        self.mcp_tools = MCPTools(command, env=env)
        await self.mcp_tools.__aenter__()

        # Create the Agno agent with appropriate model
        model = None
        if self.config.anthropic_api_key:
            model = Claude(
                api_key=self.config.anthropic_api_key,
                id=self.config.claude_model
            )
        elif os.getenv('OPENAI_API_KEY'):
            model = OpenAIChat(id="gpt-4")
        else:
            raise ValueError("No AI model API key found (Anthropic or OpenAI)")

        self.agent = Agent(
            name="GitHub Operations Agent",
            role="An AI agent that helps with GitHub repository operations, "
                 "issue management, code search, and pull request handling.",
            model=model,
            tools=[self.mcp_tools],
            instructions='''
You are a GitHub operations assistant with access to GitHub MCP tools.
When users ask you to:

1. **Search code**: Use the 'search_code' tool with query and optional repo parameters
2. **Fetch commits**: Use 'fetch_recent_commits' with repo and limit parameters
3. **View issues**: Use 'fetch_open_issues' with repo parameter
4. **Check CI/CD status**: Use 'fetch_github_actions_status' with repo parameter
5. **List pull requests**: Use 'fetch_pull_requests' with repo parameter
6. **Create issues**: Use 'create_issue' with repo, title, and body
7. **Add comments**: Use 'add_comment' with repo, issue_number, and comment
8. **Get file contents**: Use 'get_file_contents' with repo and path

Always be specific about which repository the user wants to work with.
Format responses clearly with code blocks when showing file contents or code snippets.
'''
        )

        return self

    async def run(self, query: str) -> str:
        """Run a query through the agent."""
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")

        return await self.agent.run(query)

    async def cleanup(self):
        """Clean up resources."""
        if self.mcp_tools:
            await self.mcp_tools.__aexit__(None, None, None)


async def create_github_agno_agent():
    """Factory function to create and initialize a GitHub Agno agent."""
    agent = AgnoGitHubAgent()
    await agent.initialize()
    return agent


# Example usage
async def main():
    """Example of using the GitHub Agno agent."""
    try:
        # Create and initialize the agent
        agent = await create_github_agno_agent()

        # Example queries
        queries = [
            "Search for kubernetes in the kubernetes/kubernetes repo",
            "Show me the recent commits in kubernetes/kubernetes repo",
            "Get the contents of README.md from kubernetes/kubernetes",
            "List open issues in kubernetes/kubernetes"
        ]

        for query in queries[:1]:  # Test with first query
            print(f"\n🔍 Query: {query}")
            print("-" * 60)

            try:
                answer = await agent.run(query)
                print(f"📝 Answer:\n{answer}")
            except Exception as e:
                print(f"❌ Error: {e}")

            print("-" * 60)

        # Cleanup
        await agent.cleanup()

    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
