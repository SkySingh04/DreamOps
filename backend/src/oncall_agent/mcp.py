"""MCP (Model Context Protocol) client for communicating with MCP servers."""

import json
import logging
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass
class MCPToolResult:
    """Result from an MCP tool call."""
    success: bool
    content: list[dict[str, Any]] | None = None
    error: str | None = None


class MCPClient:
    """HTTP client for MCP servers."""

    def __init__(self, base_url: str, logger: logging.Logger | None = None, context: str | None = None):
        """Initialize MCP client.
        
        Args:
            base_url: Base URL of the MCP server (e.g. http://localhost:8080)
            logger: Optional logger instance
            context: Kubernetes context to use (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.logger = logger or logging.getLogger(__name__)
        self.session: aiohttp.ClientSession | None = None
        self.available_tools: list[str] = []
        self._connected = False
        self.context = context

    async def connect(self) -> bool:
        """Connect to the MCP server and discover available tools."""
        try:
            if self.session:
                await self.session.close()

            self.session = aiohttp.ClientSession()

            # For kubernetes-mcp-server, check if the server is accessible
            # The server uses HTTP streaming at /mcp endpoint with SSE
            self.logger.info(f"Attempting to connect to MCP server at {self.base_url}/mcp")
            async with self.session.get(f"{self.base_url}/mcp", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status in [200, 202]:  # 202 Accepted is expected for SSE
                    # kubernetes-mcp-server doesn't send tool list immediately
                    # We'll hardcode the known tools based on the documentation
                    self.available_tools = [
                        'pods_list', 'pods_list_in_namespace', 'pods_get', 'pods_log',
                        'pods_delete', 'pods_exec', 'pods_run', 'pods_top',
                        'resources_list', 'resources_get', 'resources_create_or_update',
                        'resources_delete', 'events_list', 'namespaces_list',
                        'configuration_view', 'helm_install', 'helm_list', 'helm_uninstall'
                    ]
                    self._connected = True
                    self.logger.info(f"Connected to MCP server. Status: {resp.status}")
                    return True
                else:
                    body = await resp.text()
                    self.logger.error(f"Failed to connect to MCP server. Status: {resp.status}, Body: {body[:200]}")
                    return False

        except TimeoutError:
            self.logger.error("Timeout connecting to MCP server")
            return False
        except Exception as e:
            self.logger.error(f"Error connecting to MCP server: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self.session:
            await self.session.close()
            self.session = None
        self._connected = False
        self.available_tools = []

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> MCPToolResult:
        """Call an MCP tool with the given parameters.
        
        Args:
            tool_name: Name of the tool to call
            params: Parameters to pass to the tool
            
        Returns:
            MCPToolResult with the response
        """
        if not self._connected or not self.session:
            return MCPToolResult(success=False, error="Not connected to MCP server")

        try:
            # For kubernetes-mcp-server, we need to send messages via SSE protocol
            # The server expects newline-delimited JSON messages
            message = {
                "method": tool_name,
                "params": params
            }

            # Send as form data with SSE format
            async with self.session.post(
                f"{self.base_url}/mcp",
                data=json.dumps(message) + "\n",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in [200, 202]:
                    # Read SSE response
                    response_data = None
                    async for line in resp.content:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])
                                response_data = data
                                break  # Take first response
                            except json.JSONDecodeError:
                                pass

                    if response_data:
                        if "error" in response_data:
                            return MCPToolResult(
                                success=False,
                                error=response_data.get("error", "Unknown error")
                            )
                        else:
                            # Extract result
                            content = response_data.get("result", response_data)
                            if not isinstance(content, list):
                                content = [{"text": json.dumps(content, indent=2)}]
                            return MCPToolResult(success=True, content=content)
                    else:
                        return MCPToolResult(success=False, error="No response data")
                else:
                    error_text = await resp.text()
                    return MCPToolResult(
                        success=False,
                        error=f"HTTP {resp.status}: {error_text}"
                    )

        except TimeoutError:
            return MCPToolResult(success=False, error=f"Timeout calling tool {tool_name}")
        except Exception as e:
            self.logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return MCPToolResult(success=False, error=str(e))
