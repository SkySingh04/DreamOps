"""Incident management API endpoints for DreamOps."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query
from fastapi.responses import JSONResponse

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
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/incidents", tags=["incidents"])

# In-memory storage for demo - replace with database
INCIDENTS_DB: dict[str, Incident] = {}
ANALYSIS_DB: dict[str, dict] = {}  # Store full AI analysis


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
        INCIDENTS_DB[incident.id] = incident

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
        # Filter incidents
        filtered_incidents = list(INCIDENTS_DB.values())

        if status:
            filtered_incidents = [i for i in filtered_incidents if i.status == status]
        if severity:
            filtered_incidents = [i for i in filtered_incidents if i.severity == severity]
        if service:
            filtered_incidents = [i for i in filtered_incidents if i.service_name == service]

        # Sort incidents
        reverse = sort_order == "desc"
        if sort_by == "created_at":
            filtered_incidents.sort(key=lambda x: x.created_at, reverse=reverse)
        elif sort_by == "severity":
            severity_order = {
                Severity.CRITICAL: 0,
                Severity.HIGH: 1,
                Severity.MEDIUM: 2,
                Severity.LOW: 3,
                Severity.INFO: 4
            }
            filtered_incidents.sort(
                key=lambda x: severity_order[x.severity],
                reverse=not reverse  # Reverse logic for severity
            )

        # Paginate
        total = len(filtered_incidents)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        incidents = filtered_incidents[start_idx:end_idx]
        has_next = end_idx < total

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
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    return INCIDENTS_DB[incident_id]


@router.patch("/{incident_id}", response_model=Incident)
async def update_incident(
    incident_id: str = Path(..., description="Incident ID"),
    update_data: IncidentUpdate = ...
) -> Incident:
    """Update incident details."""
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = INCIDENTS_DB[incident_id]
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

    logger.info(f"Updated incident {incident_id}")
    return incident


@router.post("/{incident_id}/actions", response_model=SuccessResponse)
async def execute_action(
    incident_id: str = Path(..., description="Incident ID"),
    action: IncidentAction = ...,
    background_tasks: BackgroundTasks = ...
) -> SuccessResponse:
    """Execute an action on an incident."""
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = INCIDENTS_DB[incident_id]

    # Add action to incident
    incident.actions_taken.append(action)
    incident.timeline.append({
        "timestamp": action.timestamp.isoformat(),
        "event": "action_executed",
        "description": f"Executed action: {action.action_type.value}",
        "automated": action.automated,
        "user": action.user or "system"
    })

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
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = INCIDENTS_DB[incident_id]

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
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = INCIDENTS_DB[incident_id]

    # Mock related incidents
    related = []
    for i, inc in enumerate(INCIDENTS_DB.values()):
        if inc.id != incident_id and inc.service_name == incident.service_name:
            related.append({
                "id": inc.id,
                "title": inc.title,
                "severity": inc.severity,
                "status": inc.status,
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
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Check if we have analysis data
    if incident_id in ANALYSIS_DB:
        return JSONResponse(content=ANALYSIS_DB[incident_id])

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
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = INCIDENTS_DB[incident_id]

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

    logger.info(f"Incident {incident_id} acknowledged by {user}")

    return SuccessResponse(
        success=True,
        message="Incident acknowledged successfully"
    )


@router.post("/{incident_id}/resolve", response_model=SuccessResponse)
async def resolve_incident(
    incident_id: str = Path(..., description="Incident ID"),
    resolution: str = Query(..., description="Resolution description"),
    user: str = Query(..., description="User resolving the incident")
) -> SuccessResponse:
    """Resolve an incident."""
    if incident_id not in INCIDENTS_DB:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = INCIDENTS_DB[incident_id]

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

    logger.info(f"Incident {incident_id} resolved by {user}")

    return SuccessResponse(
        success=True,
        message="Incident resolved successfully"
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


# Initialize mock data on module load
init_mock_data()
