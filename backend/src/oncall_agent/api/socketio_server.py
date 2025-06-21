"""Socket.IO server for real-time WebSocket communication."""

import asyncio
from datetime import UTC, datetime
from typing import Any

import socketio

from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)

# Create Socket.IO server with CORS support
sio = socketio.AsyncServer(
    cors_allowed_origins="*",  # Configure appropriately for production
    async_mode="asgi",
    logger=False,
    engineio_logger=False,
)

# Create Socket.IO app
socket_app = socketio.ASGIApp(sio)


class BaseNamespace(socketio.AsyncNamespace):
    """Base namespace for Socket.IO events."""

    async def on_connect(self, sid: str, environ: dict) -> None:
        """Handle client connection."""
        logger.info(f"Client connected: {sid}")
        await self.emit("connected", {"status": "connected", "sid": sid}, room=sid)

    async def on_disconnect(self, sid: str) -> None:
        """Handle client disconnection."""
        logger.info(f"Client disconnected: {sid}")

    async def on_error(self, sid: str, error: str) -> None:
        """Handle connection errors."""
        logger.error(f"Socket.IO error for {sid}: {error}")


class MonitoringNamespace(BaseNamespace):
    """Namespace for monitoring-related events."""

    namespace = "/monitoring"

    async def on_subscribe_metrics(self, sid: str, data: dict) -> None:
        """Subscribe to real-time metrics."""
        logger.info(f"Client {sid} subscribed to metrics")
        # Start sending metrics to this client
        asyncio.create_task(self._send_metrics(sid))

    async def _send_metrics(self, sid: str) -> None:
        """Send periodic metrics to a client."""
        try:
            while True:
                # Check if client is still connected
                if sid not in self.server.manager.rooms.get("/monitoring", {}).get("", []):
                    break

                # Generate mock metrics (replace with real metrics in production)
                metrics = {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "cpu_usage": 45.2,
                    "memory_usage": 67.8,
                    "active_incidents": 3,
                    "queue_size": 5,
                }

                await self.emit("metric_update", metrics, room=sid)
                await asyncio.sleep(5)  # Send every 5 seconds

        except Exception as e:
            logger.error(f"Error sending metrics to {sid}: {e}")


class IncidentNamespace(BaseNamespace):
    """Namespace for incident-related events."""

    namespace = "/incidents"

    async def on_subscribe_incidents(self, sid: str, data: dict) -> None:
        """Subscribe to incident updates."""
        logger.info(f"Client {sid} subscribed to incidents")
        await self.emit("subscription_confirmed", {"status": "subscribed"}, room=sid)


# Register namespaces
sio.register_namespace(MonitoringNamespace())
sio.register_namespace(IncidentNamespace())


# Default namespace handlers
@sio.event
async def connect(sid: str, environ: dict) -> None:
    """Handle client connection to default namespace."""
    logger.info(f"Client connected to default namespace: {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection from default namespace."""
    logger.info(f"Client disconnected from default namespace: {sid}")


@sio.event
async def message(sid: str, data: Any) -> None:
    """Handle generic message event."""
    logger.info(f"Message from {sid}: {data}")
    await sio.emit("response", {"status": "received", "echo": data}, room=sid)


# Helper functions for sending events from other parts of the application
async def emit_incident_update(incident_data: dict[str, Any]) -> None:
    """Emit incident update to all connected clients."""
    await sio.emit(
        "incident_update",
        {
            "type": "incident_update",
            "data": incident_data,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        namespace="/incidents",
    )


async def emit_integration_status(integration_name: str, status: str, details: dict[str, Any] = None) -> None:
    """Emit integration status update."""
    await sio.emit(
        "integration_status",
        {
            "type": "integration_status",
            "data": {
                "integration": integration_name,
                "status": status,
                "details": details or {},
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def emit_ai_action(action: str, details: dict[str, Any]) -> None:
    """Emit AI agent action notification."""
    await sio.emit(
        "ai_action",
        {
            "type": "ai_action",
            "data": {
                "action": action,
                "details": details,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def emit_metric_update(metrics: dict[str, Any]) -> None:
    """Emit metric update to monitoring namespace."""
    await sio.emit(
        "metric_update",
        {
            "type": "metric_update",
            "data": metrics,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        namespace="/monitoring",
    )
