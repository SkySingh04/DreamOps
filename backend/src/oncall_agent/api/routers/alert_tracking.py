"""Alert tracking and usage limits API router."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
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
    billing_cycle_end: str
    is_limit_reached: bool


class RecordAlertRequest(BaseModel):
    """Request model for recording alert usage."""
    team_id: str
    alert_type: str
    incident_id: Optional[str] = None
    metadata: Optional[dict] = None


class UpdateSubscriptionRequest(BaseModel):
    """Request model for updating subscription."""
    team_id: str
    plan_id: str
    transaction_id: str


# In-memory storage for demo (replace with database in production)
TEAM_DATA = {}

SUBSCRIPTION_PLANS = {
    "free": {"name": "Free", "alerts_limit": 3, "price": 0},
    "starter": {"name": "Starter", "alerts_limit": 50, "price": 999},
    "pro": {"name": "Professional", "alerts_limit": 200, "price": 2999},
    "enterprise": {"name": "Enterprise", "alerts_limit": -1, "price": 9999},
}


@router.get("/usage/{team_id}", response_model=AlertUsageResponse)
async def get_alert_usage(team_id: str):
    """Get alert usage for a team."""
    logger.info(f"Getting alert usage for team: {team_id}")
    
    # Initialize team data if not exists
    if team_id not in TEAM_DATA:
        TEAM_DATA[team_id] = {
            "alerts_used": 0,
            "alerts_limit": 3,
            "account_tier": "free",
            "billing_cycle_start": datetime.now().replace(day=1),
            "incidents_processed": set()  # Track processed incident IDs
        }
    
    team_data = TEAM_DATA[team_id]
    
    # Check if we need to reset monthly usage
    now = datetime.now()
    billing_start = team_data["billing_cycle_start"]
    if (now - billing_start).days >= 30:
        # Reset for new billing cycle
        team_data["billing_cycle_start"] = now.replace(day=1)
        team_data["alerts_used"] = 0
        team_data["incidents_processed"] = set()
    
    # Calculate billing cycle end (1 month from start)
    billing_cycle_end = team_data["billing_cycle_start"] + timedelta(days=30)
    
    alerts_remaining = max(0, team_data["alerts_limit"] - team_data["alerts_used"])
    is_limit_reached = team_data["alerts_used"] >= team_data["alerts_limit"]
    
    return AlertUsageResponse(
        alerts_used=team_data["alerts_used"],
        alerts_limit=team_data["alerts_limit"],
        alerts_remaining=alerts_remaining,
        account_tier=team_data["account_tier"],
        billing_cycle_end=billing_cycle_end.isoformat(),
        is_limit_reached=is_limit_reached
    )


@router.post("/record")
async def record_alert_usage(request: RecordAlertRequest):
    """Record alert usage for a team."""
    logger.info(f"Recording alert usage for team: {request.team_id}, type: {request.alert_type}, incident: {request.incident_id}")
    
    # Initialize team data if not exists
    if request.team_id not in TEAM_DATA:
        TEAM_DATA[request.team_id] = {
            "alerts_used": 0,
            "alerts_limit": 3,
            "account_tier": "free",
            "billing_cycle_start": datetime.now().replace(day=1),
            "incidents_processed": set()
        }
    
    team_data = TEAM_DATA[request.team_id]
    
    # Check if this incident was already processed
    if request.incident_id and request.incident_id in team_data["incidents_processed"]:
        logger.info(f"Incident {request.incident_id} already processed, skipping")
        return {
            "success": True,
            "alerts_used": team_data["alerts_used"],
            "alerts_remaining": max(0, team_data["alerts_limit"] - team_data["alerts_used"]),
            "already_processed": True
        }
    
    # Check if limit reached
    if team_data["alerts_limit"] != -1 and team_data["alerts_used"] >= team_data["alerts_limit"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Alert limit reached",
                "message": "You have reached your monthly alert limit. Please upgrade your subscription to continue.",
                "alerts_used": team_data["alerts_used"],
                "alerts_limit": team_data["alerts_limit"],
                "account_tier": team_data["account_tier"]
            }
        )
    
    # Increment usage
    team_data["alerts_used"] += 1
    if request.incident_id:
        team_data["incidents_processed"].add(request.incident_id)
    
    alerts_remaining = max(0, team_data["alerts_limit"] - team_data["alerts_used"]) if team_data["alerts_limit"] != -1 else -1
    
    return {
        "success": True,
        "alerts_used": team_data["alerts_used"],
        "alerts_remaining": alerts_remaining,
        "is_limit_reached": team_data["alerts_limit"] != -1 and team_data["alerts_used"] >= team_data["alerts_limit"]
    }


@router.post("/upgrade")
async def upgrade_subscription(request: UpdateSubscriptionRequest):
    """Upgrade team subscription."""
    logger.info(f"Upgrading subscription for team: {request.team_id} to plan: {request.plan_id}")
    
    if request.plan_id not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan ID")
    
    plan = SUBSCRIPTION_PLANS[request.plan_id]
    
    # Initialize team data if not exists
    if request.team_id not in TEAM_DATA:
        TEAM_DATA[request.team_id] = {
            "alerts_used": 0,
            "alerts_limit": 3,
            "account_tier": "free",
            "billing_cycle_start": datetime.now().replace(day=1),
            "incidents_processed": set()
        }
    
    # Update subscription
    TEAM_DATA[request.team_id].update({
        "account_tier": request.plan_id,
        "alerts_limit": plan["alerts_limit"],
        "last_payment_at": datetime.now(),
        "transaction_id": request.transaction_id
    })
    
    logger.info(f"Team {request.team_id} upgraded to {request.plan_id} plan with {plan['alerts_limit']} alerts")
    
    return {
        "success": True,
        "new_tier": request.plan_id,
        "new_limit": plan["alerts_limit"],
        "transaction_id": request.transaction_id,
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
                "alerts_limit": plan["alerts_limit"],
                "features": []
            }
            for plan_id, plan in SUBSCRIPTION_PLANS.items()
        ]
    }