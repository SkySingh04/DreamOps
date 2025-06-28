"""Alert CRUD operations for testing and management"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/alerts", tags=["Alert Management"])

# In-memory storage for alerts (replace with database in production)
ALERTS_DB: dict[str, dict[str, Any]] = {}


class Alert(BaseModel):
    """Alert model"""
    id: str | None = None
    user_id: str
    incident_id: str
    alert_type: str = "manual"
    title: str | None = None
    description: str | None = None
    severity: str = "medium"  # low, medium, high, critical
    status: str = "active"  # active, resolved, acknowledged
    created_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class AlertUpdate(BaseModel):
    """Alert update model"""
    title: str | None = None
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class AlertResponse(BaseModel):
    """Alert response model"""
    success: bool
    message: str
    alert: Alert | None = None
    alerts: list[Alert] | None = None
    count: int | None = None


@router.post("/", response_model=AlertResponse)
async def create_alert(alert: Alert):
    """Create a new alert and increment usage count"""
    try:
        # Generate ID if not provided
        if not alert.id:
            alert.id = f"alert_{datetime.now().timestamp()}_{alert.incident_id}"

        # Set created_at if not provided
        if not alert.created_at:
            alert.created_at = datetime.now()

        # Check if alert already exists
        if alert.id in ALERTS_DB:
            raise HTTPException(status_code=400, detail="Alert already exists")

        # Store alert
        alert_dict = alert.dict()
        ALERTS_DB[alert.id] = alert_dict

        # Also record in alert tracking system
        from .alert_tracking import RecordAlertRequest, record_alert_usage
        try:
            usage_request = RecordAlertRequest(
                user_id=alert.user_id,
                alert_type=alert.alert_type,
                incident_id=alert.incident_id,
                metadata=alert.metadata
            )
            usage_result = await record_alert_usage(usage_request)
            logger.info(f"Alert usage recorded: {usage_result}")
        except HTTPException as e:
            # If limit reached, still create alert but return error
            if e.status_code == 403:
                ALERTS_DB.pop(alert.id, None)  # Remove the alert
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Alert limit reached",
                        "message": "You have reached your alert limit. Please upgrade your subscription.",
                        "alert_not_created": True
                    }
                )
        except Exception as e:
            logger.error(f"Failed to record alert usage: {e}")

        logger.info(f"Alert created: {alert.id} for user {alert.user_id}")

        return AlertResponse(
            success=True,
            message="Alert created successfully",
            alert=Alert(**alert_dict)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=AlertResponse)
async def list_alerts(
    user_id: str | None = Query(None, description="Filter by user ID"),
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum alerts to return"),
    offset: int = Query(0, ge=0, description="Number of alerts to skip")
):
    """List all alerts with optional filters"""
    try:
        # Filter alerts
        filtered_alerts = []
        for alert_id, alert_data in ALERTS_DB.items():
            if user_id and alert_data.get("user_id") != user_id:
                continue
            if status and alert_data.get("status") != status:
                continue
            filtered_alerts.append(alert_data)

        # Sort by created_at (newest first)
        filtered_alerts.sort(
            key=lambda x: x.get("created_at", datetime.min),
            reverse=True
        )

        # Apply pagination
        total_count = len(filtered_alerts)
        paginated_alerts = filtered_alerts[offset:offset + limit]

        # Convert to Alert objects
        alerts = [Alert(**alert) for alert in paginated_alerts]

        return AlertResponse(
            success=True,
            message=f"Found {len(alerts)} alerts (total: {total_count})",
            alerts=alerts,
            count=total_count
        )

    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str):
    """Get a specific alert by ID"""
    try:
        if alert_id not in ALERTS_DB:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert_data = ALERTS_DB[alert_id]
        return AlertResponse(
            success=True,
            message="Alert retrieved successfully",
            alert=Alert(**alert_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: str, update: AlertUpdate):
    """Update an existing alert"""
    try:
        if alert_id not in ALERTS_DB:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Update only provided fields
        alert_data = ALERTS_DB[alert_id]
        update_dict = update.dict(exclude_unset=True)

        for field, value in update_dict.items():
            if value is not None:
                alert_data[field] = value

        # Update timestamp
        alert_data["updated_at"] = datetime.now()

        logger.info(f"Alert updated: {alert_id}")

        return AlertResponse(
            success=True,
            message="Alert updated successfully",
            alert=Alert(**alert_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}", response_model=AlertResponse)
async def delete_alert(alert_id: str, decrement_usage: bool = Query(False)):
    """Delete an alert"""
    try:
        if alert_id not in ALERTS_DB:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert_data = ALERTS_DB.pop(alert_id)

        # Optionally decrement usage count
        if decrement_usage:
            # This would need to be implemented in alert_tracking
            logger.info("Note: Decrementing usage count not implemented yet")

        logger.info(f"Alert deleted: {alert_id}")

        return AlertResponse(
            success=True,
            message="Alert deleted successfully",
            alert=Alert(**alert_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/", response_model=AlertResponse)
async def delete_all_alerts(
    user_id: str = Query(..., description="User ID to delete alerts for"),
    confirm: bool = Query(False, description="Confirm deletion")
):
    """Delete all alerts for a user"""
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Set confirm=true to delete all alerts"
            )

        # Find and delete alerts for the user
        deleted_count = 0
        alerts_to_delete = []

        for alert_id, alert_data in ALERTS_DB.items():
            if alert_data.get("user_id") == user_id:
                alerts_to_delete.append(alert_id)

        for alert_id in alerts_to_delete:
            ALERTS_DB.pop(alert_id)
            deleted_count += 1

        logger.info(f"Deleted {deleted_count} alerts for user {user_id}")

        return AlertResponse(
            success=True,
            message=f"Deleted {deleted_count} alerts",
            count=deleted_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset-usage/{user_id}")
async def reset_alert_usage(user_id: str):
    """Reset alert usage count for a user (testing only)"""
    try:
        from .alert_tracking import USER_DATA

        if user_id in USER_DATA:
            USER_DATA[user_id]["alerts_used"] = 0
            USER_DATA[user_id]["incidents_processed"] = set()
            logger.info(f"Reset alert usage for user {user_id}")

            return {
                "success": True,
                "message": f"Alert usage reset for user {user_id}",
                "alerts_used": 0
            }
        else:
            return {
                "success": True,
                "message": "User not found, but will start fresh",
                "alerts_used": 0
            }

    except Exception as e:
        logger.error(f"Error resetting usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{user_id}")
async def get_alert_stats(user_id: str):
    """Get alert statistics for a user"""
    try:
        from .alert_tracking import get_alert_usage

        # Get usage data
        usage_data = await get_alert_usage(user_id)

        # Count alerts by status
        stats = {
            "total": 0,
            "active": 0,
            "resolved": 0,
            "acknowledged": 0,
            "by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }

        for alert_id, alert_data in ALERTS_DB.items():
            if alert_data.get("user_id") == user_id:
                stats["total"] += 1
                status = alert_data.get("status", "active")
                stats[status] = stats.get(status, 0) + 1

                severity = alert_data.get("severity", "medium")
                if severity in stats["by_severity"]:
                    stats["by_severity"][severity] += 1

        return {
            "success": True,
            "user_id": user_id,
            "usage": {
                "alerts_used": usage_data.alerts_used,
                "alerts_limit": usage_data.alerts_limit,
                "alerts_remaining": usage_data.alerts_remaining,
                "account_tier": usage_data.account_tier,
                "is_limit_reached": usage_data.is_limit_reached
            },
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
