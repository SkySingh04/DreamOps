"""FastAPI application for the Oncall Agent."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import OncallAgent, PagerAlert
from .api.routers.api_keys import router as api_keys_router
from .api.routers.settings import router as settings_router
from .config import get_config
from .utils import setup_logging

# Setup logging
config = get_config()
setup_logging(level=config.log_level)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DreamOps API",
    description="Dream easy while AI takes your on-call duty. AI-powered incident response and infrastructure management.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_keys_router)
app.include_router(settings_router, prefix="/api/v1")

# Global agent instance (deprecated - use api_server.py instead)
agent: OncallAgent | None = None


class AlertRequest(BaseModel):
    """Request model for creating alerts."""
    severity: str
    service_name: str
    description: str
    metadata: dict[str, Any] = {}


class AlertResponse(BaseModel):
    """Response model for alert processing."""
    alert_id: str
    status: str
    analysis: str | None = None
    k8s_alert_type: str | None = None
    suggested_actions: list | None = None


@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup."""
    global agent
    logger.info("Starting Oncall AI Agent API")
    agent = OncallAgent()
    await agent.connect_integrations()
    logger.info("Agent initialized and ready")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global agent
    if agent:
        await agent.shutdown()
    logger.info("Agent shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "agent_ready": agent is not None
    }


@app.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_request: AlertRequest,
    background_tasks: BackgroundTasks
):
    """Process a new alert."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    # Create PagerAlert from request
    alert = PagerAlert(
        alert_id=f"API-{datetime.now().timestamp()}",
        severity=alert_request.severity,
        service_name=alert_request.service_name,
        description=alert_request.description,
        timestamp=datetime.now(UTC).isoformat(),
        metadata=alert_request.metadata
    )

    logger.info(f"Received alert via API: {alert.alert_id}")

    # Process alert
    try:
        result = await agent.handle_pager_alert(alert)

        return AlertResponse(
            alert_id=alert.alert_id,
            status=result.get("status", "processed"),
            analysis=result.get("analysis"),
            k8s_alert_type=result.get("k8s_alert_type"),
            suggested_actions=result.get("suggested_actions", [])
        )
    except Exception as e:
        logger.error(f"Error processing alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get alert details (placeholder for future implementation)."""
    # TODO: Implement alert storage and retrieval
    return {
        "alert_id": alert_id,
        "message": "Alert retrieval not yet implemented"
    }


@app.get("/integrations")
async def list_integrations():
    """List available MCP integrations."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    integrations = []
    for name, integration in agent.mcp_integrations.items():
        integrations.append({
            "name": name,
            "capabilities": await integration.get_capabilities(),
            "connected": await integration.health_check()
        })

    return {"integrations": integrations}


@app.post("/integrations/{name}/health")
async def check_integration_health(name: str):
    """Check health of a specific integration."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if name not in agent.mcp_integrations:
        raise HTTPException(status_code=404, detail=f"Integration '{name}' not found")

    integration = agent.mcp_integrations[name]
    is_healthy = await integration.health_check()

    return {
        "name": name,
        "healthy": is_healthy,
        "capabilities": await integration.get_capabilities()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
