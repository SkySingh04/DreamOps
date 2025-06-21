"""AI Agent control and monitoring endpoints."""

import asyncio
import uuid
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from src.oncall_agent.api.schemas import (
    AgentTriggerRequest, AgentResponse, AgentStatus,
    AIAnalysis, IncidentAction, ActionType, SuccessResponse
)
from src.oncall_agent.agent import OncallAgent
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["ai-agent"])

# Global agent instance (shared with main API)
agent_instance: Optional[OncallAgent] = None

# Agent metrics storage
AGENT_METRICS = {
    "incidents_processed": 0,
    "total_response_time_ms": 0,
    "errors": [],
    "last_analysis": None,
    "start_time": datetime.now(UTC)
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


async def execute_automated_actions(incident_id: str, actions: List[IncidentAction]):
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
                "capabilities": integration.get_capabilities()
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
    comments: Optional[str] = Query(None, description="Additional comments")
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