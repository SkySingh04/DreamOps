"""Placeholder MCP integration for unconfigured services."""

from typing import Any

from .base import MCPIntegration


class PlaceholderMCPIntegration(MCPIntegration):
    """Placeholder integration for services that are not configured."""

    def __init__(self, name: str, reason: str):
        """Initialize placeholder integration.
        
        Args:
            name: Name of the integration
            reason: Reason why the integration is not available
        """
        super().__init__(name)
        self.reason = reason

    async def connect(self) -> None:
        """Placeholder connect method."""
        self.logger.info(f"Placeholder integration '{self.name}' cannot connect: {self.reason}")
        self.connected = False

    async def disconnect(self) -> None:
        """Placeholder disconnect method."""
        self.connected = False

    async def fetch_context(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Placeholder fetch_context method."""
        return {
            "error": f"Integration '{self.name}' is not configured",
            "reason": self.reason,
            "status": "unavailable"
        }

    async def execute_action(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Placeholder execute_action method."""
        return {
            "error": f"Integration '{self.name}' is not configured",
            "reason": self.reason,
            "action": action,
            "status": "unavailable"
        }

    def get_capabilities(self) -> list[str]:
        """Return empty capabilities list."""
        return []

    async def health_check(self) -> bool:
        """Placeholder health check - always returns False."""
        return False
