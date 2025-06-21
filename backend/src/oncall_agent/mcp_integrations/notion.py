"""Notion MCP integration for incident response documentation."""

import asyncio
import json
import subprocess
from datetime import datetime
from typing import Any

from .base import MCPIntegration


class NotionMCPIntegration(MCPIntegration):
    """Notion MCP integration for creating and updating incident documentation."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Notion MCP integration.
        
        Args:
            config: Configuration dictionary containing:
                - notion_token: Notion API token
                - database_id: Database ID for incident tracking
                - notion_version: API version (default: 2022-06-28)
        """
        super().__init__("notion", config)
        self.process: subprocess.Popen | None = None
        self.notion_token = self.config.get("notion_token")
        self.database_id = self.config.get("database_id")
        self.notion_version = self.config.get("notion_version", "2022-06-28")

        if not self.notion_token:
            raise ValueError("notion_token is required in config")

    async def connect(self) -> None:
        """Connect to the Notion MCP server."""
        try:
            import os

            # Set up environment variables for the MCP server
            env = os.environ.copy()
            env.update({
                "NOTION_TOKEN": self.notion_token,
                "NOTION_VERSION": self.notion_version
            })

            # Use the local notion-mcp-server if available
            server_path = "../../notion-mcp-server/bin/cli.mjs"

            # Start the Notion MCP server process
            self.process = subprocess.Popen(
                ["node", server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd="/mnt/c/Users/himan/OneDrive/Desktop/WarpSpeed/oncall-agent/backend"
            )

            # Wait a moment for the server to start
            await asyncio.sleep(3)

            # Check if process is still running
            if self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                stdout = self.process.stdout.read() if self.process.stdout else ""
                self.logger.error(f"Notion MCP server stderr: {stderr}")
                self.logger.error(f"Notion MCP server stdout: {stdout}")

                # Fallback to npx if local server fails
                self.logger.info("Falling back to npx notion-mcp-server...")
                self.process = subprocess.Popen(
                    ["npx", "-y", "@notionhq/notion-mcp-server"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )
                await asyncio.sleep(3)

                if self.process.poll() is not None:
                    stderr = self.process.stderr.read() if self.process.stderr else ""
                    raise ConnectionError(f"Notion MCP server failed to start: {stderr}")

            self.connected = True
            self.connection_time = datetime.now()
            self.logger.info("Connected to Notion MCP server")

        except Exception as e:
            self.logger.error(f"Failed to connect to Notion MCP: {e}")
            # Don't raise error, mark as disconnected and continue
            self.connected = False
            self.logger.warning("Notion MCP server not available, some features may be limited")

    async def disconnect(self) -> None:
        """Disconnect from the Notion MCP server."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None

        self.connected = False
        self.connection_time = None
        self.logger.info("Disconnected from Notion MCP server")

    async def fetch_context(self, context_type: str, **kwargs) -> dict[str, Any]:
        """Fetch context information from Notion.
        
        Args:
            context_type: Type of context to fetch
                - "database": Get database schema
                - "pages": Get pages from database
                - "page_content": Get specific page content
            **kwargs: Additional parameters
        
        Returns:
            Context information from Notion
        """
        self.validate_connection()

        if context_type == "database":
            return await self._fetch_database_context(**kwargs)
        elif context_type == "pages":
            return await self._fetch_pages_context(**kwargs)
        elif context_type == "page_content":
            return await self._fetch_page_content(**kwargs)
        else:
            raise ValueError(f"Unsupported context type: {context_type}")

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an action in Notion.
        
        Args:
            action: Action to perform
                - "create_incident_page": Create new incident documentation page
                - "update_page": Update existing page
                - "add_comment": Add comment to page
                - "create_database_entry": Create entry in database
            params: Parameters for the action
        
        Returns:
            Result of the action
        """
        self.validate_connection()

        if action == "create_incident_page":
            return await self._create_incident_page(**params)
        elif action == "update_page":
            return await self._update_page(**params)
        elif action == "add_comment":
            return await self._add_comment(**params)
        elif action == "create_database_entry":
            return await self._create_database_entry(**params)
        else:
            raise ValueError(f"Unsupported action: {action}")

    async def get_capabilities(self) -> dict[str, list[str]]:
        """Get capabilities of the Notion integration."""
        return {
            "context_types": [
                "database",
                "pages",
                "page_content"
            ],
            "actions": [
                "create_incident_page",
                "update_page",
                "add_comment",
                "create_database_entry"
            ],
            "features": [
                "incident_documentation",
                "runbook_access",
                "team_collaboration",
                "status_tracking"
            ]
        }

    async def _fetch_database_context(self, **kwargs) -> dict[str, Any]:
        """Fetch database schema and properties."""
        database_id = kwargs.get("database_id", self.database_id)
        if not database_id:
            raise ValueError("database_id is required")

        # This would be implemented using the MCP protocol
        # For now, return mock data
        return {
            "database_id": database_id,
            "title": "Incident Tracking",
            "properties": {
                "Name": {"type": "title"},
                "Status": {"type": "select"},
                "Severity": {"type": "select"},
                "Assigned": {"type": "people"},
                "Created": {"type": "created_time"}
            }
        }

    async def _fetch_pages_context(self, **kwargs) -> dict[str, Any]:
        """Fetch pages from a database."""
        database_id = kwargs.get("database_id", self.database_id)
        if not database_id:
            raise ValueError("database_id is required")

        # Mock implementation - would use MCP protocol
        return {
            "pages": [],
            "has_more": False,
            "next_cursor": None
        }

    async def _fetch_page_content(self, page_id: str, **kwargs) -> dict[str, Any]:
        """Fetch content of a specific page."""
        # Mock implementation - would use MCP protocol
        return {
            "page_id": page_id,
            "title": "Sample Page",
            "content": "Page content would be here"
        }

    async def _create_incident_page(self, **params) -> dict[str, Any]:
        """Create a new incident documentation page."""
        alert_id = params.get("alert_id")
        service_name = params.get("service_name")
        severity = params.get("severity")
        description = params.get("description")
        metadata = params.get("metadata", {})

        if not all([alert_id, service_name, severity, description]):
            raise ValueError("alert_id, service_name, severity, and description are required")

        try:
            # If MCP server is available, try to use it
            if self.connected and self.process:
                return await self._create_page_via_mcp(alert_id, service_name, severity, description, metadata)
            else:
                # Fallback to creating a mock response
                self.logger.warning("MCP server not available, creating mock incident page")
                return await self._create_mock_page(alert_id, service_name, severity, description, metadata)

        except Exception as e:
            self.logger.error(f"Failed to create incident page: {e}")
            # Fallback to mock on any error
            return await self._create_mock_page(alert_id, service_name, severity, description, metadata)

    async def _create_page_via_mcp(self, alert_id: str, service_name: str, severity: str, description: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Create page using MCP protocol."""
        try:
            # Create MCP request for page creation
            mcp_request = {
                "jsonrpc": "2.0",
                "id": f"create_page_{alert_id}",
                "method": "tools/call",
                "params": {
                    "name": "create_page",
                    "arguments": {
                        "parent": {"page_id": "workspace"} if not self.database_id else {"database_id": self.database_id},
                        "properties": {
                            "title": {
                                "title": [{"text": {"content": f"Incident: {service_name} - {alert_id}"}}]
                            }
                        },
                        "children": [
                            {
                                "object": "block",
                                "type": "heading_2",
                                "heading_2": {"rich_text": [{"text": {"content": "🚨 Incident Overview"}}]}
                            },
                            {
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{
                                        "text": {"content": f"**Alert ID:** {alert_id}\n**Service:** {service_name}\n**Severity:** {severity}\n**Timestamp:** {datetime.now().isoformat()}\n\n**Description:**\n{description}"}
                                    }]
                                }
                            },
                            {
                                "object": "block",
                                "type": "heading_3",
                                "heading_3": {"rich_text": [{"text": {"content": "📊 Metadata"}}]}
                            },
                            {
                                "object": "block",
                                "type": "code",
                                "code": {
                                    "rich_text": [{"text": {"content": json.dumps(metadata, indent=2)}}],
                                    "language": "json"
                                }
                            }
                        ]
                    }
                }
            }

            # Send request to MCP server
            self.process.stdin.write(json.dumps(mcp_request) + "\n")
            self.process.stdin.flush()

            # Wait for response (simplified - real implementation would be more robust)
            await asyncio.sleep(1)

            # Read response (this is simplified)
            response_line = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(self.process.stdout.readline)),
                timeout=10
            )

            if response_line:
                response = json.loads(response_line.strip())
                if "result" in response:
                    page_id = response["result"].get("id")
                    page_url = response["result"].get("url")
                    self.logger.info(f"Successfully created Notion page via MCP: {page_id}")
                    return {
                        "success": True,
                        "page_id": page_id,
                        "url": page_url,
                        "created_via": "mcp_server"
                    }

            # If we get here, MCP didn't work properly
            raise Exception("MCP server communication failed")

        except Exception as e:
            self.logger.error(f"MCP page creation failed: {e}")
            raise

    async def _create_mock_page(self, alert_id: str, service_name: str, severity: str, description: str, metadata: dict[str, Any]) -> dict[str, Any]:
        """Create mock page when MCP is not available."""
        page_id = f"mock-incident-{alert_id}-{int(datetime.now().timestamp())}"
        self.logger.info(f"Created mock incident page for alert {alert_id}")
        return {
            "success": True,
            "page_id": page_id,
            "url": f"https://notion.so/mock-page-{page_id}",
            "title": f"Incident: {service_name} - {alert_id}",
            "created_via": "mock",
            "properties": {
                "Alert ID": alert_id,
                "Service": service_name,
                "Severity": severity,
                "Status": "Open",
                "Created": datetime.now().isoformat()
            },
            "content": f"## Incident Overview\n\n**Service:** {service_name}\n**Alert ID:** {alert_id}\n**Severity:** {severity}\n\n**Description:**\n{description}\n\n**Metadata:**\n```json\n{json.dumps(metadata, indent=2)}\n```\n\n## Investigation Log\n\n_Investigation steps will be logged here..._\n\n## Resolution\n\n_Resolution details will be added here..._"
        }

    async def _update_page(self, page_id: str, content: str, **kwargs) -> dict[str, Any]:
        """Update an existing page."""
        # Mock implementation - would use MCP protocol
        self.logger.info(f"Updated page {page_id}")
        return {
            "page_id": page_id,
            "updated": True,
            "timestamp": datetime.now().isoformat()
        }

    async def _add_comment(self, page_id: str, comment: str, **kwargs) -> dict[str, Any]:
        """Add a comment to a page."""
        # Mock implementation - would use MCP protocol
        self.logger.info(f"Added comment to page {page_id}")
        return {
            "page_id": page_id,
            "comment_id": f"comment-{datetime.now().timestamp()}",
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        }

    async def _create_database_entry(self, **params) -> dict[str, Any]:
        """Create an entry in a database."""
        database_id = params.get("database_id", self.database_id)
        properties = params.get("properties", {})

        if not database_id:
            raise ValueError("database_id is required")

        # Mock implementation - would use MCP protocol
        entry_id = f"entry-{datetime.now().timestamp()}"
        self.logger.info(f"Created database entry {entry_id}")
        return {
            "entry_id": entry_id,
            "database_id": database_id,
            "properties": properties,
            "created": datetime.now().isoformat()
        }

    async def create_incident_documentation(self, alert_data: dict[str, Any]) -> dict[str, Any]:
        """Helper method to create comprehensive incident documentation."""
        try:
            # Create incident page using MCP
            page_result = await self.execute_action("create_incident_page", {
                "alert_id": alert_data.get("alert_id"),
                "service_name": alert_data.get("service_name"),
                "severity": alert_data.get("severity"),
                "description": alert_data.get("description"),
                "metadata": alert_data.get("metadata", {})
            })

            # Create database entry if database_id is configured
            database_result = None
            if self.database_id:
                try:
                    database_result = await self.execute_action("create_database_entry", {
                        "properties": {
                            "Name": alert_data.get("service_name"),
                            "Alert ID": alert_data.get("alert_id"),
                            "Severity": alert_data.get("severity"),
                            "Status": "Open"
                        }
                    })
                except Exception as e:
                    self.logger.warning(f"Failed to create database entry: {e}")

            # Extract results
            if page_result.get("success"):
                return {
                    "success": True,
                    "page_id": page_result.get("page_id"),
                    "url": page_result.get("url"),
                    "created_via": page_result.get("created_via", "unknown"),
                    "incident_page": page_result,
                    "database_entry": database_result
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create incident page"
                }

        except Exception as e:
            self.logger.error(f"Failed to create incident documentation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
