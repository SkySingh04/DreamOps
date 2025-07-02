"""Direct Notion integration using the Notion API."""

import json
from datetime import datetime
from typing import Any

import httpx

from ..services.notion_activity_tracker import notion_tracker
from .base import MCPIntegration


class NotionDirectIntegration(MCPIntegration):
    """Direct Notion integration using HTTP API calls."""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize Notion integration.
        
        Args:
            config: Configuration dictionary containing:
                - notion_token: Notion API token
                - database_id: Database ID for incident tracking (optional)
                - notion_version: API version (default: 2022-06-28)
        """
        super().__init__("notion", config)
        self.notion_token = self.config.get("notion_token")
        self.database_id = self.config.get("database_id")
        self.notion_version = self.config.get("notion_version", "2022-06-28")
        self.base_url = "https://api.notion.com/v1"
        self.client = None

        if not self.notion_token:
            raise ValueError("notion_token is required in config")

    async def connect(self) -> None:
        """Connect to Notion API."""
        try:
            # Create HTTP client with headers
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.notion_token}",
                    "Notion-Version": self.notion_version,
                    "Content-Type": "application/json"
                }
            )

            # Test connection by searching
            response = await self.client.post("/search", json={})
            if response.status_code == 200:
                self.connected = True
                self.connection_time = datetime.now()
                self.logger.info("Connected to Notion API")
            else:
                raise ConnectionError(f"Failed to connect: {response.status_code} - {response.text}")

        except Exception as e:
            self.logger.error(f"Failed to connect to Notion: {e}")
            raise ConnectionError(f"Failed to connect to Notion: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Notion API."""
        if self.client:
            await self.client.aclose()
            self.client = None

        self.connected = False
        self.connection_time = None
        self.logger.info("Disconnected from Notion API")

    async def fetch_context(self, context_type: str, **kwargs) -> dict[str, Any]:
        """Fetch context information from Notion."""
        self.validate_connection()

        if context_type == "search":
            return await self._search(**kwargs)
        elif context_type == "get_page":
            return await self._get_page(**kwargs)
        elif context_type == "get_database":
            return await self._get_database(**kwargs)
        else:
            raise ValueError(f"Unsupported context type: {context_type}")

    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an action in Notion."""
        self.validate_connection()

        if action == "create_page":
            return await self._create_page(**params)
        elif action == "update_page":
            return await self._update_page(**params)
        elif action == "append_to_page":
            return await self._append_to_page(**params)
        else:
            raise ValueError(f"Unsupported action: {action}")

    async def get_capabilities(self) -> dict[str, list[str]]:
        """Get capabilities of the Notion integration."""
        return {
            "context_types": [
                "search",
                "get_page",
                "get_database"
            ],
            "actions": [
                "create_page",
                "update_page",
                "append_to_page"
            ],
            "features": [
                "incident_documentation",
                "direct_api_access",
                "database_operations",
                "page_operations"
            ]
        }

    async def _search(self, query: str = "", **kwargs) -> dict[str, Any]:
        """Search Notion."""
        try:
            body = {"query": query}
            if kwargs.get("filter"):
                body["filter"] = kwargs["filter"]
            if kwargs.get("sort"):
                body["sort"] = kwargs["sort"]

            response = await self.client.post("/search", json=body)
            response.raise_for_status()
            result = response.json()

            # Track the search operation
            await notion_tracker.log_operation("search_pages", {
                "query": query,
                "results_count": len(result.get("results", [])),
                "has_more": result.get("has_more", False)
            })

            return result
        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            await notion_tracker.log_operation("search_pages", {
                "query": query,
                "success": False,
                "error": str(e)
            })
            return {"error": str(e)}

    async def _get_page(self, page_id: str, **kwargs) -> dict[str, Any]:
        """Get a Notion page."""
        try:
            response = await self.client.get(f"/pages/{page_id}")
            response.raise_for_status()
            result = response.json()

            # Track the read operation
            await notion_tracker.log_operation("read_page", {
                "page_id": page_id,
                "page_url": result.get("url"),
                "created_time": result.get("created_time"),
                "last_edited_time": result.get("last_edited_time")
            })

            return result
        except Exception as e:
            self.logger.error(f"Get page failed: {e}")
            await notion_tracker.log_operation("read_page", {
                "page_id": page_id,
                "success": False,
                "error": str(e)
            })
            return {"error": str(e)}

    async def _get_database(self, database_id: str, **kwargs) -> dict[str, Any]:
        """Get a Notion database."""
        try:
            response = await self.client.get(f"/databases/{database_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Get database failed: {e}")
            return {"error": str(e)}

    async def _create_page(self, **params) -> dict[str, Any]:
        """Create a Notion page."""
        try:
            response = await self.client.post("/pages", json=params)
            if response.status_code != 200:
                error_data = response.json()
                self.logger.error(f"Create page failed with status {response.status_code}: {error_data}")
                await notion_tracker.log_operation("create_page", {
                    "success": False,
                    "status_code": response.status_code,
                    "error": str(error_data),
                    "properties": params.get("properties", {})
                })
                return {"error": f"{response.status_code}: {error_data}"}

            result = response.json()

            # Track successful page creation
            await notion_tracker.log_operation("create_page", {
                "page_id": result.get("id"),
                "page_url": result.get("url"),
                "created_time": result.get("created_time"),
                "properties": params.get("properties", {}),
                "parent_type": "database" if params.get("parent", {}).get("database_id") else "workspace"
            })

            return result
        except Exception as e:
            self.logger.error(f"Create page failed: {e}")
            await notion_tracker.log_operation("create_page", {
                "success": False,
                "error": str(e),
                "properties": params.get("properties", {})
            })
            return {"error": str(e)}

    async def _update_page(self, page_id: str, properties: dict[str, Any], **kwargs) -> dict[str, Any]:
        """Update a Notion page."""
        try:
            response = await self.client.patch(
                f"/pages/{page_id}",
                json={"properties": properties}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Update page failed: {e}")
            return {"error": str(e)}

    async def _append_to_page(self, page_id: str, children: list[dict[str, Any]], **kwargs) -> dict[str, Any]:
        """Append blocks to a Notion page."""
        try:
            response = await self.client.patch(
                f"/blocks/{page_id}/children",
                json={"children": children}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Append to page failed: {e}")
            return {"error": str(e)}

    async def create_incident_documentation(self, alert_data: dict[str, Any]) -> dict[str, Any]:
        """Create incident documentation in Notion."""
        try:
            # First, search for existing pages to get parent
            search_result = await self._search()

            # Create page properties
            properties = {
                "Name": {
                    "title": [{
                        "text": {
                            "content": f"Incident: {alert_data.get('service_name')} - {alert_data.get('alert_id')}"
                        }
                    }]
                },
                "Status": {
                    "status": {
                        "name": "In progress"
                    }
                }
            }

            # Create page content blocks
            children = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "📋 Incident Overview"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "text": {
                                "content": f"Service: {alert_data.get('service_name')}\nAlert ID: {alert_data.get('alert_id')}\nSeverity: {alert_data.get('severity')}\nTimestamp: {alert_data.get('timestamp', datetime.now().isoformat())}"
                            }
                        }]
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                },
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"text": {"content": "🚨 Alert Description"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "text": {"content": alert_data.get('description', 'No description provided')[:1900]}
                        }]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"text": {"content": "📊 Metadata"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{
                            "text": {"content": json.dumps(alert_data.get('metadata', {}), indent=2)[:2000]}
                        }],
                        "language": "json"
                    }
                },
                {
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "🔍 Investigation Log"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"text": {"content": "Check service health metrics"}}],
                        "checked": False
                    }
                },
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"text": {"content": "Review recent deployments"}}],
                        "checked": False
                    }
                },
                {
                    "object": "block",
                    "type": "to_do",
                    "to_do": {
                        "rich_text": [{"text": {"content": "Check error logs"}}],
                        "checked": False
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "✅ Resolution"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": "Resolution details will be added here..."}}]
                    }
                }
            ]

            # Determine parent - if database_id is provided, use it
            parent = {}
            if self.database_id:
                parent = {"database_id": self.database_id}
            else:
                # Use the workspace as parent if no database specified
                parent = {"workspace": True}

            # Create the page
            page_data = {
                "parent": parent,
                "properties": properties,
                "children": children
            }

            result = await self._create_page(**page_data)

            if "error" not in result:
                self.logger.info(f"Created incident page with ID: {result.get('id')}")
                return {
                    "success": True,
                    "page_id": result.get("id"),
                    "url": result.get("url"),
                    "created_time": result.get("created_time")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error")
                }

        except Exception as e:
            self.logger.error(f"Failed to create incident documentation: {e}")
            return {
                "success": False,
                "error": str(e)
            }
