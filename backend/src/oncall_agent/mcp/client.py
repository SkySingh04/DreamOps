"""
MCP (Model Context Protocol) Client Implementation

This module provides a client for connecting to MCP servers and calling their tools.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiohttp


@dataclass
class MCPToolResult:
    """Result from an MCP tool call"""
    success: bool
    content: list[dict[str, Any]]
    error: str | None = None
    tool: str | None = None
    params: dict[str, Any] | None = None
    timestamp: datetime | None = None


class MCPClient:
    """Client for interacting with MCP servers"""

    def __init__(self, server_url: str, logger: logging.Logger | None = None):
        """
        Initialize MCP client.
        
        Args:
            server_url: URL of the MCP server (e.g., http://localhost:8080)
            logger: Optional logger instance
        """
        self.server_url = server_url.rstrip('/')
        self.logger = logger or logging.getLogger(__name__)
        self.session: aiohttp.ClientSession | None = None
        self._connected = False
        self._available_tools: list[str] = []

    async def connect(self) -> bool:
        """Connect to the MCP server and discover available tools."""
        try:
            if self.session:
                await self.session.close()

            self.session = aiohttp.ClientSession()

            # Test connection and get available tools
            async with self.session.get(f"{self.server_url}/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    self._available_tools = data.get('tools', [])
                    self._connected = True
                    self.logger.info(f"Connected to MCP server at {self.server_url}. Available tools: {len(self._available_tools)}")
                    return True
                else:
                    self.logger.error(f"Failed to connect to MCP server. Status: {response.status}")
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
        self._available_tools = []

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._connected

    @property
    def available_tools(self) -> list[str]:
        """Get list of available tools."""
        return self._available_tools.copy()

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> MCPToolResult:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            params: Parameters for the tool
            
        Returns:
            MCPToolResult with the response
        """
        if not self._connected:
            return MCPToolResult(
                success=False,
                content=[],
                error="Not connected to MCP server",
                tool=tool_name,
                params=params
            )

        if tool_name not in self._available_tools:
            return MCPToolResult(
                success=False,
                content=[],
                error=f"Tool '{tool_name}' not available on MCP server",
                tool=tool_name,
                params=params
            )

        try:
            # Make the tool call
            async with self.session.post(
                f"{self.server_url}/tools/{tool_name}",
                json=params,
                headers={'Content-Type': 'application/json'}
            ) as response:

                data = await response.json()

                if response.status == 200:
                    return MCPToolResult(
                        success=True,
                        content=data.get('content', []),
                        tool=tool_name,
                        params=params,
                        timestamp=datetime.utcnow()
                    )
                else:
                    return MCPToolResult(
                        success=False,
                        content=[],
                        error=data.get('error', f'Tool call failed with status {response.status}'),
                        tool=tool_name,
                        params=params
                    )

        except Exception as e:
            self.logger.error(f"Error calling tool {tool_name}: {e}")
            return MCPToolResult(
                success=False,
                content=[],
                error=str(e),
                tool=tool_name,
                params=params
            )

    async def list_contexts(self) -> list[str]:
        """List available Kubernetes contexts."""
        result = await self.call_tool('kubernetes_list_contexts', {})
        if result.success and result.content:
            # Extract contexts from the response
            try:
                text = result.content[0].get('text', '')
                data = json.loads(text) if text else {}
                return data.get('contexts', [])
            except:
                return []
        return []
