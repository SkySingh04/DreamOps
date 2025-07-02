"""API routers package."""

from .agent import router as agent_router
from .alert_crud import router as alert_crud
from .alert_tracking import router as alert_tracking
from .analytics import router as analytics_router
from .dashboard import router as dashboard_router
from .incidents import router as incidents_router
from .integrations import router as integrations_router
from .monitoring import router as monitoring_router
from .payments import router as payments_router
from .security import router as security_router
from .settings import router as settings_router

__all__ = [
    "dashboard_router",
    "incidents_router",
    "agent_router",
    "integrations_router",
    "analytics_router",
    "security_router",
    "monitoring_router",
    "settings_router",
    "payments_router",
    "alert_tracking",
    "alert_crud"
]
