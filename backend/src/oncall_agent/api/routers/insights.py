"""API endpoints for Notion insights and analysis."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.oncall_agent.services.notion_insights import get_insights_service
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/analysis")
async def get_incident_analysis(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=90)
) -> JSONResponse:
    """Get incident analysis and insights from Notion."""
    try:
        service = await get_insights_service()
        analysis = await service.analyze_incidents()

        return JSONResponse(content={
            "success": True,
            "data": analysis
        })

    except Exception as e:
        logger.error(f"Error getting incident analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_incident_report() -> JSONResponse:
    """Get a formatted incident report."""
    try:
        service = await get_insights_service()
        report = await service.generate_summary_report()

        return JSONResponse(content={
            "success": True,
            "report": report,
            "format": "markdown"
        })

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def get_recommendations() -> JSONResponse:
    """Get actionable recommendations based on incident patterns."""
    try:
        service = await get_insights_service()
        analysis = await service.analyze_incidents()

        # Prioritize recommendations
        recommendations = []
        for i, rec in enumerate(analysis.get("recommendations", []), 1):
            priority = "high" if "Urgent" in rec else "medium"
            recommendations.append({
                "id": i,
                "recommendation": rec,
                "priority": priority
            })

        return JSONResponse(content={
            "success": True,
            "total_incidents_analyzed": analysis.get("total_incidents", 0),
            "recommendations": recommendations
        })

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def get_incident_trends() -> JSONResponse:
    """Get incident trends over time."""
    try:
        service = await get_insights_service()
        incidents = await service.get_recent_incidents(days=30)

        # Group by day
        by_day = {}
        for incident in incidents:
            created_at = incident.get("created_at", "")
            if created_at:
                day = created_at.split("T")[0]
                by_day[day] = by_day.get(day, 0) + 1

        # Convert to sorted list
        trend_data = [
            {"date": day, "count": count}
            for day, count in sorted(by_day.items())
        ]

        return JSONResponse(content={
            "success": True,
            "data": trend_data,
            "total_days": len(trend_data),
            "total_incidents": sum(d["count"] for d in trend_data)
        })

    except Exception as e:
        logger.error(f"Error getting trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-chaos")
async def analyze_chaos_results() -> JSONResponse:
    """Analyze results after chaos engineering session."""
    try:
        service = await get_insights_service()

        # Get incidents from the last hour
        recent_incidents = await service.get_recent_incidents(days=1)

        # Filter to very recent (last hour)
        from datetime import datetime, timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        chaos_incidents = []
        for inc in recent_incidents:
            created_at_str = inc.get("created_at", "")
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_at.replace(tzinfo=None) > one_hour_ago:
                    chaos_incidents.append(inc)

        # Analyze chaos results
        analysis = {
            "chaos_incidents_created": len(chaos_incidents),
            "services_affected": list(set(inc["service_name"] for inc in chaos_incidents)),
            "issue_types": list(set(inc["incident_type"] for inc in chaos_incidents)),
            "all_documented": len(chaos_incidents) > 0,
            "incidents": chaos_incidents
        }

        # Generate insights
        insights = []
        if len(chaos_incidents) == 0:
            insights.append("No incidents detected from recent chaos engineering")
        else:
            insights.append(f"Successfully documented {len(chaos_incidents)} incidents from chaos engineering")

            # Check for specific issues
            issue_types = [inc["incident_type"] for inc in chaos_incidents]
            if "oom" in issue_types:
                insights.append("OOM issues detected - memory limits need review")
            if "image_pull" in issue_types:
                insights.append("Image pull failures detected - check registry access")
            if "crash_loop" in issue_types:
                insights.append("Application crashes detected - review logs and health checks")

        analysis["insights"] = insights

        return JSONResponse(content={
            "success": True,
            "data": analysis
        })

    except Exception as e:
        logger.error(f"Error analyzing chaos results: {e}")
        raise HTTPException(status_code=500, detail=str(e))
