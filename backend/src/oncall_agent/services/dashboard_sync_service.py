"""Service to sync incident data to frontend dashboard tables."""

import json
from datetime import UTC, datetime
from typing import Any

from src.oncall_agent.services.incident_service import get_pool
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)


async def init_dashboard_tables() -> None:
    """Initialize dashboard-compatible tables if they don't exist."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Create users table if not exists (for foreign key reference)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                firebase_uid VARCHAR(128) UNIQUE,
                name VARCHAR(100),
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash TEXT,
                role VARCHAR(20) NOT NULL DEFAULT 'member',
                llm_provider VARCHAR(20),
                llm_model VARCHAR(50),
                is_setup_complete BOOLEAN NOT NULL DEFAULT FALSE,
                setup_completed_at TIMESTAMPTZ,
                last_validation_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deleted_at TIMESTAMPTZ,
                stripe_customer_id TEXT UNIQUE,
                stripe_subscription_id TEXT UNIQUE,
                stripe_product_id TEXT,
                plan_name VARCHAR(50),
                subscription_status VARCHAR(20),
                account_tier VARCHAR(20) DEFAULT 'free',
                alerts_used INTEGER DEFAULT 0,
                alerts_limit INTEGER DEFAULT 3,
                billing_cycle_start TIMESTAMPTZ DEFAULT NOW(),
                last_payment_at TIMESTAMPTZ
            )
        """)

        # Create dashboard-compatible incidents table
        # This matches the frontend Drizzle schema exactly
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_incidents (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                title VARCHAR(255) NOT NULL,
                description TEXT,
                severity VARCHAR(20) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'open',
                source VARCHAR(50) NOT NULL,
                source_id VARCHAR(255),
                assigned_to INTEGER REFERENCES users(id),
                resolved_by INTEGER REFERENCES users(id),
                resolved_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata TEXT
            )
        """)

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dashboard_incidents_status ON dashboard_incidents(status)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dashboard_incidents_severity ON dashboard_incidents(severity)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dashboard_incidents_created_at ON dashboard_incidents(created_at DESC)
        """)

        # Create AI actions table for dashboard
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_actions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                incident_id INTEGER REFERENCES dashboard_incidents(id),
                action VARCHAR(100) NOT NULL,
                description TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'completed',
                ai_agent VARCHAR(50) NOT NULL DEFAULT 'oncall-agent',
                approved_by INTEGER REFERENCES users(id),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata TEXT
            )
        """)

        # Create metrics table for dashboard
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                metric_type VARCHAR(50) NOT NULL,
                value TEXT NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                metadata TEXT
            )
        """)

        logger.info("Dashboard tables initialized successfully")


async def ensure_demo_user_exists() -> int:
    """Ensure demo user exists and return user ID."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Check if demo user exists
        row = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            "demo@dreamops.io"
        )

        if row:
            return row["id"]

        # Create demo user
        row = await conn.fetchrow("""
            INSERT INTO users (email, name, role, is_setup_complete, account_tier, alerts_limit)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, "demo@dreamops.io", "Demo User", "admin", True, "free", 100)

        logger.info(f"Created demo user with ID {row['id']}")
        return row["id"]


async def sync_incident_to_dashboard(
    source_id: str,
    title: str,
    description: str,
    severity: str,
    status: str,
    source: str,
    user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> int:
    """
    Sync an incident to the dashboard-compatible table.

    Returns the dashboard incident ID.
    """
    pool = await get_pool()

    # Ensure we have a valid user_id
    if user_id is None:
        user_id = await ensure_demo_user_exists()

    # Map backend status to frontend status
    status_mapping = {
        "triggered": "open",
        "acknowledged": "investigating",
        "resolved": "resolved",
        "closed": "closed",
    }
    dashboard_status = status_mapping.get(status.lower(), status.lower())

    # Map severity
    severity_mapping = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "warning": "medium",
        "info": "low",
    }
    dashboard_severity = severity_mapping.get(severity.lower(), "medium")

    async with pool.acquire() as conn:
        # Check if incident already exists by source_id
        existing = await conn.fetchrow(
            "SELECT id FROM dashboard_incidents WHERE source_id = $1",
            source_id
        )

        if existing:
            # Update existing incident
            await conn.execute("""
                UPDATE dashboard_incidents SET
                    status = $1,
                    updated_at = $2,
                    resolved_at = CASE WHEN $1 = 'resolved' THEN NOW() ELSE resolved_at END
                WHERE source_id = $3
            """, dashboard_status, datetime.now(UTC), source_id)
            logger.info(f"Updated dashboard incident for source_id={source_id}")
            return existing["id"]

        # Create new incident
        row = await conn.fetchrow("""
            INSERT INTO dashboard_incidents (
                user_id, title, description, severity, status, source, source_id, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """,
            user_id,
            title,
            description,
            dashboard_severity,
            dashboard_status,
            source,
            source_id,
            json.dumps(metadata) if metadata else None,
        )

        logger.info(f"Created dashboard incident ID={row['id']} for source_id={source_id}")
        return row["id"]


async def record_ai_action(
    action: str,
    description: str | None = None,
    incident_id: int | None = None,
    user_id: int | None = None,
    status: str = "completed",
    metadata: dict[str, Any] | None = None,
) -> int:
    """Record an AI action in the dashboard."""
    pool = await get_pool()

    if user_id is None:
        user_id = await ensure_demo_user_exists()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO ai_actions (
                user_id, incident_id, action, description, status, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """,
            user_id,
            incident_id,
            action,
            description,
            status,
            json.dumps(metadata) if metadata else None,
        )

        logger.info(f"Recorded AI action ID={row['id']}: {action}")
        return row["id"]


async def record_metric(
    metric_type: str,
    value: str,
    user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a metric in the dashboard."""
    pool = await get_pool()

    if user_id is None:
        user_id = await ensure_demo_user_exists()

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO metrics (user_id, metric_type, value, metadata)
            VALUES ($1, $2, $3, $4)
        """,
            user_id,
            metric_type,
            value,
            json.dumps(metadata) if metadata else None,
        )

        logger.info(f"Recorded metric: {metric_type}={value}")


async def update_incident_status(
    source_id: str,
    status: str,
    resolved_by_user_id: int | None = None,
) -> bool:
    """Update incident status in dashboard."""
    pool = await get_pool()

    status_mapping = {
        "triggered": "open",
        "acknowledged": "investigating",
        "resolved": "resolved",
        "closed": "closed",
    }
    dashboard_status = status_mapping.get(status.lower(), status.lower())

    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE dashboard_incidents SET
                status = $1,
                updated_at = NOW(),
                resolved_at = CASE WHEN $1 = 'resolved' THEN NOW() ELSE resolved_at END,
                resolved_by = CASE WHEN $1 = 'resolved' THEN $3 ELSE resolved_by END
            WHERE source_id = $2
        """, dashboard_status, source_id, resolved_by_user_id)

        updated = result.split()[-1] != '0'
        if updated:
            logger.info(f"Updated dashboard incident status: source_id={source_id}, status={dashboard_status}")
        return updated
