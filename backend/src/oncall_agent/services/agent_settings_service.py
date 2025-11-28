"""PostgreSQL persistence service for AI agent settings."""

import json
from datetime import UTC, datetime
from typing import Any

from src.oncall_agent.services.incident_service import get_pool
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)

# Default settings values
DEFAULT_SETTINGS = {
    "mode": "plan",
    "confidence_threshold": 70,
    "auto_execute_enabled": False,
    "ai_agent_enabled": True,  # Master toggle for AI agent analysis
    "approval_required_for": ["medium", "high"],
    "risk_matrix": {
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
    },
    "notification_preferences": {
        "slack_enabled": True,
        "email_enabled": False,
        "channels": [],
    },
    "dry_run_mode": False,
    "safety_confidence_threshold": 80,
    "risk_tolerance": "medium",
    "emergency_stop_active": False,
}


async def init_agent_settings_table() -> None:
    """Initialize agent_settings table if it doesn't exist."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_settings (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                mode VARCHAR(20) NOT NULL DEFAULT 'plan',
                confidence_threshold INTEGER NOT NULL DEFAULT 70,
                auto_execute_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                ai_agent_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                approval_required_for JSONB NOT NULL DEFAULT '["medium", "high"]',
                risk_matrix JSONB NOT NULL DEFAULT '{}',
                notification_preferences JSONB NOT NULL DEFAULT '{}',
                dry_run_mode BOOLEAN NOT NULL DEFAULT FALSE,
                safety_confidence_threshold INTEGER NOT NULL DEFAULT 80,
                risk_tolerance VARCHAR(20) NOT NULL DEFAULT 'medium',
                emergency_stop_active BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        # Add ai_agent_enabled column if it doesn't exist (migration for existing tables)
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'agent_settings' AND column_name = 'ai_agent_enabled'
                ) THEN
                    ALTER TABLE agent_settings ADD COLUMN ai_agent_enabled BOOLEAN NOT NULL DEFAULT TRUE;
                END IF;
            END $$;
        """)
        logger.info("Agent settings table initialized")


async def get_agent_settings(user_id: int = 1) -> dict[str, Any]:
    """Get agent settings for a user. Creates default settings if none exist."""
    try:
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agent_settings WHERE user_id = $1",
                user_id
            )

            if row:
                return {
                    "mode": row["mode"],
                    "confidence_threshold": row["confidence_threshold"],
                    "auto_execute_enabled": row["auto_execute_enabled"],
                    "ai_agent_enabled": row.get("ai_agent_enabled", True),  # Default to True if column missing
                    "approval_required_for": json.loads(row["approval_required_for"]) if isinstance(row["approval_required_for"], str) else row["approval_required_for"],
                    "risk_matrix": json.loads(row["risk_matrix"]) if isinstance(row["risk_matrix"], str) else row["risk_matrix"],
                    "notification_preferences": json.loads(row["notification_preferences"]) if isinstance(row["notification_preferences"], str) else row["notification_preferences"],
                    "dry_run_mode": row["dry_run_mode"],
                    "safety_confidence_threshold": row["safety_confidence_threshold"],
                    "risk_tolerance": row["risk_tolerance"],
                    "emergency_stop_active": row["emergency_stop_active"],
                }

            # Create default settings for user
            logger.info(f"Creating default agent settings for user {user_id}")
            await save_agent_settings(user_id, DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS.copy()

    except Exception as e:
        logger.error(f"Error getting agent settings: {e}")
        # Return defaults on error
        return DEFAULT_SETTINGS.copy()


async def save_agent_settings(user_id: int, settings: dict[str, Any]) -> dict[str, Any]:
    """Save agent settings for a user. Uses upsert to create or update."""
    try:
        pool = await get_pool()

        async with pool.acquire() as conn:
            # Upsert settings
            await conn.execute("""
                INSERT INTO agent_settings (
                    user_id, mode, confidence_threshold, auto_execute_enabled,
                    ai_agent_enabled, approval_required_for, risk_matrix, notification_preferences,
                    dry_run_mode, safety_confidence_threshold, risk_tolerance,
                    emergency_stop_active, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    mode = EXCLUDED.mode,
                    confidence_threshold = EXCLUDED.confidence_threshold,
                    auto_execute_enabled = EXCLUDED.auto_execute_enabled,
                    ai_agent_enabled = EXCLUDED.ai_agent_enabled,
                    approval_required_for = EXCLUDED.approval_required_for,
                    risk_matrix = EXCLUDED.risk_matrix,
                    notification_preferences = EXCLUDED.notification_preferences,
                    dry_run_mode = EXCLUDED.dry_run_mode,
                    safety_confidence_threshold = EXCLUDED.safety_confidence_threshold,
                    risk_tolerance = EXCLUDED.risk_tolerance,
                    emergency_stop_active = EXCLUDED.emergency_stop_active,
                    updated_at = NOW()
            """,
                user_id,
                settings.get("mode", DEFAULT_SETTINGS["mode"]),
                settings.get("confidence_threshold", DEFAULT_SETTINGS["confidence_threshold"]),
                settings.get("auto_execute_enabled", DEFAULT_SETTINGS["auto_execute_enabled"]),
                settings.get("ai_agent_enabled", DEFAULT_SETTINGS["ai_agent_enabled"]),
                json.dumps(settings.get("approval_required_for", DEFAULT_SETTINGS["approval_required_for"])),
                json.dumps(settings.get("risk_matrix", DEFAULT_SETTINGS["risk_matrix"])),
                json.dumps(settings.get("notification_preferences", DEFAULT_SETTINGS["notification_preferences"])),
                settings.get("dry_run_mode", DEFAULT_SETTINGS["dry_run_mode"]),
                settings.get("safety_confidence_threshold", DEFAULT_SETTINGS["safety_confidence_threshold"]),
                settings.get("risk_tolerance", DEFAULT_SETTINGS["risk_tolerance"]),
                settings.get("emergency_stop_active", DEFAULT_SETTINGS["emergency_stop_active"]),
            )

            logger.info(f"Saved agent settings for user {user_id}")
            return await get_agent_settings(user_id)

    except Exception as e:
        logger.error(f"Error saving agent settings: {e}")
        raise


async def update_agent_settings(user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    """Update specific fields in agent settings."""
    try:
        # Get current settings
        current = await get_agent_settings(user_id)

        # Merge updates
        for key, value in updates.items():
            if key in current:
                current[key] = value

        # Save merged settings
        return await save_agent_settings(user_id, current)

    except Exception as e:
        logger.error(f"Error updating agent settings: {e}")
        raise


async def get_safety_settings(user_id: int = 1) -> dict[str, Any]:
    """Get safety-specific settings for a user."""
    settings = await get_agent_settings(user_id)
    return {
        "dry_run_mode": settings.get("dry_run_mode", False),
        "confidence_threshold": settings.get("safety_confidence_threshold", 80) / 100,  # Convert to 0-1 scale
        "risk_tolerance": settings.get("risk_tolerance", "medium"),
        "emergency_stop_active": settings.get("emergency_stop_active", False),
        "auto_execute_permissions": {
            "read_logs": True,
            "check_status": True,
            "restart_pod": settings.get("mode") == "yolo",
            "scale_deployment": settings.get("mode") == "yolo",
            "delete_resource": False,
            "modify_database": False,
        },
        "mandatory_approval_actions": ["delete_resource", "modify_database", "change_security"],
    }


async def update_safety_settings(user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
    """Update safety-specific settings."""
    # Map safety config fields to agent settings fields
    settings_updates = {}

    if "dry_run_mode" in updates:
        settings_updates["dry_run_mode"] = updates["dry_run_mode"]
    if "confidence_threshold" in updates:
        # Convert from 0-1 scale to percentage
        settings_updates["safety_confidence_threshold"] = int(updates["confidence_threshold"] * 100)
    if "risk_tolerance" in updates:
        settings_updates["risk_tolerance"] = updates["risk_tolerance"]
    if "emergency_stop_active" in updates:
        settings_updates["emergency_stop_active"] = updates["emergency_stop_active"]

    if settings_updates:
        await update_agent_settings(user_id, settings_updates)

    return await get_safety_settings(user_id)


async def is_ai_agent_enabled(user_id: int = 1) -> bool:
    """Check if AI agent is enabled for a user. Used by webhook handler."""
    try:
        settings = await get_agent_settings(user_id)
        return settings.get("ai_agent_enabled", True)
    except Exception as e:
        logger.error(f"Error checking ai_agent_enabled: {e}")
        # Default to enabled on error to avoid blocking incidents
        return True


async def set_ai_agent_enabled(user_id: int, enabled: bool) -> dict[str, Any]:
    """Toggle AI agent on/off for a user."""
    logger.info(f"Setting ai_agent_enabled={enabled} for user {user_id}")
    return await update_agent_settings(user_id, {"ai_agent_enabled": enabled})
