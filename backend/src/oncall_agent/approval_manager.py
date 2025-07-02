"""Approval manager for handling approval mode interactions."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from .api.log_streaming import log_stream_manager
from .api.schemas import ApprovalRequest
from .strategies.kubernetes_resolver import ResolutionAction

logger = logging.getLogger(__name__)

# Global approval queue
APPROVAL_QUEUE: dict[str, ApprovalRequest] = {}
# Approval events for async waiting
APPROVAL_EVENTS: dict[str, asyncio.Event] = {}
# Approval results
APPROVAL_RESULTS: dict[str, bool] = {}


class ApprovalManager:
    """Manages approval requests and responses."""

    def __init__(self, timeout_seconds: int = 300):  # 5 minute default timeout
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(__name__)

    async def request_approval(
        self,
        action: ResolutionAction,
        incident_id: str
    ) -> bool:
        """Request approval for an action and wait for response.
        
        Args:
            action: The action requiring approval
            incident_id: The incident ID this action is for
            
        Returns:
            True if approved, False if rejected or timed out
        """
        # Create approval request
        approval_id = str(uuid.uuid4())
        # Create action plan from the resolution action
        action_plan = [{
            "type": action.action_type,
            "description": action.description,
            "params": action.params,
            "risk_level": action.risk_level,
            "confidence": action.confidence
        }]

        # Create confidence score
        from .api.schemas import (
            ActionRiskAssessment,
            ConfidenceFactors,
            ConfidenceScore,
        )
        confidence_score = ConfidenceScore(
            overall_confidence=action.confidence,
            factor_breakdown=ConfidenceFactors(
                pattern_recognition=0.8,
                historical_success=0.8,
                context_quality=0.8,
                resource_availability=0.9,
                time_sensitivity=0.8
            ),
            recommendation="Approval required for medium/high risk action",
            threshold_met=False
        )

        # Create risk assessment
        risk_assessment = ActionRiskAssessment(
            action_type=action.action_type,
            risk_level=action.risk_level,
            risk_factors=[],
            auto_execute_allowed=False,
            requires_approval=True
        )

        approval_request = ApprovalRequest(
            id=approval_id,
            incident_id=incident_id,
            action_plan=action_plan,
            confidence_score=confidence_score,
            risk_assessments=[risk_assessment],
            requested_at=datetime.now(UTC),
            timeout_at=datetime.now(UTC) + timedelta(seconds=self.timeout_seconds),
            status="PENDING",
            comments=""
        )

        # Add to queue
        APPROVAL_QUEUE[approval_id] = approval_request

        # Create event for waiting
        event = asyncio.Event()
        APPROVAL_EVENTS[approval_id] = event

        # Log approval request to frontend
        await log_stream_manager.log_warning(
            f"⏸️ Approval required for: {action.action_type}",
            incident_id=incident_id,
            stage="approval_required",
            action_type=action.action_type,
            metadata={
                "approval_id": approval_id,
                "action_type": action.action_type,
                "description": action.description,
                "risk_level": action.risk_level,
                "confidence": action.confidence,
                "command": self._get_command_preview(action),
                "approval_required": True
            }
        )

        try:
            # Wait for approval with timeout
            await asyncio.wait_for(event.wait(), timeout=self.timeout_seconds)

            # Get result
            approved = APPROVAL_RESULTS.get(approval_id, False)

            # Update status
            if approved:
                APPROVAL_QUEUE[approval_id].status = "APPROVED"
                await log_stream_manager.log_success(
                    f"✅ Action approved: {action.action_type}",
                    incident_id=incident_id,
                    action_type=action.action_type,
                    metadata={"approval_id": approval_id}
                )
            else:
                APPROVAL_QUEUE[approval_id].status = "REJECTED"
                await log_stream_manager.log_error(
                    f"❌ Action rejected: {action.action_type}",
                    incident_id=incident_id,
                    action_type=action.action_type,
                    metadata={"approval_id": approval_id}
                )

            return approved

        except TimeoutError:
            # Timeout expired
            APPROVAL_QUEUE[approval_id].status = "EXPIRED"
            await log_stream_manager.log_error(
                f"⏱️ Approval timeout for: {action.action_type}",
                incident_id=incident_id,
                action_type=action.action_type,
                metadata={"approval_id": approval_id}
            )
            return False

        finally:
            # Cleanup
            APPROVAL_EVENTS.pop(approval_id, None)
            APPROVAL_RESULTS.pop(approval_id, None)

    def approve_action(self, approval_id: str) -> bool:
        """Approve an action.
        
        Args:
            approval_id: The approval request ID
            
        Returns:
            True if the approval was processed, False if not found
        """
        if approval_id not in APPROVAL_QUEUE:
            return False

        if APPROVAL_QUEUE[approval_id].status != "PENDING":
            return False

        # Set result
        APPROVAL_RESULTS[approval_id] = True

        # Trigger event if waiting
        if approval_id in APPROVAL_EVENTS:
            APPROVAL_EVENTS[approval_id].set()

        return True

    def reject_action(self, approval_id: str) -> bool:
        """Reject an action.
        
        Args:
            approval_id: The approval request ID
            
        Returns:
            True if the rejection was processed, False if not found
        """
        if approval_id not in APPROVAL_QUEUE:
            return False

        if APPROVAL_QUEUE[approval_id].status != "PENDING":
            return False

        # Set result
        APPROVAL_RESULTS[approval_id] = False

        # Trigger event if waiting
        if approval_id in APPROVAL_EVENTS:
            APPROVAL_EVENTS[approval_id].set()

        return True

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Get all pending approval requests."""
        now = datetime.now(UTC)
        pending = []

        for approval_id, request in APPROVAL_QUEUE.items():
            if request.status == "PENDING" and request.timeout_at > now:
                pending.append(request)

        return pending

    def _get_command_preview(self, action: ResolutionAction) -> str:
        """Generate command preview for an action."""
        params = action.params

        command_map = {
            "restart_pod": f"kubectl delete pod {params.get('pod_name', '<pod>')} -n {params.get('namespace', 'default')}",
            "scale_deployment": f"kubectl scale deployment {params.get('deployment_name', '<deployment>')} --replicas={params.get('replicas', 3)} -n {params.get('namespace', 'default')}",
            "rollback_deployment": f"kubectl rollout undo deployment {params.get('deployment_name', '<deployment>')} -n {params.get('namespace', 'default')}",
            "increase_memory": f"kubectl patch deployment {params.get('deployment_name', '<deployment>')} --type json -p '[{{\"op\": \"replace\", \"path\": \"/spec/template/spec/containers/0/resources/limits/memory\", \"value\": \"512Mi\"}}]' -n {params.get('namespace', 'default')}",
            "identify_error_pods": f"kubectl get pods -n {params.get('namespace', 'default')} | grep -E 'Error|CrashLoopBackOff'",
            "restart_error_pods": f"kubectl delete pods -n {params.get('namespace', 'default')} --field-selector=status.phase!=Running"
        }

        return command_map.get(action.action_type, f"kubectl {action.action_type}")


# Global instance
approval_manager = ApprovalManager()
