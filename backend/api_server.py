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
    admin_integrations,
    agent_logs,
    agent_router,
    alert_crud,
    alert_tracking,
    analytics_router,
    api_keys,
    auth_setup,
    chaos,
    dashboard_router,
    dev_config,
    firebase_auth,
    incidents_router,
    integrations_router,
    mock_payments,
    monitoring_router,
    payments_router,
    security_router,
    settings_router,
    user_integrations,
)
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger, setup_logging

# Setup logging FIRST before creating any loggers
config = get_config()
setup_logging(level=config.log_level)

logger = get_logger(__name__)

# Log configuration for debugging
logger.info(f"Configuration loaded - NODE_ENV: {config.node_env}, ENVIRONMENT: {getattr(config, 'environment', 'not set')}")


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

    # Start Kubernetes MCP server if enabled
    if config.k8s_enabled and config.k8s_use_mcp_server:
        logger.info("Starting Kubernetes MCP server...")
        try:
            import asyncio
            import subprocess

            # Extract port from MCP server URL
            mcp_port = '8080'
            if config.k8s_mcp_server_url:
                parts = config.k8s_mcp_server_url.split(':')
                if len(parts) >= 3:
                    mcp_port = parts[-1]

            # Start the official MCP Kubernetes server
            env = os.environ.copy()
            env['K8S_MCP_SERVER_PORT'] = mcp_port

            # Use the kubernetes-mcp-server by manusa with HTTP port
            mcp_process = subprocess.Popen(
                ['pnpm', 'exec', 'kubernetes-mcp-server', '--http-port', mcp_port],
                env=env
            )
            app.state.mcp_process = mcp_process

            # Wait for server to start
            await asyncio.sleep(2)
            logger.info(f"Kubernetes MCP server started on port {mcp_port}")
        except Exception as e:
            logger.error(f"Failed to start Kubernetes MCP server: {e}")
            app.state.mcp_process = None

    yield

    # Shutdown
    logger.info("Shutting down Oncall Agent API Server")
    if config.pagerduty_enabled:
        from src.oncall_agent.api.webhooks import agent_trigger
        if agent_trigger:
            await agent_trigger.shutdown()

    # Stop MCP server if running
    if hasattr(app.state, 'mcp_process') and app.state.mcp_process:
        logger.info("Stopping Kubernetes MCP server...")
        try:
            app.state.mcp_process.terminate()
            app.state.mcp_process.wait(timeout=5)
        except:
            app.state.mcp_process.kill()


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


# Add request logging middleware - MUST be added BEFORE CORS to ensure proper order
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    # Log request details
    logger.info(f"Incoming request: {request.method} {request.url.path}")

    # Skip body reading for OPTIONS requests to prevent interference with CORS
    if request.method == "OPTIONS":
        response = await call_next(request)
        return response

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
                "path": getattr(route, "path", ""),
                "methods": list(getattr(route, "methods", set())),
                "name": getattr(route, "name", "")
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

        # Define all available MCP integrations
        available_mcp_integrations = {
            "kubernetes_mcp": {
                "name": "kubernetes_mcp",
                "display_name": "Kubernetes MCP",
                "description": "Kubernetes cluster management and monitoring",
                "capabilities": {
                    "context_types": ["pods", "deployments", "services", "events", "logs"],
                    "actions": ["restart_pod", "scale_deployment", "rollback_deployment", "execute_kubectl"],
                    "features": ["risk_assessment", "dry_run", "auto_approval"],
                    "execution_modes": ["direct", "dry_run", "approval_required"],
                    "risk_assessment": ["low", "medium", "high"],
                    "command_types": ["get", "describe", "logs", "version", "cluster-info", "top", "api-resources", "explain", "scale", "rollout", "restart", "label", "annotate", "set", "expose", "delete", "apply", "create", "replace", "patch", "edit", "exec", "port-forward", "proxy", "drain", "cordon", "uncordon"]
                }
            },
            "notion": {
                "name": "notion",
                "display_name": "Notion MCP",
                "description": "Notion database integration for incident documentation",
                "capabilities": {
                    "context_types": ["pages", "databases", "blocks"],
                    "actions": ["create_page", "update_page", "query_database", "search_content"],
                    "features": ["documentation", "knowledge_base", "incident_logs"],
                    "content_types": ["text", "code", "tables", "lists", "media"]
                }
            },
            "github": {
                "name": "github",
                "display_name": "GitHub MCP",
                "description": "GitHub repository and issue management",
                "capabilities": {
                    "context_types": ["repositories", "issues", "pull_requests", "commits", "actions"],
                    "actions": ["create_issue", "update_issue", "create_pr", "merge_pr", "trigger_action"],
                    "features": ["code_review", "issue_tracking", "ci_cd", "version_control"],
                    "repository_operations": ["read", "write", "admin"]
                }
            },
            "grafana": {
                "name": "grafana",
                "display_name": "Grafana MCP",
                "description": "Grafana dashboards and alerting",
                "capabilities": {
                    "context_types": ["dashboards", "panels", "alerts", "datasources"],
                    "actions": ["create_dashboard", "update_panel", "create_alert", "query_metrics"],
                    "features": ["visualization", "alerting", "monitoring", "analytics"],
                    "data_sources": ["prometheus", "influxdb", "elasticsearch", "mysql", "postgres"]
                }
            },
            "pagerduty": {
                "name": "pagerduty",
                "display_name": "PagerDuty MCP",
                "description": "PagerDuty incident management and escalation",
                "capabilities": {
                    "context_types": ["incidents", "services", "users", "schedules"],
                    "actions": ["create_incident", "update_incident", "acknowledge", "resolve"],
                    "features": ["incident_management", "escalation", "on_call", "notifications"],
                    "incident_operations": ["create", "update", "acknowledge", "resolve", "escalate"]
                }
            },
            "datadog": {
                "name": "datadog",
                "display_name": "Datadog MCP",
                "description": "Datadog monitoring and APM",
                "capabilities": {
                    "context_types": ["metrics", "logs", "traces", "dashboards", "monitors"],
                    "actions": ["query_metrics", "search_logs", "create_monitor", "update_dashboard"],
                    "features": ["monitoring", "apm", "log_management", "alerting"],
                    "data_types": ["metrics", "logs", "traces", "events"]
                }
            }
        }

        # Try to get agent instance for real status
        try:
            from src.oncall_agent.api.webhooks import agent_trigger, get_agent_trigger
            if agent_trigger and hasattr(agent_trigger, 'agent') and agent_trigger.agent:
                agent = agent_trigger.agent
            else:
                # Initialize agent if not already done
                trigger = await get_agent_trigger()
                agent = trigger.agent

            # Get real status from agent if available
            for mcp_name, mcp_info in available_mcp_integrations.items():
                try:
                    if agent and mcp_name in agent.mcp_integrations:
                        integration = agent.mcp_integrations[mcp_name]
                        is_healthy = await integration.health_check()
                        real_capabilities = await integration.get_capabilities()
                        integrations.append({
                            "name": mcp_name,
                            "display_name": mcp_info["display_name"],
                            "description": mcp_info["description"],
                            "capabilities": real_capabilities if real_capabilities else mcp_info["capabilities"],
                            "connected": is_healthy,
                            "configured": True
                        })
                    else:
                        # Show as available but not configured
                        integrations.append({
                            "name": mcp_name,
                            "display_name": mcp_info["display_name"],
                            "description": mcp_info["description"],
                            "capabilities": mcp_info["capabilities"],
                            "connected": False,
                            "configured": False
                        })
                except Exception as e:
                    logger.error(f"Error checking integration {mcp_name}: {e}")
                    integrations.append({
                        "name": mcp_name,
                        "display_name": mcp_info["display_name"],
                        "description": mcp_info["description"],
                        "capabilities": mcp_info["capabilities"],
                        "connected": False,
                        "configured": False
                    })
        except Exception as e:
            logger.error(f"Error getting agent instance: {e}")
            # Fallback: return all available integrations as not configured
            for mcp_name, mcp_info in available_mcp_integrations.items():
                integrations.append({
                    "name": mcp_name,
                    "display_name": mcp_info["display_name"],
                    "description": mcp_info["description"],
                    "capabilities": mcp_info["capabilities"],
                    "connected": False,
                    "configured": False
                })

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
app.include_router(payments_router, prefix="/api/v1")
app.include_router(mock_payments.router, prefix="/api/v1")
app.include_router(alert_tracking, prefix="/api/v1")
app.include_router(alert_crud, prefix="/api/v1")
app.include_router(api_keys.router)
app.include_router(user_integrations.router)  # Already has /api/v1 prefix
app.include_router(admin_integrations.router)  # Admin integration verification routes

# Include dev config router only in development mode
if config.node_env == "development" or config.environment == "development":
    app.include_router(dev_config.router)
    app.include_router(chaos.router, prefix="/api/v1")
    logger.info("Dev config and chaos routes registered (development mode)")
else:
    logger.info(f"Dev routes not registered (node_env={config.node_env}, environment={config.environment})")

# Conditionally include webhook router
if config.pagerduty_enabled:
    app.include_router(webhooks.router)
    logger.info("PagerDuty webhook routes registered")

logger.info("All API routes registered successfully")

# Add request logging middleware AFTER routes are registered
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Log all incoming requests for debugging."""
    return await log_requests(request, call_next)

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
