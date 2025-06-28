"""AI Agent control and monitoring endpoints."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import JSONResponse

from src.oncall_agent.agent import OncallAgent
from src.oncall_agent.api.schemas import (
    ActionHistory,
    ActionRiskAssessment,
    ActionType,
    AgentResponse,
    AgentStatus,
    AgentTriggerRequest,
    AIAgentConfig,
    AIAgentConfigUpdate,
    AIAnalysis,
    AIMode,
    ApprovalRequest,
    ConfidenceFactors,
    ConfidenceScore,
    DryRunResult,
    IncidentAction,
    NotificationPreferences,
    RiskLevel,
    SafetyConfig,
    SuccessResponse,
)
from src.oncall_agent.approval_manager import approval_manager
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["ai-agent"])

# Global agent instance (shared with main API)
agent_instance: OncallAgent | None = None
enhanced_agent_instance = None  # Enhanced agent with execution capabilities

# Agent metrics storage
AGENT_METRICS = {
    "incidents_processed": 0,
    "total_response_time_ms": 0,
    "errors": [],
    "last_analysis": None,
    "start_time": datetime.now(UTC)
}

# Default risk matrix for AI actions
DEFAULT_RISK_MATRIX = {
    "low": [
        "Read metrics and logs",
        "Query monitoring systems",
        "Generate reports",
        "Send notifications",
        "Update incident status",
    ],
    "medium": [
        "Restart services",
        "Scale deployments",
        "Clear caches",
        "Rotate credentials",
        "Update configurations",
    ],
    "high": [
        "Delete resources",
        "Modify production data",
        "Change security settings",
        "Perform database operations",
        "Execute custom scripts",
    ],
}

# In-memory configuration storage (in production, this would be database-backed)
AGENT_CONFIG = AIAgentConfig(
    mode=AIMode.YOLO,
    confidence_threshold=70,
    risk_matrix=DEFAULT_RISK_MATRIX,
    auto_execute_enabled=True,
    approval_required_for=[RiskLevel.MEDIUM, RiskLevel.HIGH],
    notification_preferences=NotificationPreferences(
        slack_enabled=True,
        email_enabled=False,
        channels=[],
    ),
)

# Safety configuration
SAFETY_CONFIG = SafetyConfig(
    dry_run_mode=False,
    confidence_threshold=0.8,
    risk_tolerance=RiskLevel.MEDIUM,
    auto_execute_permissions={
        "read_logs": True,
        "check_status": True,
        "restart_pod": False,
        "scale_deployment": False,
        "delete_resource": False,
        "modify_database": False,
    },
    mandatory_approval_actions=["delete_resource", "modify_database", "change_security"],
    emergency_stop_active=False,
)

# In-memory storage for safety features
# Note: APPROVAL_QUEUE is now managed by approval_manager
ACTION_HISTORY: list[ActionHistory] = []
CONFIDENCE_HISTORY: list[tuple[datetime, float]] = []


# Risk Assessment Matrix
RISK_MATRIX = {
    "read_operations": {
        "view_logs": RiskLevel.LOW,
        "check_status": RiskLevel.LOW,
        "gather_metrics": RiskLevel.LOW,
        "list_resources": RiskLevel.LOW,
    },
    "operational_changes": {
        "restart_pod": RiskLevel.MEDIUM,
        "restart_service": RiskLevel.MEDIUM,
        "scale_deployment": RiskLevel.MEDIUM,
        "update_config": RiskLevel.MEDIUM,
        "clear_cache": RiskLevel.MEDIUM,
        "rotate_credentials": RiskLevel.MEDIUM,
    },
    "destructive_operations": {
        "delete_resource": RiskLevel.HIGH,
        "modify_database": RiskLevel.HIGH,
        "change_security": RiskLevel.HIGH,
        "network_changes": RiskLevel.HIGH,
        "system_restart": RiskLevel.HIGH,
    },
}


class ConfidenceScorer:
    """Calculate confidence scores for AI actions."""

    @staticmethod
    def calculate_confidence(incident_data: dict, context_quality: float = 0.8) -> ConfidenceScore:
        """Calculate overall confidence score."""

        # Mock confidence calculation (in production, use ML models)
        factors = ConfidenceFactors(
            pattern_recognition=min(1.0, len(incident_data.get("symptoms", [])) * 0.2),
            historical_success=0.75,  # Mock historical success rate
            context_quality=context_quality,
            resource_availability=0.9,  # Mock resource availability
            time_sensitivity=0.8 if incident_data.get("severity") == "high" else 0.6,
        )

        # Weighted calculation
        overall_confidence = (
            factors.pattern_recognition * 0.30 +
            factors.historical_success * 0.25 +
            factors.context_quality * 0.20 +
            factors.resource_availability * 0.15 +
            factors.time_sensitivity * 0.10
        )

        # Determine recommendation
        if overall_confidence >= 0.8:
            recommendation = "High confidence - safe for auto-execution"
        elif overall_confidence >= 0.6:
            recommendation = "Medium confidence - consider approval workflow"
        else:
            recommendation = "Low confidence - requires human intervention"

        threshold_met = overall_confidence >= SAFETY_CONFIG.confidence_threshold

        return ConfidenceScore(
            overall_confidence=overall_confidence,
            factor_breakdown=factors,
            recommendation=recommendation,
            threshold_met=threshold_met,
        )


class RiskAssessment:
    """Assess risk levels for actions."""

    @staticmethod
    def classify_action_risk(action_type: str, action_details: dict) -> ActionRiskAssessment:
        """Classify the risk level of an action."""

        # Find risk level in matrix
        risk_level = RiskLevel.MEDIUM  # Default
        for category, actions in RISK_MATRIX.items():
            if action_type in actions:
                risk_level = actions[action_type]
                break

        # Determine risk factors
        risk_factors = []
        if action_details.get("affects_production", False):
            risk_factors.append("affects_production")
        if action_details.get("data_modification", False):
            risk_factors.append("data_modification")
        if action_details.get("security_impact", False):
            risk_factors.append("security_impact")

        # Check permissions
        auto_execute_allowed = (
            SAFETY_CONFIG.auto_execute_permissions.get(action_type, False) and
            risk_level != RiskLevel.HIGH and
            not SAFETY_CONFIG.emergency_stop_active
        )

        requires_approval = (
            action_type in SAFETY_CONFIG.mandatory_approval_actions or
            risk_level == RiskLevel.HIGH or
            not auto_execute_allowed
        )

        return ActionRiskAssessment(
            action_type=action_type,
            risk_level=risk_level,
            risk_factors=risk_factors,
            auto_execute_allowed=auto_execute_allowed,
            requires_approval=requires_approval,
        )


class DryRunExecutor:
    """Execute dry run simulations."""

    @staticmethod
    def execute_dry_run(action_plan: list[dict]) -> list[DryRunResult]:
        """Simulate action execution without actually performing actions."""
        results = []

        for i, action in enumerate(action_plan):
            action_id = f"dryrun_{uuid.uuid4().hex[:8]}"
            action_type = action.get("type", "unknown")

            # Simulate execution logic
            would_execute = not SAFETY_CONFIG.emergency_stop_active

            # Generate realistic outcomes
            if action_type == "restart_pod":
                expected_outcome = f"Pod {action.get('target', 'unknown')} would be restarted"
                potential_risks = ["Brief service interruption", "Potential data loss in transit"]
                rollback_plan = "Monitor pod startup and rollback if health checks fail"
                estimated_duration = 60
            elif action_type == "scale_deployment":
                replicas = action.get("replicas", 3)
                expected_outcome = f"Deployment scaled to {replicas} replicas"
                potential_risks = ["Resource exhaustion", "Increased costs"]
                rollback_plan = "Scale back to original replica count"
                estimated_duration = 30
            else:
                expected_outcome = f"Would execute {action_type} action"
                potential_risks = ["Unknown side effects"]
                rollback_plan = "Manual intervention required"
                estimated_duration = 120

            result = DryRunResult(
                action_id=action_id,
                action_type=action_type,
                would_execute=would_execute,
                expected_outcome=expected_outcome,
                potential_risks=potential_risks,
                rollback_plan=rollback_plan,
                estimated_duration=estimated_duration,
                resource_impact={
                    "cpu_impact": "low",
                    "memory_impact": "medium",
                    "network_impact": "low",
                },
            )
            results.append(result)

        return results


class RollbackManager:
    """Manage action rollbacks."""

    @staticmethod
    def record_action(action_type: str, action_details: dict, original_state: dict) -> str:
        """Record an executed action for potential rollback."""
        action_id = f"action_{uuid.uuid4().hex[:8]}"

        action_record = ActionHistory(
            id=action_id,
            incident_id=action_details.get("incident_id", "unknown"),
            action_type=action_type,
            action_details=action_details,
            executed_at=datetime.now(UTC),
            original_state=original_state,
            rollback_available=action_type in ["restart_pod", "scale_deployment", "update_config"],
        )

        ACTION_HISTORY.append(action_record)
        return action_id

    @staticmethod
    def rollback_action(action_id: str) -> dict:
        """Rollback a specific action."""
        action = next((a for a in ACTION_HISTORY if a.id == action_id), None)

        if not action:
            return {"success": False, "error": "Action not found"}

        if not action.rollback_available:
            return {"success": False, "error": "Rollback not supported for this action"}

        if action.rollback_executed:
            return {"success": False, "error": "Action already rolled back"}

        # Simulate rollback logic
        if action.action_type == "restart_pod":
            rollback_result = "Pod rollback initiated"
        elif action.action_type == "scale_deployment":
            original_replicas = action.original_state.get("replicas", 1)
            rollback_result = f"Deployment scaled back to {original_replicas} replicas"
        else:
            rollback_result = "Configuration restored to original state"

        # Mark as rolled back
        action.rollback_executed = True
        action.rollback_at = datetime.now(UTC)

        return {
            "success": True,
            "message": "Action rolled back successfully",
            "details": rollback_result,
        }


async def get_agent() -> OncallAgent:
    """Get or create agent instance."""
    global agent_instance
    if not agent_instance:
        agent_instance = OncallAgent()
        await agent_instance.connect_integrations()
    return agent_instance


@router.get("/status", response_model=AgentStatus)
async def get_agent_status() -> AgentStatus:
    """Get AI agent system status."""
    try:
        agent = await get_agent()

        # Calculate metrics
        uptime = (datetime.now(UTC) - AGENT_METRICS["start_time"]).total_seconds()
        avg_response_time = (
            AGENT_METRICS["total_response_time_ms"] / AGENT_METRICS["incidents_processed"]
            if AGENT_METRICS["incidents_processed"] > 0 else 0
        )

        # Get active integrations
        active_integrations = []
        for name, integration in agent.mcp_integrations.items():
            if await integration.health_check():
                active_integrations.append(name)

        return AgentStatus(
            status="healthy" if not AGENT_METRICS["errors"] else "degraded",
            version="1.0.0",
            uptime_seconds=uptime,
            incidents_processed_today=AGENT_METRICS["incidents_processed"],
            average_response_time_ms=avg_response_time,
            queue_size=0,  # Mock for now
            active_integrations=active_integrations,
            last_error=AGENT_METRICS["errors"][-1] if AGENT_METRICS["errors"] else None
        )
    except Exception as e:
        logger.error(f"Error getting agent status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AgentResponse)
async def trigger_analysis(
    request: AgentTriggerRequest,
    background_tasks: BackgroundTasks
) -> AgentResponse:
    """Manually trigger AI analysis for an incident."""
    try:
        start_time = datetime.now(UTC)

        # Mock analysis for now
        analysis = AIAnalysis(
            summary="Service experiencing intermittent connectivity issues with database",
            root_cause="Network packet loss detected between service pods and database cluster",
            impact_assessment="Approximately 15% of API requests failing with timeout errors",
            recommended_actions=[
                {
                    "type": "immediate",
                    "action": "restart_network_pods",
                    "reason": "Reset network stack to clear potential buffer issues",
                    "estimated_impact": "2-3 minutes of additional downtime"
                },
                {
                    "type": "investigation",
                    "action": "check_network_policies",
                    "reason": "Verify no recent changes to network policies",
                    "estimated_impact": "none"
                },
                {
                    "type": "long_term",
                    "action": "implement_circuit_breaker",
                    "reason": "Prevent cascade failures during network issues",
                    "estimated_impact": "improved resilience"
                }
            ],
            confidence_score=0.82,
            related_incidents=["inc-789", "inc-790"],
            knowledge_base_references=["kb-net-001", "kb-timeout-002"]
        )

        # Calculate execution time
        execution_time = (datetime.now(UTC) - start_time).total_seconds() * 1000

        # Update metrics
        AGENT_METRICS["incidents_processed"] += 1
        AGENT_METRICS["total_response_time_ms"] += execution_time
        AGENT_METRICS["last_analysis"] = datetime.now(UTC)

        # Mock automated actions
        automated_actions = []
        if request.context.get("auto_remediate", False):
            automated_actions.append(IncidentAction(
                action_type=ActionType.RESTART_POD,
                parameters={"pod": "network-controller", "namespace": "kube-system"},
                automated=True,
                result={"status": "success", "message": "Pod restarted successfully"}
            ))

        response = AgentResponse(
            incident_id=request.incident_id,
            analysis=analysis,
            automated_actions=automated_actions,
            execution_time_ms=execution_time,
            tokens_used=1250  # Mock token count
        )

        # Trigger any automated actions in background
        if automated_actions:
            background_tasks.add_task(
                execute_automated_actions,
                request.incident_id,
                automated_actions
            )

        return response

    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        AGENT_METRICS["errors"].append(str(e))
        raise HTTPException(status_code=500, detail=str(e))


async def execute_automated_actions(incident_id: str, actions: list[IncidentAction]):
    """Execute automated actions (mock implementation)."""
    for action in actions:
        logger.info(f"Executing automated action {action.action_type} for incident {incident_id}")
        await asyncio.sleep(1)  # Simulate action execution


@router.get("/capabilities")
async def get_agent_capabilities() -> JSONResponse:
    """Get AI agent capabilities and supported actions."""
    try:
        agent = await get_agent()

        capabilities = {
            "analysis": {
                "root_cause_analysis": True,
                "impact_assessment": True,
                "pattern_recognition": True,
                "anomaly_detection": True,
                "predictive_analysis": False  # Coming soon
            },
            "supported_actions": [
                {
                    "type": ActionType.RESTART_POD.value,
                    "description": "Restart Kubernetes pods",
                    "automated": True
                },
                {
                    "type": ActionType.SCALE_DEPLOYMENT.value,
                    "description": "Scale Kubernetes deployments",
                    "automated": True
                },
                {
                    "type": ActionType.ROLLBACK.value,
                    "description": "Rollback deployments",
                    "automated": False,
                    "requires_approval": True
                },
                {
                    "type": ActionType.RUN_DIAGNOSTICS.value,
                    "description": "Run diagnostic commands",
                    "automated": True
                },
                {
                    "type": ActionType.CREATE_TICKET.value,
                    "description": "Create tracking tickets",
                    "automated": True
                }
            ],
            "integrations": {}
        }

        # Add integration capabilities
        for name, integration in agent.mcp_integrations.items():
            capabilities["integrations"][name] = {
                "connected": await integration.health_check(),
                "capabilities": await integration.get_capabilities()
            }

        return JSONResponse(content=capabilities)

    except Exception as e:
        logger.error(f"Error getting capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/knowledge-base")
async def search_knowledge_base(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=50)
) -> JSONResponse:
    """Search agent knowledge base."""
    try:
        # Mock knowledge base search
        results = []

        # Simulate different types of knowledge base entries
        kb_entries = [
            {
                "id": "kb-001",
                "title": "Handling Database Connection Pool Exhaustion",
                "type": "runbook",
                "relevance_score": 0.95
            },
            {
                "id": "kb-002",
                "title": "Kubernetes Pod CrashLoopBackOff Resolution",
                "type": "troubleshooting",
                "relevance_score": 0.87
            },
            {
                "id": "kb-003",
                "title": "Network Timeout Patterns and Solutions",
                "type": "pattern",
                "relevance_score": 0.82
            },
            {
                "id": "kb-004",
                "title": "Service Mesh Configuration Best Practices",
                "type": "best_practice",
                "relevance_score": 0.75
            }
        ]

        # Filter based on query (mock relevance)
        for entry in kb_entries[:limit]:
            if query.lower() in entry["title"].lower():
                entry["relevance_score"] = min(1.0, entry["relevance_score"] + 0.1)
            results.append(entry)

        # Sort by relevance
        results.sort(key=lambda x: x["relevance_score"], reverse=True)

        return JSONResponse(content={
            "query": query,
            "results": results[:limit],
            "total_results": len(results)
        })

    except Exception as e:
        logger.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-metrics")
async def get_learning_metrics() -> JSONResponse:
    """Get AI agent learning and improvement metrics."""
    try:
        # Mock learning metrics
        metrics = {
            "accuracy_metrics": {
                "root_cause_accuracy": 0.84,
                "action_success_rate": 0.91,
                "false_positive_rate": 0.06,
                "trend": "improving"
            },
            "learning_stats": {
                "patterns_learned": 156,
                "incidents_analyzed": AGENT_METRICS["incidents_processed"],
                "knowledge_base_size": 1024,
                "last_model_update": (datetime.now(UTC) - timedelta(days=3)).isoformat()
            },
            "performance_over_time": [
                {"date": (datetime.now(UTC) - timedelta(days=i)).date().isoformat(),
                 "accuracy": 0.80 + (i * 0.01),
                 "incidents": 20 + i}
                for i in range(7, -1, -1)
            ]
        }

        return JSONResponse(content=metrics)

    except Exception as e:
        logger.error(f"Error getting learning metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(
    incident_id: str = Query(..., description="Incident ID"),
    helpful: bool = Query(..., description="Was the analysis helpful?"),
    accuracy: int = Query(..., ge=1, le=5, description="Accuracy rating (1-5)"),
    comments: str | None = Query(None, description="Additional comments")
) -> SuccessResponse:
    """Submit feedback on AI analysis."""
    try:
        # Store feedback (mock for now)
        feedback_data = {
            "incident_id": incident_id,
            "helpful": helpful,
            "accuracy": accuracy,
            "comments": comments,
            "timestamp": datetime.now(UTC).isoformat()
        }

        logger.info(f"Received feedback for incident {incident_id}: {feedback_data}")

        return SuccessResponse(
            success=True,
            message="Feedback submitted successfully",
            data={"feedback_id": str(uuid.uuid4())}
        )

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", response_model=AIAgentConfig)
async def get_agent_config() -> AIAgentConfig:
    """Get current AI agent configuration."""
    try:
        return AGENT_CONFIG
    except Exception as e:
        logger.error(f"Error getting agent config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config", response_model=AIAgentConfig)
async def update_agent_config(config_update: AIAgentConfigUpdate) -> AIAgentConfig:
    """Update AI agent configuration."""
    try:
        global AGENT_CONFIG, enhanced_agent_instance

        # Update only provided fields
        update_data = config_update.model_dump(exclude_unset=True)

        # Create new config with updates
        current_config = AGENT_CONFIG.model_dump()
        current_config.update(update_data)

        # Validate and create new config
        AGENT_CONFIG = AIAgentConfig(**current_config)

        # If mode changed, reset agent instances to use new mode
        if "mode" in update_data:
            # Reset webhook agent trigger to use new mode
            from src.oncall_agent.api import webhooks
            webhooks.agent_trigger = None

            # Reset enhanced agent instance
            enhanced_agent_instance = None

            logger.info(f"AI mode changed to {AGENT_CONFIG.mode.value}, agent instances will be recreated")

        logger.info(f"Agent configuration updated: {update_data}")
        return AGENT_CONFIG

    except Exception as e:
        logger.error(f"Error updating agent config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Safety and Risk Management Endpoints

@router.get("/safety-config", response_model=SafetyConfig)
async def get_safety_config() -> SafetyConfig:
    """Get current safety configuration."""
    try:
        return SAFETY_CONFIG
    except Exception as e:
        logger.error(f"Error getting safety config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/safety-config", response_model=SafetyConfig)
async def update_safety_config(config_update: dict) -> SafetyConfig:
    """Update safety configuration."""
    try:
        global SAFETY_CONFIG

        # Update configuration fields
        for key, value in config_update.items():
            if hasattr(SAFETY_CONFIG, key):
                setattr(SAFETY_CONFIG, key, value)

        logger.info(f"Safety configuration updated: {config_update}")
        return SAFETY_CONFIG

    except Exception as e:
        logger.error(f"Error updating safety config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dry-run", response_model=list[DryRunResult])
async def execute_dry_run(action_plan: list[dict]) -> list[DryRunResult]:
    """Execute a dry run simulation of action plan."""
    try:
        results = DryRunExecutor.execute_dry_run(action_plan)
        logger.info(f"Dry run executed for {len(action_plan)} actions")
        return results

    except Exception as e:
        logger.error(f"Error executing dry run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confidence-score")
async def calculate_confidence(incident_data: dict) -> ConfidenceScore:
    """Calculate confidence score for incident analysis."""
    try:
        confidence_result = ConfidenceScorer.calculate_confidence(incident_data)

        # Record confidence history
        CONFIDENCE_HISTORY.append((datetime.now(UTC), confidence_result.overall_confidence))

        # Keep only last 100 entries
        if len(CONFIDENCE_HISTORY) > 100:
            CONFIDENCE_HISTORY.pop(0)

        logger.info(f"Confidence calculated: {confidence_result.overall_confidence:.2f}")
        return confidence_result

    except Exception as e:
        logger.error(f"Error calculating confidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk-assessment")
async def assess_risk(action_type: str, action_details: dict = {}) -> ActionRiskAssessment:
    """Assess risk level for a specific action."""
    try:
        risk_assessment = RiskAssessment.classify_action_risk(action_type, action_details)
        logger.info(f"Risk assessed for {action_type}: {risk_assessment.risk_level}")
        return risk_assessment

    except Exception as e:
        logger.error(f"Error assessing risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approvals/pending")
async def get_pending_approvals() -> list[ApprovalRequest]:
    """Get list of pending approval requests."""
    try:
        return approval_manager.get_pending_approvals()

    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, comments: str = "") -> SuccessResponse:
    """Approve a pending action."""
    try:
        success = approval_manager.approve_action(approval_id)

        if not success:
            raise HTTPException(status_code=404, detail="Approval request not found or already processed")

        logger.info(f"Action approved: {approval_id}")

        return SuccessResponse(
            success=True,
            message="Action approved and will be executed",
            data={"approval_id": approval_id, "comments": comments}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approvals/{approval_id}/reject")
async def reject_action(approval_id: str, comments: str = "") -> SuccessResponse:
    """Reject a pending action."""
    try:
        success = approval_manager.reject_action(approval_id)

        if not success:
            raise HTTPException(status_code=404, detail="Approval request not found or already processed")

        logger.info(f"Action rejected: {approval_id}")

        return SuccessResponse(
            success=True,
            message="Action rejected",
            data={"approval_id": approval_id, "comments": comments}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/action-history")
async def get_action_history() -> list[ActionHistory]:
    """Get history of executed actions."""
    try:
        # Return last 50 actions, most recent first
        return sorted(ACTION_HISTORY, key=lambda x: x.executed_at, reverse=True)[:50]

    except Exception as e:
        logger.error(f"Error getting action history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback/{action_id}")
async def rollback_action(action_id: str) -> dict:
    """Rollback a specific action."""
    try:
        result = RollbackManager.rollback_action(action_id)

        if result["success"]:
            logger.info(f"Action rolled back: {action_id}")
        else:
            logger.warning(f"Rollback failed for {action_id}: {result['error']}")

        return result

    except Exception as e:
        logger.error(f"Error rolling back action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback-last")
async def rollback_last_action() -> dict:
    """Rollback the most recent action."""
    try:
        if not ACTION_HISTORY:
            return {"success": False, "error": "No actions to rollback"}

        # Find most recent rollback-able action
        for action in reversed(ACTION_HISTORY):
            if action.rollback_available and not action.rollback_executed:
                return RollbackManager.rollback_action(action.id)

        return {"success": False, "error": "No rollback-able actions found"}

    except Exception as e:
        logger.error(f"Error rolling back last action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/confidence-history")
async def get_confidence_history() -> list[dict]:
    """Get historical confidence scores."""
    try:
        return [
            {
                "timestamp": timestamp.isoformat(),
                "confidence": confidence
            }
            for timestamp, confidence in CONFIDENCE_HISTORY
        ]

    except Exception as e:
        logger.error(f"Error getting confidence history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emergency-stop", response_model=SuccessResponse)
async def emergency_stop() -> SuccessResponse:
    """Emergency stop all AI agent operations."""
    try:
        # In a real implementation, this would:
        # 1. Stop all running AI operations
        # 2. Cancel queued tasks
        # 3. Set agent to emergency stop mode
        # 4. Send notifications to team

        logger.warning("Emergency stop activated for AI agent")

        return SuccessResponse(
            success=True,
            message="Emergency stop activated - all AI operations halted",
            data={"timestamp": datetime.now(UTC).isoformat()}
        )

    except Exception as e:
        logger.error(f"Error during emergency stop: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompts")
async def get_agent_prompts() -> JSONResponse:
    """Get current agent prompt templates (for transparency)."""
    try:
        # Return sanitized prompt templates
        prompts = {
            "incident_analysis": {
                "description": "Main prompt for analyzing incidents",
                "variables": ["incident_description", "service_context", "recent_changes"],
                "example": "Analyze the following incident and provide root cause analysis..."
            },
            "action_recommendation": {
                "description": "Prompt for recommending remediation actions",
                "variables": ["incident_type", "service_architecture", "constraints"],
                "example": "Based on the analysis, recommend appropriate remediation actions..."
            },
            "pattern_detection": {
                "description": "Prompt for detecting incident patterns",
                "variables": ["incident_history", "time_range", "service_name"],
                "example": "Identify any patterns in the following incident history..."
            }
        }

        return JSONResponse(content={"prompts": prompts})

    except Exception as e:
        logger.error(f"Error getting prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute-action", response_model=dict)
async def execute_remediation_action(
    action_type: str,
    params: dict[str, Any],
    dry_run: bool = False,
    auto_approve: bool = False
) -> dict:
    """Execute a specific remediation action (for testing/manual execution)."""
    try:
        # Import here to avoid circular dependency
        from src.oncall_agent.agent_enhanced import EnhancedOncallAgent

        global enhanced_agent_instance

        # Create enhanced agent if needed
        if not enhanced_agent_instance:
            enhanced_agent_instance = EnhancedOncallAgent(ai_mode=AGENT_CONFIG.mode)
            await enhanced_agent_instance.connect_integrations()

        # Execute via K8s MCP integration
        if enhanced_agent_instance.k8s_mcp:
            result = await enhanced_agent_instance.k8s_mcp.execute_action(
                action_type,
                {**params, "dry_run": dry_run, "auto_approve": auto_approve}
            )

            # Add execution metadata
            result["executed_by"] = "manual_api_call"
            result["mode"] = AGENT_CONFIG.mode.value
            result["timestamp"] = datetime.now(UTC).isoformat()

            return result
        else:
            return {
                "success": False,
                "error": "Kubernetes integration not available",
                "executed_by": "manual_api_call"
            }

    except Exception as e:
        logger.error(f"Error executing action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/execution-history", response_model=list[dict])
async def get_execution_history(limit: int = 50) -> list[dict]:
    """Get history of executed remediation actions."""
    try:
        global enhanced_agent_instance

        if enhanced_agent_instance and enhanced_agent_instance.agent_executor:
            history = enhanced_agent_instance.agent_executor.get_execution_history()
            # Return most recent entries
            return history[-limit:]
        else:
            return []

    except Exception as e:
        logger.error(f"Error getting execution history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/k8s-audit-log", response_model=list[dict])
async def get_k8s_audit_log(limit: int = 100) -> list[dict]:
    """Get Kubernetes command audit log."""
    try:
        global enhanced_agent_instance

        if enhanced_agent_instance and enhanced_agent_instance.k8s_mcp:
            audit_log = enhanced_agent_instance.k8s_mcp.get_audit_log()
            # Return most recent entries
            return audit_log[-limit:]
        else:
            return []

    except Exception as e:
        logger.error(f"Error getting K8s audit log: {e}")
        raise HTTPException(status_code=500, detail=str(e))
