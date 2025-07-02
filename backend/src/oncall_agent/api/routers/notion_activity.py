"""API endpoints for tracking Notion activity."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.oncall_agent.services.notion_activity_tracker import notion_tracker
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/notion-activity", tags=["notion-activity"])


@router.get("/summary")
async def get_notion_activity_summary() -> JSONResponse:
    """Get a summary of all Notion operations performed by the agent."""
    try:
        summary = await notion_tracker.get_activity_summary()

        return JSONResponse(content={
            "success": True,
            "data": summary
        })

    except Exception as e:
        logger.error(f"Error getting Notion activity summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-reads")
async def get_recent_reads(
    limit: int = Query(10, description="Number of recent reads to return", ge=1, le=100)
) -> JSONResponse:
    """Get the most recent Notion page reads."""
    try:
        reads = await notion_tracker.get_recent_reads(limit)

        return JSONResponse(content={
            "success": True,
            "count": len(reads),
            "reads": reads
        })

    except Exception as e:
        logger.error(f"Error getting recent reads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent-writes")
async def get_recent_writes(
    limit: int = Query(10, description="Number of recent writes to return", ge=1, le=100)
) -> JSONResponse:
    """Get the most recent Notion page writes."""
    try:
        writes = await notion_tracker.get_recent_writes(limit)

        return JSONResponse(content={
            "success": True,
            "count": len(writes),
            "writes": writes
        })

    except Exception as e:
        logger.error(f"Error getting recent writes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify-page-read/{page_id}")
async def verify_page_read(page_id: str) -> JSONResponse:
    """Verify if a specific Notion page has been read by the agent."""
    try:
        verification = await notion_tracker.verify_page_read(page_id)

        return JSONResponse(content={
            "success": True,
            "data": verification
        })

    except Exception as e:
        logger.error(f"Error verifying page read: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/page-history/{page_id}")
async def get_page_history(page_id: str) -> JSONResponse:
    """Get all activities related to a specific Notion page."""
    try:
        history = await notion_tracker.get_page_history(page_id)

        return JSONResponse(content={
            "success": True,
            "page_id": page_id,
            "activity_count": len(history),
            "activities": history
        })

    except Exception as e:
        logger.error(f"Error getting page history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-history")
async def clear_activity_history() -> JSONResponse:
    """Clear all Notion activity history (admin only)."""
    try:
        await notion_tracker.clear_history()

        return JSONResponse(content={
            "success": True,
            "message": "Notion activity history cleared"
        })

    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live-status")
async def get_live_status() -> JSONResponse:
    """Get live status of Notion operations."""
    try:
        summary = await notion_tracker.get_activity_summary()

        # Extract key metrics
        today = datetime.utcnow().date().isoformat()
        operations_today = 0
        for activity in summary.get("recent_activities", []):
            if activity.get("timestamp", "").startswith(today):
                operations_today += 1

        status = {
            "is_active": summary["last_activity"] is not None,
            "last_activity": summary["last_activity"],
            "operations_today": operations_today,
            "pages_read_total": summary["pages_read"],
            "pages_created_total": summary["pages_created"],
            "tracking_since": summary["tracked_since"]
        }

        return JSONResponse(content={
            "success": True,
            "status": status
        })

    except Exception as e:
        logger.error(f"Error getting live status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from datetime import datetime
