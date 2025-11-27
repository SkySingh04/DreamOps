"""Incident management API endpoints for DreamOps."""

import json
import uuid
from datetime import UTC, datetime
from io import BytesIO

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.oncall_agent.api.schemas import (
    AIAnalysis,
    Incident,
    IncidentAction,
    IncidentCreate,
    IncidentList,
    IncidentStatus,
    IncidentUpdate,
    Severity,
    SuccessResponse,
)
from src.oncall_agent.services.incident_service import (
    AnalysisService,
    IncidentService,
    ReportService,
)
from src.oncall_agent.services.slack_notifier import get_slack_notifier
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/incidents", tags=["incidents"])


def create_mock_incident(data: IncidentCreate) -> Incident:
    """Create a mock incident."""
    incident_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    incident = Incident(
        id=incident_id,
        title=data.title,
        description=data.description,
        severity=data.severity,
        status=IncidentStatus.TRIGGERED,
        service_name=data.service_name,
        alert_source=data.alert_source,
        created_at=now,
        metadata=data.metadata,
        timeline=[{
            "timestamp": now.isoformat(),
            "event": "incident_created",
            "description": f"Incident created from {data.alert_source}"
        }]
    )

    # Add mock AI analysis for high/critical incidents
    if data.severity in [Severity.HIGH, Severity.CRITICAL]:
        incident.ai_analysis = AIAnalysis(
            summary="Service experiencing high error rate and latency spikes",
            root_cause="Database connection pool exhausted due to slow queries",
            impact_assessment="User-facing API degraded, affecting checkout flow",
            recommended_actions=[
                {
                    "action": "restart_service",
                    "reason": "Clear stuck connections",
                    "priority": "high"
                },
                {
                    "action": "scale_database",
                    "reason": "Increase connection pool size",
                    "priority": "medium"
                }
            ],
            confidence_score=0.85,
            related_incidents=["inc-123", "inc-456"],
            knowledge_base_references=["kb-001", "kb-002"]
        )

    return incident


@router.post("/", response_model=Incident, status_code=201)
async def create_incident(
    incident_data: IncidentCreate,
    background_tasks: BackgroundTasks
) -> Incident:
    """Create a new incident."""
    try:
        # Create incident
        incident = create_mock_incident(incident_data)
        await IncidentService.create(incident)

        logger.info(f"Created incident {incident.id}: {incident.title}")

        # Trigger AI analysis in background for high/critical incidents
        if incident.severity in [Severity.HIGH, Severity.CRITICAL]:
            background_tasks.add_task(
                trigger_ai_analysis,
                incident.id
            )

        return incident
    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def trigger_ai_analysis(incident_id: str):
    """Trigger AI analysis for an incident (mock)."""
    logger.info(f"Triggering AI analysis for incident {incident_id}")
    # In real implementation, this would call the OncallAgent


@router.get("/", response_model=IncidentList)
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: IncidentStatus | None = None,
    severity: Severity | None = None,
    service: str | None = None,
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|severity)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
) -> IncidentList:
    """List incidents with filtering and pagination."""
    try:
        # Get incidents from database
        incidents, total = await IncidentService.list(
            page=page,
            page_size=page_size,
            status=status,
            severity=severity,
            service=service,
            sort_by=sort_by,
            sort_order=sort_order
        )

        has_next = (page * page_size) < total

        return IncidentList(
            incidents=incidents,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next
        )
    except Exception as e:
        logger.error(f"Error listing incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{incident_id}", response_model=Incident)
async def get_incident(
    incident_id: str = Path(..., description="Incident ID")
) -> Incident:
    """Get incident details."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident


@router.patch("/{incident_id}", response_model=Incident)
async def update_incident(
    incident_id: str = Path(..., description="Incident ID"),
    update_data: IncidentUpdate = ...
) -> Incident:
    """Update incident details."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    now = datetime.now(UTC)

    # Update fields
    if update_data.status is not None:
        old_status = incident.status
        incident.status = update_data.status
        incident.timeline.append({
            "timestamp": now.isoformat(),
            "event": "status_changed",
            "description": f"Status changed from {old_status} to {update_data.status}",
            "user": update_data.assignee or "system"
        })

        if update_data.status == IncidentStatus.RESOLVED:
            incident.resolved_at = now

    if update_data.assignee is not None:
        incident.assignee = update_data.assignee
        incident.timeline.append({
            "timestamp": now.isoformat(),
            "event": "assigned",
            "description": f"Incident assigned to {update_data.assignee}"
        })

    if update_data.notes is not None:
        incident.timeline.append({
            "timestamp": now.isoformat(),
            "event": "note_added",
            "description": update_data.notes,
            "user": update_data.assignee or "system"
        })

    if update_data.resolution is not None:
        incident.resolution = update_data.resolution

    incident.updated_at = now

    # Persist to database
    await IncidentService.update(incident)

    logger.info(f"Updated incident {incident_id}")
    return incident


@router.post("/{incident_id}/actions", response_model=SuccessResponse)
async def execute_action(
    incident_id: str = Path(..., description="Incident ID"),
    action: IncidentAction = ...,
    background_tasks: BackgroundTasks = ...
) -> SuccessResponse:
    """Execute an action on an incident."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Add action to incident
    incident.actions_taken.append(action)
    incident.timeline.append({
        "timestamp": action.timestamp.isoformat(),
        "event": "action_executed",
        "description": f"Executed action: {action.action_type.value}",
        "automated": action.automated,
        "user": action.user or "system"
    })

    # Persist to database
    await IncidentService.update(incident)

    # Mock action execution
    background_tasks.add_task(
        execute_action_async,
        incident_id,
        action
    )

    logger.info(f"Executing action {action.action_type} on incident {incident_id}")

    return SuccessResponse(
        success=True,
        message=f"Action {action.action_type.value} queued for execution",
        data={"action_id": str(uuid.uuid4())}
    )


async def execute_action_async(incident_id: str, action: IncidentAction):
    """Execute action asynchronously (mock)."""
    logger.info(f"Executing {action.action_type} for incident {incident_id}")
    # In real implementation, this would call the appropriate integration


@router.get("/{incident_id}/timeline")
async def get_incident_timeline(
    incident_id: str = Path(..., description="Incident ID")
) -> JSONResponse:
    """Get incident timeline."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return JSONResponse(content={
        "incident_id": incident_id,
        "timeline": incident.timeline
    })


@router.get("/{incident_id}/related")
async def get_related_incidents(
    incident_id: str = Path(..., description="Incident ID"),
    limit: int = Query(5, ge=1, le=20)
) -> JSONResponse:
    """Get related incidents."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Get related incidents by service name from database
    all_incidents, _ = await IncidentService.list(
        page=1,
        page_size=limit + 1,  # +1 to exclude current incident
        service=incident.service_name
    )

    related = []
    for i, inc in enumerate(all_incidents):
        if inc.id != incident_id:
            related.append({
                "id": inc.id,
                "title": inc.title,
                "severity": inc.severity.value if hasattr(inc.severity, 'value') else str(inc.severity),
                "status": inc.status.value if hasattr(inc.status, 'value') else str(inc.status),
                "created_at": inc.created_at.isoformat(),
                "similarity_score": 0.85 - (i * 0.1)  # Mock similarity
            })
            if len(related) >= limit:
                break

    return JSONResponse(content={
        "incident_id": incident_id,
        "related_incidents": related
    })


@router.get("/{incident_id}/analysis")
async def get_incident_analysis(
    incident_id: str = Path(..., description="Incident ID")
) -> JSONResponse:
    """Get detailed AI analysis for an incident."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check if we have analysis data
    analysis = await AnalysisService.get(incident_id)
    if analysis:
        return JSONResponse(content=analysis)

    # Return placeholder if no analysis yet
    return JSONResponse(content={
        "incident_id": incident_id,
        "status": "pending",
        "message": "Analysis is being processed"
    })


@router.post("/{incident_id}/acknowledge", response_model=SuccessResponse)
async def acknowledge_incident(
    incident_id: str = Path(..., description="Incident ID"),
    user: str = Query(..., description="User acknowledging the incident")
) -> SuccessResponse:
    """Acknowledge an incident."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status != IncidentStatus.TRIGGERED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot acknowledge incident in {incident.status} status"
        )

    incident.status = IncidentStatus.ACKNOWLEDGED
    incident.assignee = user
    incident.timeline.append({
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "acknowledged",
        "description": f"Incident acknowledged by {user}",
        "user": user
    })

    # Persist to database
    await IncidentService.update(incident)

    logger.info(f"Incident {incident_id} acknowledged by {user}")

    return SuccessResponse(
        success=True,
        message="Incident acknowledged successfully"
    )


@router.post("/{incident_id}/resolve", response_model=SuccessResponse)
async def resolve_incident(
    incident_id: str = Path(..., description="Incident ID"),
    resolution: str = Query(..., description="Resolution description"),
    user: str = Query(..., description="User resolving the incident"),
    background_tasks: BackgroundTasks = ...
) -> SuccessResponse:
    """Resolve an incident."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if incident.status == IncidentStatus.RESOLVED:
        raise HTTPException(
            status_code=400,
            detail="Incident is already resolved"
        )

    now = datetime.now(UTC)
    incident.status = IncidentStatus.RESOLVED
    incident.resolution = resolution
    incident.resolved_at = now
    incident.timeline.append({
        "timestamp": now.isoformat(),
        "event": "resolved",
        "description": f"Incident resolved: {resolution}",
        "user": user
    })

    # Persist to database
    await IncidentService.update(incident)

    # Auto-generate incident report in background
    background_tasks.add_task(generate_resolution_report, incident_id)

    logger.info(f"Incident {incident_id} resolved by {user}")

    return SuccessResponse(
        success=True,
        message="Incident resolved successfully"
    )


async def generate_resolution_report(incident_id: str):
    """Generate resolution report in background."""
    try:
        await ReportService.generate_and_save(incident_id)
        logger.info(f"Auto-generated resolution report for incident {incident_id}")
    except Exception as e:
        logger.error(f"Failed to generate resolution report for {incident_id}: {e}")


@router.post("/{incident_id}/share/slack")
async def share_incident_to_slack(
    incident_id: str = Path(..., description="Incident ID")
) -> JSONResponse:
    """Share incident analysis to Slack."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    analysis = await AnalysisService.get(incident_id) or {}

    # Get analysis text
    analysis_text = ""
    if analysis:
        analysis_text = analysis.get("analysis", "")
    elif incident.ai_analysis:
        analysis_text = f"**Summary:** {incident.ai_analysis.summary}\n\n"
        if incident.ai_analysis.root_cause:
            analysis_text += f"**Root Cause:** {incident.ai_analysis.root_cause}\n\n"
        if incident.ai_analysis.impact_assessment:
            analysis_text += f"**Impact:** {incident.ai_analysis.impact_assessment}\n\n"
        if incident.ai_analysis.recommended_actions:
            analysis_text += "**Recommended Actions:**\n"
            for action in incident.ai_analysis.recommended_actions:
                if isinstance(action, dict):
                    analysis_text += f"- {action.get('action', 'Unknown')}: {action.get('reason', '')}\n"
                else:
                    analysis_text += f"- {action}\n"

    if not analysis_text:
        analysis_text = f"Incident: {incident.title}\n\nDescription: {incident.description or 'No description available'}"

    # Post to Slack
    slack_notifier = get_slack_notifier()
    if not slack_notifier.enabled:
        raise HTTPException(status_code=400, detail="Slack integration not configured")

    severity = incident.severity.value if hasattr(incident.severity, 'value') else str(incident.severity)
    result = await slack_notifier.post_incident_analysis(
        incident_id=incident.id,
        title=incident.title,
        severity=severity,
        analysis=analysis_text
    )

    if result.get("success"):
        return JSONResponse(content={
            "success": True,
            "message": "Incident shared to Slack",
            "thread_ts": result.get("thread_ts")
        })
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to post to Slack"))


@router.get("/{incident_id}/report/json")
async def download_incident_report_json(
    incident_id: str = Path(..., description="Incident ID")
) -> StreamingResponse:
    """Download incident report as JSON."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Try to get pre-generated report first (for resolved incidents)
    saved_report = await ReportService.get_saved_report(incident_id)
    if saved_report:
        report = saved_report["json_report"]
        logger.info(f"Using pre-generated JSON report for incident {incident_id}")
    else:
        # Generate on-the-fly for non-resolved incidents
        analysis = await AnalysisService.get(incident_id) or {}
        report = {
            "report_generated_at": datetime.now(UTC).isoformat(),
            "report_type": "incident_analysis",
            "incident": {
                "id": incident.id,
                "title": incident.title,
                "description": incident.description,
                "severity": incident.severity.value if hasattr(incident.severity, 'value') else str(incident.severity),
                "status": incident.status.value if hasattr(incident.status, 'value') else str(incident.status),
                "service_name": incident.service_name,
                "alert_source": incident.alert_source,
                "assignee": incident.assignee,
                "created_at": incident.created_at.isoformat() if incident.created_at else None,
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "resolution": incident.resolution,
            },
            "ai_analysis": analysis if analysis else (
                incident.ai_analysis.model_dump() if incident.ai_analysis else None
            ),
            "timeline": incident.timeline,
            "actions_taken": [
                {
                    "action_type": a.action_type.value if hasattr(a.action_type, 'value') else str(a.action_type),
                    "description": a.description,
                    "automated": a.automated,
                    "user": a.user,
                    "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                    "result": a.result
                }
                for a in incident.actions_taken
            ],
            "metadata": incident.metadata
        }

    # Create JSON file
    json_content = json.dumps(report, indent=2, default=str)
    buffer = BytesIO(json_content.encode('utf-8'))

    filename = f"incident-report-{incident_id[:8]}-{datetime.now(UTC).strftime('%Y%m%d')}.json"

    return StreamingResponse(
        buffer,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/{incident_id}/report/markdown")
async def download_incident_report_markdown(
    incident_id: str = Path(..., description="Incident ID")
) -> StreamingResponse:
    """Download incident report as Markdown (for PDF conversion)."""
    incident = await IncidentService.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Try to get pre-generated report first (for resolved incidents)
    saved_report = await ReportService.get_saved_report(incident_id)
    if saved_report:
        md_content = saved_report["markdown_report"]
        logger.info(f"Using pre-generated Markdown report for incident {incident_id}")
    else:
        # Generate on-the-fly for non-resolved incidents
        analysis = await AnalysisService.get(incident_id) or {}

        # Build Markdown report
        md_lines = [
            f"# Incident Report: {incident.title}",
            "",
            f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| **ID** | `{incident.id}` |",
            f"| **Severity** | {incident.severity.value if hasattr(incident.severity, 'value') else str(incident.severity)} |",
            f"| **Status** | {incident.status.value if hasattr(incident.status, 'value') else str(incident.status)} |",
            f"| **Service** | {incident.service_name} |",
            f"| **Alert Source** | {incident.alert_source} |",
            f"| **Assignee** | {incident.assignee or 'Unassigned'} |",
            f"| **Created** | {incident.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if incident.created_at else 'N/A'} |",
            f"| **Resolved** | {incident.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC') if incident.resolved_at else 'N/A'} |",
            "",
            "## Description",
            "",
            incident.description or "No description provided.",
            "",
        ]

        # Add AI Analysis section
        ai_data = analysis if analysis else (incident.ai_analysis.model_dump() if incident.ai_analysis else None)
        if ai_data:
            md_lines.extend([
                "## AI Analysis",
                "",
            ])

            # Handle different analysis formats
            if isinstance(ai_data, dict):
                if 'analysis' in ai_data:
                    md_lines.append(ai_data['analysis'])
                else:
                    if ai_data.get('summary'):
                        md_lines.extend([f"### Summary", "", ai_data['summary'], ""])
                    if ai_data.get('root_cause'):
                        md_lines.extend([f"### Root Cause", "", ai_data['root_cause'], ""])
                    if ai_data.get('impact_assessment'):
                        md_lines.extend([f"### Impact Assessment", "", ai_data['impact_assessment'], ""])
                    if ai_data.get('recommended_actions'):
                        md_lines.extend([f"### Recommended Actions", ""])
                        for i, action in enumerate(ai_data['recommended_actions'], 1):
                            if isinstance(action, dict):
                                md_lines.append(f"{i}. **{action.get('action', 'Unknown')}**: {action.get('reason', '')}")
                            else:
                                md_lines.append(f"{i}. {action}")
                        md_lines.append("")
            md_lines.append("")

        # Add Timeline section
        if incident.timeline:
            md_lines.extend([
                "## Timeline",
                "",
            ])
            for event in incident.timeline:
                timestamp = event.get('timestamp', 'N/A')
                event_type = event.get('event', 'unknown')
                description = event.get('description', '')
                user = event.get('user', 'system')
                md_lines.append(f"- **{timestamp}** - `{event_type}` - {description} (by {user})")
            md_lines.append("")

        # Add Actions Taken section
        if incident.actions_taken:
            md_lines.extend([
                "## Actions Taken",
                "",
            ])
            for action in incident.actions_taken:
                md_lines.extend([
                    f"### {action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type)}",
                    f"- **Description:** {action.description}",
                    f"- **Automated:** {'Yes' if action.automated else 'No'}",
                    f"- **User:** {action.user or 'System'}",
                    f"- **Result:** {action.result or 'N/A'}",
                    "",
                ])

        # Add Resolution section
        if incident.resolution:
            md_lines.extend([
                "## Resolution",
                "",
                incident.resolution,
                "",
            ])

        md_lines.extend([
            "---",
            "",
            "*Report generated by DreamOps AI Incident Management Platform*",
        ])

        # Create Markdown content
        md_content = "\n".join(md_lines)

    buffer = BytesIO(md_content.encode('utf-8'))

    filename = f"incident-report-{incident_id[:8]}-{datetime.now(UTC).strftime('%Y%m%d')}.md"

    return StreamingResponse(
        buffer,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# Initialize with some mock data
def init_mock_data():
    """Initialize some mock incidents."""
    mock_incidents = [
        IncidentCreate(
            title="API Gateway High Error Rate",
            description="Error rate exceeded 5% threshold",
            severity=Severity.HIGH,
            service_name="api-gateway",
            alert_source="prometheus"
        ),
        IncidentCreate(
            title="Database Connection Pool Exhausted",
            description="No available connections in pool",
            severity=Severity.CRITICAL,
            service_name="user-service",
            alert_source="datadog"
        ),
        IncidentCreate(
            title="Disk Space Warning",
            description="Disk usage at 85% on node-3",
            severity=Severity.MEDIUM,
            service_name="infrastructure",
            alert_source="nagios"
        ),
    ]

    for incident_data in mock_incidents:
        incident = create_mock_incident(incident_data)
        INCIDENTS_DB[incident.id] = incident


# Note: Mock data initialization removed. Incidents are created via webhooks only.
# To add mock incidents, call init_mock_data() manually or via /api/v1/incidents POST endpoint.
