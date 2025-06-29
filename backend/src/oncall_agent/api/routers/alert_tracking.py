"""Alert tracking and usage limits API router."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...config import get_config
from ...utils import get_logger

logger = get_logger(__name__)
config = get_config()

router = APIRouter(prefix="/alert-tracking", tags=["Alert Tracking"])


class AlertUsageResponse(BaseModel):
    """Alert usage response model."""
    alerts_used: int
    alerts_limit: int
    alerts_remaining: int
    account_tier: str
    plan_name: str
    billing_cycle_end: str
    is_limit_reached: bool


class RecordAlertRequest(BaseModel):
    """Request model for recording alert usage."""
    user_id: str
    alert_type: str
    incident_id: str | None = None
    metadata: dict | None = None


class UpdateSubscriptionRequest(BaseModel):
    """Request model for updating subscription."""
    user_id: str
    plan_id: str
    transaction_id: str


# In-memory storage for demo (replace with database in production)
USER_DATA = {}

SUBSCRIPTION_PLANS = {
    "free": {"name": "Free", "alerts_limit": 3, "price": 0},
    "starter": {"name": "Starter", "alerts_limit": 50, "price": 999},
    "pro": {"name": "Professional", "alerts_limit": 200, "price": 2999},
    "enterprise": {"name": "Enterprise", "alerts_limit": -1, "price": 9999},
}

# Integration restrictions by plan
INTEGRATION_RESTRICTIONS = {
    "free": ["kubernetes_mcp", "pagerduty"],  # Only K8s and PagerDuty
    "starter": ["kubernetes_mcp", "pagerduty"],  # Only K8s and PagerDuty
    "pro": ["kubernetes_mcp", "pagerduty", "notion", "github", "grafana", "datadog"],  # All integrations
    "enterprise": ["kubernetes_mcp", "pagerduty", "notion", "github", "grafana", "datadog"],  # All integrations
}


@router.get("/usage/{user_id}", response_model=AlertUsageResponse)
async def get_alert_usage(user_id: str):
    """Get alert usage for a user."""
    logger.info(f"Getting alert usage for user: {user_id}")
    
    # Check if in development mode
    import os
    is_dev_mode = os.getenv("NEXT_PUBLIC_DEV_MODE", "false").lower() == "true" or os.getenv("NODE_ENV", "") == "development"

    # Initialize user data if not exists
    if user_id not in USER_DATA:
        # In dev mode, start with Pro plan
        default_plan = "pro" if is_dev_mode else "free"
        default_limit = SUBSCRIPTION_PLANS[default_plan]["alerts_limit"]
        
        USER_DATA[user_id] = {
            "alerts_used": 0,
            "alerts_limit": default_limit,
            "account_tier": default_plan,
            "billing_cycle_start": datetime.now().replace(day=1),
            "incidents_processed": set()  # Track processed incident IDs
        }

    user_data = USER_DATA[user_id]

    # Check if we need to reset monthly usage
    now = datetime.now()
    billing_start = user_data["billing_cycle_start"]
    if (now - billing_start).days >= 30:
        # Reset for new billing cycle
        user_data["billing_cycle_start"] = now.replace(day=1)
        user_data["alerts_used"] = 0
        user_data["incidents_processed"] = set()

    # Calculate billing cycle end (1 month from start)
    billing_cycle_end = user_data["billing_cycle_start"] + timedelta(days=30)

    alerts_remaining = max(0, user_data["alerts_limit"] - user_data["alerts_used"])
    is_limit_reached = user_data["alerts_used"] >= user_data["alerts_limit"]
    
    # Get plan name from SUBSCRIPTION_PLANS
    plan_info = SUBSCRIPTION_PLANS.get(user_data["account_tier"], {"name": "Free"})
    plan_name = plan_info["name"]

    return AlertUsageResponse(
        alerts_used=user_data["alerts_used"],
        alerts_limit=user_data["alerts_limit"],
        alerts_remaining=alerts_remaining,
        account_tier=user_data["account_tier"],
        plan_name=plan_name,
        billing_cycle_end=billing_cycle_end.isoformat(),
        is_limit_reached=is_limit_reached
    )


@router.post("/record")
async def record_alert_usage(request: RecordAlertRequest):
    """Record alert usage for a user."""
    logger.info(f"Recording alert usage for user: {request.user_id}, type: {request.alert_type}, incident: {request.incident_id}")

    # Check if in development mode
    import os
    is_dev_mode = os.getenv("NEXT_PUBLIC_DEV_MODE", "false").lower() == "true" or os.getenv("NODE_ENV", "") == "development"
    
    # Initialize user data if not exists
    if request.user_id not in USER_DATA:
        # In dev mode, start with Pro plan
        default_plan = "pro" if is_dev_mode else "free"
        default_limit = SUBSCRIPTION_PLANS[default_plan]["alerts_limit"]
        
        USER_DATA[request.user_id] = {
            "alerts_used": 0,
            "alerts_limit": default_limit,
            "account_tier": default_plan,
            "billing_cycle_start": datetime.now().replace(day=1),
            "incidents_processed": set()
        }

    user_data = USER_DATA[request.user_id]

    # Check if this incident was already processed
    if request.incident_id and request.incident_id in user_data["incidents_processed"]:
        logger.info(f"Incident {request.incident_id} already processed, skipping")
        return {
            "success": True,
            "alerts_used": user_data["alerts_used"],
            "alerts_remaining": max(0, user_data["alerts_limit"] - user_data["alerts_used"]),
            "already_processed": True
        }

    # Check if limit reached
    if user_data["alerts_limit"] != -1 and user_data["alerts_used"] >= user_data["alerts_limit"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Alert limit reached",
                "message": "You have reached your monthly alert limit. Please upgrade your subscription to continue.",
                "alerts_used": user_data["alerts_used"],
                "alerts_limit": user_data["alerts_limit"],
                "account_tier": user_data["account_tier"]
            }
        )

    # Increment usage
    user_data["alerts_used"] += 1
    if request.incident_id:
        user_data["incidents_processed"].add(request.incident_id)

    alerts_remaining = max(0, user_data["alerts_limit"] - user_data["alerts_used"]) if user_data["alerts_limit"] != -1 else -1

    return {
        "success": True,
        "alerts_used": user_data["alerts_used"],
        "alerts_remaining": alerts_remaining,
        "is_limit_reached": user_data["alerts_limit"] != -1 and user_data["alerts_used"] >= user_data["alerts_limit"]
    }


@router.post("/upgrade-plan")
async def upgrade_subscription(user_id: str, plan_id: str, transaction_id: str):
    """Upgrade user subscription."""
    logger.info(f"Upgrading subscription for user: {user_id} to plan: {plan_id}")

    if plan_id not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan ID")

    plan = SUBSCRIPTION_PLANS[plan_id]

    # Initialize user data if not exists
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {
            "alerts_used": 0,
            "alerts_limit": 3,
            "account_tier": "free",
            "billing_cycle_start": datetime.now().replace(day=1),
            "incidents_processed": set()
        }

    # Update subscription
    USER_DATA[user_id].update({
        "account_tier": plan_id,
        "alerts_limit": plan["alerts_limit"],
        "last_payment_at": datetime.now(),
        "transaction_id": transaction_id
    })

    logger.info(f"User {user_id} upgraded to {plan_id} plan with {plan['alerts_limit']} alerts")

    return {
        "success": True,
        "new_tier": plan_id,
        "new_limit": plan["alerts_limit"],
        "transaction_id": transaction_id,
        "message": f"Successfully upgraded to {plan['name']} plan"
    }


@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans."""
    return {
        "plans": [
            {
                "id": plan_id,
                "name": plan["name"],
                "price": plan["price"],
                "price_display": f"₹{plan['price']}" if plan["price"] > 0 else "Free",
                "alerts_limit": plan["alerts_limit"],
                "alerts_limit_display": "Unlimited" if plan["alerts_limit"] == -1 else str(plan["alerts_limit"]),
                "features": []
            }
            for plan_id, plan in SUBSCRIPTION_PLANS.items()
        ]
    }


@router.get("/current-plan/{user_id}")
async def get_current_plan(user_id: str):
    """Get current plan details for a user."""
    if user_id not in USER_DATA:
        # Default to free plan
        return {
            "plan_id": "free",
            "plan_name": "Free",
            "alerts_limit": 3,
            "alerts_limit_display": "3",
            "price_display": "Free"
        }
    
    user_data = USER_DATA[user_id]
    plan_id = user_data.get("account_tier", "free")
    plan_info = SUBSCRIPTION_PLANS.get(plan_id, SUBSCRIPTION_PLANS["free"])
    
    return {
        "plan_id": plan_id,
        "plan_name": plan_info["name"],
        "alerts_limit": plan_info["alerts_limit"],
        "alerts_limit_display": "Unlimited" if plan_info["alerts_limit"] == -1 else str(plan_info["alerts_limit"]),
        "price_display": f"₹{plan_info['price']}" if plan_info["price"] > 0 else "Free"
    }


@router.get("/check-integration-access/{user_id}/{integration_name}")
async def check_integration_access(user_id: str, integration_name: str):
    """Check if a user has access to a specific integration based on their plan."""
    # Check if in development mode - always allow if NEXT_PUBLIC_DEV_MODE is true
    import os
    if os.getenv("NEXT_PUBLIC_DEV_MODE", "false").lower() == "true":
        return {"has_access": True, "reason": "Development mode - all integrations enabled"}
    
    # Get user's current plan
    if user_id not in USER_DATA:
        plan_id = "free"
    else:
        plan_id = USER_DATA[user_id].get("account_tier", "free")
    
    # Get allowed integrations for the plan
    allowed_integrations = INTEGRATION_RESTRICTIONS.get(plan_id, [])
    
    # Check if integration is allowed
    has_access = integration_name in allowed_integrations
    
    return {
        "has_access": has_access,
        "user_plan": plan_id,
        "allowed_integrations": allowed_integrations,
        "reason": f"Integration '{integration_name}' is {'allowed' if has_access else 'not allowed'} on {plan_id} plan"
    }
