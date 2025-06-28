"""FastAPI server for webhook endpoints and API."""

import json
import logging
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
    dashboard_router,
    incidents_router,
    integrations_router,
    monitoring_router,
    security_router,
    settings_router,
    payments_router,
    alert_tracking,
    alert_crud,
)
from src.oncall_agent.api.routers import mock_payments
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
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
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")
app.include_router(agent_logs.router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(security_router, prefix="/api/v1")
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(mock_payments.router, prefix="/api/v1")
app.include_router(alert_tracking, prefix="/api/v1")
app.include_router(alert_crud, prefix="/api/v1")

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

    # Run server
    uvicorn.run(
        "api_server:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_reload,
        workers=config.api_workers if not config.api_reload else 1,
        log_level=config.api_log_level.lower(),
    )


if __name__ == "__main__":
    main()
