"""FastAPI server for webhook endpoints and API."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.oncall_agent.api import webhooks
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger


logger = get_logger(__name__)
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle events."""
    # Startup
    logger.info("Starting Oncall Agent API Server")
    logger.info(f"API Server running on {config.api_host}:{config.api_port}")
    logger.info(f"PagerDuty integration: {'enabled' if config.pagerduty_enabled else 'disabled'}")
    
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
    title="Oncall Agent API",
    description="AI-powered oncall agent with PagerDuty integration",
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
if config.pagerduty_enabled:
    app.include_router(webhooks.router)
    logger.info("PagerDuty webhook routes registered")


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {sig}, shutting down...")
    sys.exit(0)


def main():
    """Run the API server."""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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