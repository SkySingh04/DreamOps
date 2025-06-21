"""Base class for MCP (Model Context Protocol) integrations."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class MCPIntegration(ABC):
    """Abstract base class for MCP integrations.
    
    This class provides the interface that all MCP integrations must implement
    to work with the oncall agent. Each integration (Kubernetes, Grafana, etc.)
    should extend this class and implement the required methods.
    """

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        """Initialize the MCP integration.
        
        Args:
            name: Name of the integration (e.g., "kubernetes", "grafana")
            config: Optional configuration dictionary for the integration
        """
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.connected = False
        self.connection_time: datetime | None = None

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the MCP server/service.
        
        This method should establish the connection to the external service
        and perform any necessary authentication or initialization.
        
        Raises:
            ConnectionError: If unable to connect to the service
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the MCP server/service.
        
        This method should cleanly close the connection and release any
        resources being used by the integration.
        """
        pass

    @abstractmethod
    async def fetch_context(self, context_type: str, **kwargs) -> dict[str, Any]:
        """Fetch context information from the integration.
        
        This method retrieves relevant context data that can help in
        analyzing and resolving incidents.
        
        Args:
            context_type: Type of context to fetch (e.g., "metrics", "logs", "status")
            **kwargs: Additional parameters specific to the context type
            
        Returns:
            Dictionary containing the requested context information
            
        Raises:
            ValueError: If context_type is not supported
            ConnectionError: If not connected to the service
        """
        pass

    @abstractmethod
    async def execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute an action through the integration.
        
        This method performs actions like restarting services, scaling deployments,
        or updating configurations.
        
        Args:
            action: The action to perform (e.g., "restart_pod", "scale_deployment")
            params: Parameters required for the action
            
        Returns:
            Dictionary containing the result of the action
            
        Raises:
            ValueError: If action is not supported or params are invalid
            PermissionError: If the integration lacks permissions for the action
            ConnectionError: If not connected to the service
        """
        pass

    @abstractmethod
    async def get_capabilities(self) -> dict[str, list[str]]:
        """Get the capabilities of this integration.
        
        Returns a dictionary describing what context types and actions
        this integration supports.
        
        Returns:
            Dictionary with keys:
                - "context_types": List of supported context types
                - "actions": List of supported actions
                - "features": List of additional features
        """
        pass

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the integration.
        
        Returns:
            Dictionary containing health status information
        """
        return {
            "name": self.name,
            "connected": self.connected,
            "connection_time": self.connection_time.isoformat() if self.connection_time else None,
            "status": "healthy" if self.connected else "disconnected"
        }

    def validate_connection(self) -> None:
        """Validate that the integration is connected.
        
        Raises:
            ConnectionError: If not connected
        """
        if not self.connected:
            raise ConnectionError(f"{self.name} integration is not connected")

    async def retry_operation(self, operation, max_attempts: int = 3, delay: float = 1.0):
        """Retry an operation with exponential backoff.
        
        Args:
            operation: Async function to retry
            max_attempts: Maximum number of attempts
            delay: Initial delay between attempts in seconds
            
        Returns:
            Result of the operation
            
        Raises:
            The last exception if all attempts fail
        """
        last_exception = None

        for attempt in range(max_attempts):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    wait_time = delay * (2 ** attempt)
                    self.logger.warning(
                        f"Operation failed (attempt {attempt + 1}/{max_attempts}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Operation failed after {max_attempts} attempts: {e}")

        raise last_exception
