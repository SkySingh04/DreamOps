# JSON Serialization Fix

## Issue
The API was returning an error: `TypeError: Object of type ResolutionAction is not JSON serializable`

This occurred when the enhanced agent returned execution results containing `ResolutionAction` dataclass objects.

## Root Cause
In `agent_executor.py`, the execution context was storing the entire `ResolutionAction` object:
```python
execution_context = {
    "action": action,  # This is a ResolutionAction dataclass!
    "incident_id": incident_id,
    ...
}
```

## Fix Applied
Modified the execution context to convert the `ResolutionAction` to a dictionary:
```python
execution_context = {
    "action": {
        "action_type": action.action_type,
        "description": action.description,
        "params": action.params,
        "confidence": action.confidence,
        "risk_level": action.risk_level,
        "estimated_time": action.estimated_time,
        "rollback_possible": action.rollback_possible
    },
    "incident_id": incident_id,
    ...
}
```

## Additional Enhancement
Added a `to_dict()` method to the `ResolutionAction` dataclass for consistent serialization:
```python
def to_dict(self) -> dict[str, Any]:
    """Convert to dictionary for JSON serialization."""
    return {
        "action_type": self.action_type,
        "description": self.description,
        "params": self.params,
        "confidence": self.confidence,
        "risk_level": self.risk_level,
        "estimated_time": self.estimated_time,
        "rollback_possible": self.rollback_possible,
        "prerequisites": self.prerequisites or []
    }
```

## Result
The API can now properly return JSON responses containing execution details without serialization errors.