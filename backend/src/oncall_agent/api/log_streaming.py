"""
Real-time log streaming infrastructure for AI agent logs.
"""
import asyncio
import json
import logging
from collections import deque
from collections.abc import AsyncGenerator
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import Request
from sse_starlette.sse import EventSourceResponse


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    ALERT = "ALERT"


@dataclass
class AgentLogEntry:
    """Structured log entry for AI agent activities."""
    timestamp: str
    level: LogLevel
    message: str
    incident_id: str | None = None
    integration: str | None = None
    action_type: str | None = None
    metadata: dict[str, Any] | None = None
    progress: float | None = None  # 0.0 to 1.0
    stage: str | None = None  # "webhook_received", "gathering_context", "claude_analysis", etc.

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['level'] = self.level.value
        return data


class LogStreamManager:
    """Manages log streaming for connected clients."""

    def __init__(self, max_buffer_size: int = 1000):
        self.buffer: deque = deque(maxlen=max_buffer_size)
        self.clients: dict[str, asyncio.Queue] = {}
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)

    async def add_log(self, log_entry: AgentLogEntry):
        """Add a log entry and notify all connected clients."""
        async with self.lock:
            # Add to buffer for replay to new clients
            self.buffer.append(log_entry)

            # Send to all connected clients
            disconnected_clients = []
            for client_id, queue in self.clients.items():
                try:
                    # Non-blocking put with timeout
                    await asyncio.wait_for(
                        queue.put(log_entry.to_dict()),
                        timeout=0.5
                    )
                except (TimeoutError, asyncio.QueueFull):
                    # Mark client for disconnection if queue is full
                    disconnected_clients.append(client_id)

            # Remove disconnected clients
            for client_id in disconnected_clients:
                del self.clients[client_id]
                self.logger.info(f"Removed disconnected client: {client_id}")

    async def subscribe(self, client_id: str) -> asyncio.Queue:
        """Subscribe a client to log updates."""
        async with self.lock:
            queue = asyncio.Queue(maxsize=100)
            self.clients[client_id] = queue

            # Send buffered logs to new client
            for log_entry in self.buffer:
                await queue.put(log_entry.to_dict())

            self.logger.info(f"New client subscribed: {client_id}")
            return queue

    async def unsubscribe(self, client_id: str):
        """Unsubscribe a client from log updates."""
        async with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]
                self.logger.info(f"Client unsubscribed: {client_id}")

    def create_log_entry(
        self,
        message: str,
        level: LogLevel = LogLevel.INFO,
        incident_id: str | None = None,
        integration: str | None = None,
        action_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        progress: float | None = None,
        stage: str | None = None
    ) -> AgentLogEntry:
        """Create a structured log entry."""
        return AgentLogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level,
            message=message,
            incident_id=incident_id,
            integration=integration,
            action_type=action_type,
            metadata=metadata,
            progress=progress,
            stage=stage
        )

    # Convenience methods for different log levels
    async def log_alert(self, message: str, **kwargs):
        """Log an alert-level message."""
        entry = self.create_log_entry(message, LogLevel.ALERT, **kwargs)
        await self.add_log(entry)

    async def log_info(self, message: str, **kwargs):
        """Log an info-level message."""
        entry = self.create_log_entry(message, LogLevel.INFO, **kwargs)
        await self.add_log(entry)

    async def log_success(self, message: str, **kwargs):
        """Log a success-level message."""
        entry = self.create_log_entry(message, LogLevel.SUCCESS, **kwargs)
        await self.add_log(entry)

    async def log_error(self, message: str, **kwargs):
        """Log an error-level message."""
        entry = self.create_log_entry(message, LogLevel.ERROR, **kwargs)
        await self.add_log(entry)

    async def log_warning(self, message: str, **kwargs):
        """Log a warning-level message."""
        entry = self.create_log_entry(message, LogLevel.WARNING, **kwargs)
        await self.add_log(entry)


# Global log stream manager instance
log_stream_manager = LogStreamManager()


async def agent_log_generator(request: Request, client_id: str) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events for agent logs."""
    queue = await log_stream_manager.subscribe(client_id)

    try:
        while True:
            # Check if client is still connected
            if await request.is_disconnected():
                break

            try:
                # Wait for new log entries with timeout
                log_data = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield json.dumps({"data": log_data})
            except TimeoutError:
                # Send heartbeat to keep connection alive
                yield json.dumps({"type": "heartbeat", "timestamp": datetime.utcnow().isoformat() + "Z"})

    finally:
        await log_stream_manager.unsubscribe(client_id)


def create_sse_response(request: Request, client_id: str) -> EventSourceResponse:
    """Create an SSE response for streaming agent logs."""
    return EventSourceResponse(
        agent_log_generator(request, client_id),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )
