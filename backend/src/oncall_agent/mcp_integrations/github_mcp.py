"""GitHub MCP integration for the oncall agent."""

import json
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import MCPIntegration


class GitHubMCPIntegration(MCPIntegration):
    """GitHub MCP integration using the local GitHub MCP server.
    
    This integration connects to the GitHub MCP server running locally
    to provide GitHub API access for incident management and analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the GitHub MCP integration.
        
        Args:
            config: Configuration dictionary containing:
                - github_token: GitHub personal access token
                - mcp_server_path: Path to the GitHub MCP server binary
                - server_host: Host for the MCP server (default: localhost)
                - server_port: Port for the MCP server (default: 8080)
        """
        super().__init__("github", config)
        
        # Configuration with defaults
        self.github_token = self.config.get("github_token", "")
        self.mcp_server_path = self.config.get(
            "mcp_server_path", 
            "/mnt/c/Users/harsh/OneDrive/Desktop/oncall/github-mcp-server/github-mcp-server"
        )
        self.server_host = self.config.get("server_host", "localhost")
        self.server_port = self.config.get("server_port", 8080)
        
        # Runtime state
        self.server_process: Optional[subprocess.Popen] = None
        self.mcp_client = None
        
    async def connect(self) -> None:
        """Connect to the GitHub MCP server."""
        try:
            # Start the GitHub MCP server if not already running
            if not self.server_process:
                await self._start_mcp_server()
            
            # Initialize MCP client connection
            await self._initialize_mcp_client()
            
            # Test the connection
            await self._test_connection()
            
            self.connected = True
            self.connection_time = datetime.now()
            self.logger.info("Successfully connected to GitHub MCP server")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to GitHub MCP server: {e}")
            raise ConnectionError(f"GitHub MCP connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from the GitHub MCP server."""
        try:
            # Close MCP client connection
            if self.mcp_client:
                await self.mcp_client.close()
                self.mcp_client = None
            
            # Stop the MCP server process
            if self.server_process:
                self.server_process.terminate()
                await asyncio.sleep(1)
                if self.server_process.poll() is None:
                    self.server_process.kill()
                self.server_process = None
            
            self.connected = False
            self.connection_time = None
            self.logger.info("Disconnected from GitHub MCP server")
            
        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")
    
    async def fetch_context(self, context_type: str, **kwargs) -> Dict[str, Any]:
        """Fetch context information from GitHub.
        
        Args:
            context_type: Type of context to fetch:
                - "repository_info": Get repository information
                - "recent_commits": Get recent commits
                - "open_issues": Get open issues
                - "pull_requests": Get pull requests
                - "actions_status": Get GitHub Actions status
                - "releases": Get recent releases
                - "file_contents": Get file or directory contents
                - "search_code": Search code across repositories
            **kwargs: Additional parameters for the context request
        
        Returns:
            Dictionary containing the requested GitHub context
        """
        self.validate_connection()
        
        try:
            if context_type == "repository_info":
                return await self._get_repository_info(**kwargs)
            elif context_type == "recent_commits":
                return await self._get_recent_commits(**kwargs)
            elif context_type == "open_issues":
                return await self._get_open_issues(**kwargs)
            elif context_type == "pull_requests":
                return await self._get_pull_requests(**kwargs)
            elif context_type == "actions_status":
                return await self._get_actions_status(**kwargs)
            elif context_type == "releases":
                return await self._get_releases(**kwargs)
            elif context_type == "file_contents":
                return await self._get_file_contents(**kwargs)
            elif context_type == "search_code":
                return await self._search_code(**kwargs)
            else:
                raise ValueError(f"Unsupported context type: {context_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to fetch context {context_type}: {e}")
            return {"error": str(e), "context_type": context_type}
    
    async def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action through GitHub.
        
        Args:
            action: The action to perform:
                - "create_issue": Create a new issue
                - "add_comment": Add comment to issue/PR
                - "update_issue": Update issue status/labels
                - "create_pr": Create pull request
                - "merge_pr": Merge pull request
                - "trigger_workflow": Trigger GitHub Actions workflow
            params: Parameters required for the action
        
        Returns:
            Dictionary containing the result of the action
        """
        self.validate_connection()
        
        try:
            if action == "create_issue":
                return await self._create_issue(params)
            elif action == "add_comment":
                return await self._add_comment(params)
            elif action == "update_issue":
                return await self._update_issue(params)
            elif action == "create_pr":
                return await self._create_pull_request(params)
            elif action == "merge_pr":
                return await self._merge_pull_request(params)
            elif action == "trigger_workflow":
                return await self._trigger_workflow(params)
            else:
                raise ValueError(f"Unsupported action: {action}")
                
        except Exception as e:
            self.logger.error(f"Failed to execute action {action}: {e}")
            return {"error": str(e), "action": action}
    
    async def get_capabilities(self) -> Dict[str, List[str]]:
        """Get the capabilities of the GitHub MCP integration."""
        return {
            "context_types": [
                "repository_info",
                "recent_commits", 
                "open_issues",
                "pull_requests",
                "actions_status",
                "releases",
                "file_contents",
                "search_code"
            ],
            "actions": [
                "create_issue",
                "add_comment",
                "update_issue",
                "create_pr",
                "merge_pr",
                "trigger_workflow"
            ],
            "features": [
                "incident_tracking",
                "automated_reporting", 
                "workflow_automation",
                "repository_monitoring",
                "code_analysis",
                "file_content_access",
                "code_search",
                "error_pattern_detection"
            ]
        }
    
    async def _start_mcp_server(self) -> None:
        """Start the GitHub MCP server process."""
        try:
            # Build the command to start the MCP server
            cmd = [
                self.mcp_server_path,
                "--host", self.server_host,
                "--port", str(self.server_port)
            ]
            
            # Set environment variables
            env = {
                "GITHUB_TOKEN": self.github_token,
                "PATH": "/usr/local/bin:/usr/bin:/bin"
            }
            
            # Start the server process
            self.server_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for the server to start
            await asyncio.sleep(2)
            
            # Check if the process is still running
            if self.server_process.poll() is not None:
                stdout, stderr = self.server_process.communicate()
                raise RuntimeError(f"MCP server failed to start: {stderr}")
            
            self.logger.info(f"GitHub MCP server started on {self.server_host}:{self.server_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def _initialize_mcp_client(self) -> None:
        """Initialize the MCP client connection."""
        try:
            # For now, we'll use a simple HTTP client approach
            # In a production environment, you'd use a proper MCP client library
            import aiohttp
            
            self.mcp_client = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "Authorization": f"Bearer {self.github_token}",
                    "Content-Type": "application/json"
                }
            )
            
            self.logger.info("MCP client initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP client: {e}")
            raise
    
    async def _test_connection(self) -> None:
        """Test the connection to the MCP server."""
        try:
            # Make a simple request to test connectivity
            async with self.mcp_client.get(f"http://{self.server_host}:{self.server_port}/health") as response:
                if response.status != 200:
                    raise ConnectionError(f"Health check failed: {response.status}")
            
            self.logger.info("MCP server health check passed")
            
        except Exception as e:
            self.logger.error(f"MCP server health check failed: {e}")
            raise
    
    async def _get_repository_info(self, **kwargs) -> Dict[str, Any]:
        """Get repository information."""
        repo = kwargs.get("repository", "")
        if not repo:
            raise ValueError("Repository parameter is required")
        
        # Make MCP call to get repository info
        return await self._make_mcp_request("get_repository", {"repository": repo})
    
    async def _get_recent_commits(self, **kwargs) -> Dict[str, Any]:
        """Get recent commits."""
        repo = kwargs.get("repository", "")
        limit = kwargs.get("limit", 10)
        
        if not repo:
            raise ValueError("Repository parameter is required")
        
        return await self._make_mcp_request("list_commits", {
            "repository": repo,
            "limit": limit
        })
    
    async def _get_open_issues(self, **kwargs) -> Dict[str, Any]:
        """Get open issues."""
        repo = kwargs.get("repository", "")
        limit = kwargs.get("limit", 20)
        
        if not repo:
            raise ValueError("Repository parameter is required")
        
        return await self._make_mcp_request("list_issues", {
            "repository": repo,
            "state": "open",
            "limit": limit
        })
    
    async def _get_pull_requests(self, **kwargs) -> Dict[str, Any]:
        """Get pull requests."""
        repo = kwargs.get("repository", "")
        state = kwargs.get("state", "open")
        
        if not repo:
            raise ValueError("Repository parameter is required")
        
        return await self._make_mcp_request("list_pull_requests", {
            "repository": repo,
            "state": state
        })
    
    async def _get_actions_status(self, **kwargs) -> Dict[str, Any]:
        """Get GitHub Actions workflow status."""
        repo = kwargs.get("repository", "")
        if not repo:
            raise ValueError("Repository parameter is required")
        
        return await self._make_mcp_request("get_workflow_runs", {
            "repository": repo,
            "limit": 10
        })
    
    async def _get_releases(self, **kwargs) -> Dict[str, Any]:
        """Get recent releases."""
        repo = kwargs.get("repository", "")
        limit = kwargs.get("limit", 5)
        
        if not repo:
            raise ValueError("Repository parameter is required")
        
        return await self._make_mcp_request("list_releases", {
            "repository": repo,
            "limit": limit
        })
    
    async def _get_file_contents(self, **kwargs) -> Dict[str, Any]:
        """Get file or directory contents from repository."""
        repo = kwargs.get("repository", "")
        path = kwargs.get("path", "")
        branch = kwargs.get("branch", "main")
        
        if not repo or not path:
            raise ValueError("Repository and path parameters are required")
        
        # Parse owner/repo format
        if "/" in repo:
            owner, repo_name = repo.split("/", 1)
        else:
            raise ValueError("Repository must be in 'owner/repo' format")
        
        return await self._make_mcp_request("get_file_contents", {
            "owner": owner,
            "repo": repo_name,
            "path": path,
            "branch": branch
        })
    
    async def _search_code(self, **kwargs) -> Dict[str, Any]:
        """Search code across repositories."""
        query = kwargs.get("query", "")
        repository = kwargs.get("repository", "")
        language = kwargs.get("language", "")
        filename = kwargs.get("filename", "")
        
        if not query:
            raise ValueError("Query parameter is required")
        
        # Build search query with filters
        search_query = query
        if repository:
            search_query += f" repo:{repository}"
        if language:
            search_query += f" language:{language}"
        if filename:
            search_query += f" filename:{filename}"
        
        return await self._make_mcp_request("search_code", {
            "q": search_query,
            "perPage": kwargs.get("limit", 10)
        })
    
    async def _create_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new issue."""
        required_params = ["repository", "title", "body"]
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        return await self._make_mcp_request("create_issue", params)
    
    async def _add_comment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add comment to issue or pull request."""
        required_params = ["repository", "issue_number", "body"]
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        return await self._make_mcp_request("add_issue_comment", params)
    
    async def _update_issue(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update issue status or labels."""
        required_params = ["repository", "issue_number"]
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        return await self._make_mcp_request("update_issue", params)
    
    async def _create_pull_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a pull request."""
        required_params = ["repository", "title", "head", "base"]
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        return await self._make_mcp_request("create_pull_request", params)
    
    async def _merge_pull_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Merge a pull request."""
        required_params = ["repository", "pull_number"]
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        return await self._make_mcp_request("merge_pull_request", params)
    
    async def _trigger_workflow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a GitHub Actions workflow."""
        required_params = ["repository", "workflow_id"]
        for param in required_params:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
        
        return await self._make_mcp_request("trigger_workflow", params)
    
    async def _make_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make a request to the MCP server."""
        try:
            url = f"http://{self.server_host}:{self.server_port}/mcp/{method}"
            
            async with self.mcp_client.post(url, json=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"MCP request failed: {response.status} - {error_text}")
                    
        except Exception as e:
            self.logger.error(f"MCP request failed for {method}: {e}")
            raise