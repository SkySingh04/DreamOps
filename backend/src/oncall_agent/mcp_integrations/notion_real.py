"""Real Notion MCP integration using MCP protocol communication."""

import json
import subprocess
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from .base import MCPIntegration


class NotionRealMCPIntegration(MCPIntegration):
    """Notion MCP integration using real MCP protocol communication."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Notion MCP integration.
        
        Args:
            config: Configuration dictionary containing:
                - notion_token: Notion API token
                - database_id: Database ID for incident tracking
                - notion_version: API version (default: 2022-06-28)
        """
        super().__init__("notion", config)
        self.process: Optional[subprocess.Popen] = None
        self.notion_token = self.config.get("notion_token")
        self.database_id = self.config.get("database_id")
        self.notion_version = self.config.get("notion_version", "2022-06-28")
        
        if not self.notion_token:
            raise ValueError("notion_token is required in config")
    
    async def connect(self) -> None:
        """Connect to the Notion MCP server."""
        try:
            # Set up environment variables for the MCP server
            env = {
                **subprocess.os.environ.copy(),
                "OPENAPI_MCP_HEADERS": json.dumps({
                    "Authorization": f"Bearer {self.notion_token}",
                    "Notion-Version": self.notion_version
                })
            }
            
            # Start the Notion MCP server process
            self.process = subprocess.Popen(
                ["npx", "-y", "@notionhq/notion-mcp-server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=0
            )
            
            # Wait for the server to be ready
            await asyncio.sleep(3)
            
            # Check if process is still running
            if self.process.poll() is not None:
                stderr = self.process.stderr.read() if self.process.stderr else ""
                raise ConnectionError(f"Notion MCP server failed to start: {stderr}")
            
            # Send initialization request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {}
                },
                "id": 1
            }
            
            response = await self._send_request(init_request)
            if response and response.get("result"):
                self.connected = True
                self.connection_time = datetime.now()
                self.logger.info("Connected to Notion MCP server")
            else:
                raise ConnectionError("Failed to initialize MCP connection")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Notion MCP: {e}")
            raise ConnectionError(f"Failed to connect to Notion MCP: {e}")
    
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
    
    async def _send_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC request to the MCP server."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise ConnectionError("MCP server process not running")
        
        try:
            # Send request
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str)
            self.process.stdin.flush()
            
            # Read response
            response_str = self.process.stdout.readline()
            if response_str:
                return json.loads(response_str)
            return None
            
        except Exception as e:
            self.logger.error(f"Error communicating with MCP server: {e}")
            return None
    
    async def fetch_context(self, context_type: str, **kwargs) -> Dict[str, Any]:
        """Fetch context information from Notion using MCP protocol."""
        self.validate_connection()
        
        if context_type == "search":
            return await self._search_notion(**kwargs)
        elif context_type == "get_page":
            return await self._get_page(**kwargs)
        elif context_type == "get_database":
            return await self._get_database(**kwargs)
        else:
            raise ValueError(f"Unsupported context type: {context_type}")
    
    async def execute_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action in Notion using MCP protocol."""
        self.validate_connection()
        
        if action == "create_page":
            return await self._create_page(**params)
        elif action == "update_page":
            return await self._update_page(**params)
        elif action == "create_database_item":
            return await self._create_database_item(**params)
        else:
            raise ValueError(f"Unsupported action: {action}")
    
    async def get_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of the Notion integration."""
        # Request tool list from MCP server
        list_tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": str(uuid.uuid4())
        }
        
        response = await self._send_request(list_tools_request)
        
        if response and response.get("result"):
            tools = response["result"].get("tools", [])
            tool_names = [tool["name"] for tool in tools]
            
            # Categorize tools
            context_types = []
            actions = []
            
            for name in tool_names:
                if any(x in name for x in ["search", "retrieve", "get", "list"]):
                    context_types.append(name)
                else:
                    actions.append(name)
            
            return {
                "context_types": context_types[:10],  # Limit for display
                "actions": actions[:10],
                "features": [
                    "incident_documentation",
                    "real_notion_api",
                    "database_operations",
                    "page_operations"
                ]
            }
        
        # Fallback if MCP request fails
        return {
            "context_types": ["search", "get_page", "get_database"],
            "actions": ["create_page", "update_page", "create_database_item"],
            "features": ["incident_documentation", "real_notion_api"]
        }
    
    async def _search_notion(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search Notion using MCP protocol."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "query": query,
                    "filter": kwargs.get("filter", {}),
                    "sort": kwargs.get("sort", {})
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = await self._send_request(request)
        return response.get("result", {}) if response else {}
    
    async def _get_page(self, page_id: str, **kwargs) -> Dict[str, Any]:
        """Get a Notion page using MCP protocol."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "blocks_children_list",
                "arguments": {
                    "block_id": page_id
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = await self._send_request(request)
        return response.get("result", {}) if response else {}
    
    async def _get_database(self, database_id: str, **kwargs) -> Dict[str, Any]:
        """Get a Notion database using MCP protocol."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "databases_retrieve",
                "arguments": {
                    "database_id": database_id
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = await self._send_request(request)
        return response.get("result", {}) if response else {}
    
    async def _create_page(self, **params) -> Dict[str, Any]:
        """Create a Notion page using MCP protocol."""
        # Construct page creation request
        parent = params.get("parent", {})
        properties = params.get("properties", {})
        children = params.get("children", [])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "pages_create",
                "arguments": {
                    "parent": parent,
                    "properties": properties,
                    "children": children
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = await self._send_request(request)
        return response.get("result", {}) if response else {}
    
    async def _update_page(self, page_id: str, **params) -> Dict[str, Any]:
        """Update a Notion page using MCP protocol."""
        properties = params.get("properties", {})
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "pages_update",
                "arguments": {
                    "page_id": page_id,
                    "properties": properties
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = await self._send_request(request)
        return response.get("result", {}) if response else {}
    
    async def _create_database_item(self, **params) -> Dict[str, Any]:
        """Create a database item using MCP protocol."""
        database_id = params.get("database_id", self.database_id)
        properties = params.get("properties", {})
        
        if not database_id:
            raise ValueError("database_id is required")
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "pages_create",
                "arguments": {
                    "parent": {"database_id": database_id},
                    "properties": properties
                }
            },
            "id": str(uuid.uuid4())
        }
        
        response = await self._send_request(request)
        return response.get("result", {}) if response else {}
    
    async def create_incident_documentation(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create incident documentation in Notion using real API."""
        try:
            # Create properties for the incident page
            properties = {
                "Name": {
                    "title": [{
                        "text": {
                            "content": f"Incident: {alert_data.get('service_name')} - {alert_data.get('alert_id')}"
                        }
                    }]
                }
            }
            
            # Create children blocks for the page content
            children = [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Incident Overview"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "text": {
                                "content": f"Service: {alert_data.get('service_name')}\nAlert ID: {alert_data.get('alert_id')}\nSeverity: {alert_data.get('severity')}\n\nDescription:\n{alert_data.get('description')}"
                            }
                        }]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Investigation Log"}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"text": {"content": "Investigation steps will be logged here..."}}]
                    }
                },
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"text": {"content": "Resolution"}}]
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
            
            # Determine parent (database or page)
            parent = {}
            if self.database_id:
                parent = {"database_id": self.database_id}
            else:
                # If no database_id, create as a standalone page
                parent = {"page_id": "root"}  # This would need to be a real page ID
            
            # Create the page
            result = await self._create_page(
                parent=parent,
                properties=properties,
                children=children
            )
            
            if result:
                self.logger.info(f"Created incident page with ID: {result.get('id')}")
                return {
                    "success": True,
                    "page_id": result.get("id"),
                    "url": result.get("url"),
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create page"
                }
            
        except Exception as e:
            self.logger.error(f"Failed to create incident documentation: {e}")
            return {
                "success": False,
                "error": str(e)
            }