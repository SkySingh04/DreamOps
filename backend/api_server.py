"""FastAPI server for webhook endpoints and API."""

import json
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.oncall_agent.api import webhooks
from src.oncall_agent.api.routers import (
    agent_logs,
    agent_router,
    analytics_router,
    api_keys,
    auth,
    auth_setup,
    dashboard_router,
    incidents_router,
    integrations_router,
    monitoring_router,
    security_router,
    settings_router,
    team_integrations,
    firebase_auth,
)
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger, setup_logging

# Setup logging FIRST before creating any loggers
config = get_config()
setup_logging(level=config.log_level)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle events."""
    # Startup
    logger.info("Starting Oncall Agent API Server")
    logger.info(f"API Server running on {config.api_host}:{config.api_port}")
    logger.info(f"PagerDuty integration: {'enabled' if config.pagerduty_enabled else 'disabled'}")
    logger.info(f"PagerDuty webhook secret configured: {bool(config.pagerduty_webhook_secret)}")
    logger.info(f"Log level: {config.log_level}")

    # Initialize webhook handler
    if config.pagerduty_enabled:
        from src.oncall_agent.api.webhooks import get_agent_trigger
        trigger = await get_agent_trigger()
        logger.info("OncallAgent initialized for webhook handling")

    yield

    # Shutdown
    logger.info("Shutting down Oncall Agent API Server")
    if config.pagerduty_enabled:
        from src.oncall_agent.api.webhooks import agent_trigger
        if agent_trigger:
            await agent_trigger.shutdown()


# Create FastAPI app
app = FastAPI(
    title="DreamOps API",
    description="Dream easy while AI takes your on-call duty. AI-powered incident response platform with PagerDuty integration.",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
origins = config.cors_origins.split(",") if hasattr(config, 'cors_origins') else ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    # Log request details
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    
    # Log authorization header for debugging authentication issues
    auth_header = request.headers.get("authorization")
    if request.url.path.startswith("/api/v1/auth/"):
        logger.info(f"Auth endpoint called: {request.url.path}")
        logger.info(f"Authorization header present: {bool(auth_header)}")
        if auth_header:
            logger.info(f"Authorization header format: {auth_header[:20]}...")

    # Log webhook requests in detail
    if request.url.path == "/webhook/pagerduty":
        body = await request.body()
        logger.info(f"PagerDuty webhook headers: {dict(request.headers)}")
        try:
            payload = json.loads(body) if body else {}
            # logger.info(f"PagerDuty webhook payload: {json.dumps(payload, indent=2)}")
        except:
            logger.info(f"PagerDuty webhook raw body: {body}")

        # Important: Create a new request with the body we read
        from starlette.requests import Request as StarletteRequest

        async def receive():
            return {"type": "http.request", "body": body}

        request = StarletteRequest(
            scope=request.scope,
            receive=receive
        )

    response = await call_next(request)
    return response


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Oncall Agent API",
        "version": "0.1.0",
        "status": "healthy",
        "features": {
            "pagerduty_webhooks": config.pagerduty_enabled,
            "kubernetes_integration": config.k8s_enabled,
        }
    }


@app.get("/routes")
async def list_routes():
    """List all registered routes for debugging."""
    routes = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    return {"routes": sorted(routes, key=lambda x: x["path"])}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "checks": {
            "api": "ok",
            "config": "ok",
            "pagerduty_enabled": config.pagerduty_enabled,
        }
    }

    # Check agent if initialized
    if config.pagerduty_enabled:
        try:
            from src.oncall_agent.api.webhooks import agent_trigger
            if agent_trigger:
                queue_status = agent_trigger.get_queue_status()
                health_status["checks"]["agent"] = "ok"
                health_status["checks"]["queue_size"] = queue_status["queue_size"]
            else:
                health_status["checks"]["agent"] = "not_initialized"
        except Exception as e:
            health_status["checks"]["agent"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

    return health_status


@app.get("/integrations")
async def get_mcp_integrations():
    """Get MCP integration status for frontend."""
    try:
        integrations = []
        
        # Try to get agent instance
        try:
            from src.oncall_agent.api.webhooks import agent_trigger
            if agent_trigger and hasattr(agent_trigger, 'agent') and agent_trigger.agent:
                agent = agent_trigger.agent
                
                # Get MCP integrations from agent
                for name, integration in agent.mcp_integrations.items():
                    try:
                        is_healthy = await integration.health_check()
                        integrations.append({
                            "name": name,
                            "capabilities": await integration.get_capabilities(),
                            "connected": is_healthy
                        })
                    except Exception as e:
                        logger.error(f"Error checking integration {name}: {e}")
                        integrations.append({
                            "name": name,
                            "capabilities": [],
                            "connected": False
                        })
        except Exception as e:
            logger.error(f"Error getting agent instance: {e}")
        
        return {"integrations": integrations}
    except Exception as e:
        logger.error(f"Error getting MCP integrations: {e}")
        return {"integrations": []}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if config.log_level == "DEBUG" else "An error occurred processing your request"
        }
    )


# Include routers
# Always include core routers
# Note: Both firebase_auth and auth_setup have /api/v1/auth prefix
# FastAPI will merge routes from both routers under the same prefix
app.include_router(firebase_auth.router)  # Firebase auth endpoints
app.include_router(auth_setup.router)  # Auth and setup flow endpoints
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(agent_logs.router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(security_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(api_keys.router)
app.include_router(team_integrations.router)  # Already has /api/v1 prefix

# Conditionally include webhook router
if config.pagerduty_enabled:
    app.include_router(webhooks.router)
    logger.info("PagerDuty webhook routes registered")

logger.info("All API routes registered successfully")

# Mount Socket.IO application - TEMPORARILY DISABLED
# app.mount("/socket.io", socket_app)
# logger.info("Socket.IO server mounted at /socket.io")


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)


def main():
    """Run the API server."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Filter out ONLY WebSocket connection logs
    class WebSocketFilter(logging.Filter):
        def filter(self, record):
            # Filter out WebSocket connection messages ONLY
            msg = record.getMessage()
            if "/socket.io/" in msg and ("WebSocket" in msg or "connection" in msg):
                return False
            # Allow all other logs including PagerDuty webhooks
            return True

    # Apply filter to uvicorn access logger
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addFilter(WebSocketFilter())

    # Get port from environment variable or use default
    import os
    port = int(os.environ.get("PORT", config.api_port))
    
    # Run server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",  # Bind to all interfaces for Render
        port=port,
        reload=config.api_reload,
        workers=config.api_workers if not config.api_reload else 1,
        log_level=config.api_log_level.lower(),
    )


if __name__ == "__main__":
    main()
