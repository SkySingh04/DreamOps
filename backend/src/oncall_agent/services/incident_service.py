"""PostgreSQL persistence service for incidents and AI analysis."""

import json
from datetime import UTC, datetime
from typing import Any

import asyncpg

from src.oncall_agent.api.schemas import (
    ActionType,
    AIAnalysis,
    Incident,
    IncidentAction,
    IncidentStatus,
    Severity,
)
from src.oncall_agent.config import get_config
from src.oncall_agent.utils import get_logger

logger = get_logger(__name__)

# Connection pool singleton
_pool: asyncpg.Pool | None = None


def _serialize_action(action: IncidentAction) -> dict:
    """Serialize IncidentAction to a JSON-compatible dict."""
    return {
        "action_type": action.action_type.value if hasattr(action.action_type, 'value') else str(action.action_type),
        "parameters": action.parameters,
        "automated": action.automated,
        "user": action.user,
        "timestamp": action.timestamp.isoformat() if action.timestamp else None,
        "result": action.result,
    }


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool."""
    global _pool
    if _pool is None:
        config = get_config()
        postgres_url = config.postgres_url or config.database_url or config.neon_database_url
        if not postgres_url:
            raise RuntimeError("No PostgreSQL connection URL configured (POSTGRES_URL, DATABASE_URL, or NEON_DATABASE_URL)")

        logger.info("Connecting to PostgreSQL database...")
        _pool = await asyncpg.create_pool(
            postgres_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("PostgreSQL connection pool created successfully")

        # Initialize tables
        await _init_tables()

    return _pool


async def close_pool() -> None:
    """Close the database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed")


async def _init_tables() -> None:
    """Initialize database tables if they don't exist."""
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Create incidents table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'triggered',
                service_name TEXT NOT NULL,
                alert_source TEXT NOT NULL DEFAULT 'manual',
                assignee TEXT,
                resolution TEXT,
                resolved_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}',
                timeline JSONB DEFAULT '[]',
                actions_taken JSONB DEFAULT '[]',
                ai_analysis JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """)

        # Create analysis table for full AI analysis data
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS incident_analysis (
                incident_id TEXT PRIMARY KEY REFERENCES incidents(id) ON DELETE CASCADE,
                analysis_data JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ
            )
        """)

        # Create incident_reports table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS incident_reports (
                incident_id TEXT PRIMARY KEY REFERENCES incidents(id) ON DELETE CASCADE,
                json_report JSONB NOT NULL,
                markdown_report TEXT NOT NULL,
                generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # Create indexes for common queries
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_incidents_service ON incidents(service_name)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC)
        """)

        logger.info("Database tables initialized successfully")


def _incident_from_row(row: asyncpg.Record) -> Incident:
    """Convert a database row to an Incident object."""
    ai_analysis = None
    if row['ai_analysis']:
        ai_data = row['ai_analysis'] if isinstance(row['ai_analysis'], dict) else json.loads(row['ai_analysis'])
        # Handle JSON null case - ai_data could be None after json.loads("null")
        if ai_data is not None and isinstance(ai_data, dict):
            ai_analysis = AIAnalysis(**ai_data)

    actions = []
    if row['actions_taken']:
        actions_data = row['actions_taken'] if isinstance(row['actions_taken'], list) else json.loads(row['actions_taken'])
        for action_dict in actions_data:
            # Parse action_type from string to enum if needed
            action_type = action_dict.get('action_type')
            if isinstance(action_type, str):
                action_dict['action_type'] = ActionType(action_type)

            # Parse timestamp from string if needed
            timestamp = action_dict.get('timestamp')
            if isinstance(timestamp, str):
                action_dict['timestamp'] = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            actions.append(IncidentAction(**action_dict))

    return Incident(
        id=row['id'],
        title=row['title'],
        description=row['description'] or '',
        severity=Severity(row['severity']),
        status=IncidentStatus(row['status']),
        service_name=row['service_name'],
        alert_source=row['alert_source'],
        assignee=row['assignee'],
        resolution=row['resolution'],
        resolved_at=row['resolved_at'],
        metadata=row['metadata'] if isinstance(row['metadata'], dict) else json.loads(row['metadata'] or '{}'),
        timeline=row['timeline'] if isinstance(row['timeline'], list) else json.loads(row['timeline'] or '[]'),
        actions_taken=actions,
        ai_analysis=ai_analysis,
        created_at=row['created_at'],
        updated_at=row['updated_at'],
    )


class IncidentService:
    """Service for incident database operations."""

    @staticmethod
    async def create(incident: Incident) -> Incident:
        """Create a new incident in the database."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO incidents (
                    id, title, description, severity, status, service_name,
                    alert_source, assignee, resolution, resolved_at, metadata,
                    timeline, actions_taken, ai_analysis, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                """,
                incident.id,
                incident.title,
                incident.description,
                incident.severity.value,
                incident.status.value,
                incident.service_name,
                incident.alert_source,
                incident.assignee,
                incident.resolution,
                incident.resolved_at,
                json.dumps(incident.metadata),
                json.dumps(incident.timeline),
                json.dumps([_serialize_action(a) for a in incident.actions_taken] if incident.actions_taken else []),
                json.dumps(incident.ai_analysis.model_dump() if incident.ai_analysis else None),
                incident.created_at,
                incident.updated_at,
            )

        logger.info(f"Created incident {incident.id} in database")
        return incident

    @staticmethod
    async def get(incident_id: str) -> Incident | None:
        """Get an incident by ID."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM incidents WHERE id = $1",
                incident_id
            )

        if not row:
            return None

        return _incident_from_row(row)

    @staticmethod
    async def update(incident: Incident) -> Incident:
        """Update an existing incident."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE incidents SET
                    title = $2,
                    description = $3,
                    severity = $4,
                    status = $5,
                    service_name = $6,
                    alert_source = $7,
                    assignee = $8,
                    resolution = $9,
                    resolved_at = $10,
                    metadata = $11,
                    timeline = $12,
                    actions_taken = $13,
                    ai_analysis = $14,
                    updated_at = $15
                WHERE id = $1
                """,
                incident.id,
                incident.title,
                incident.description,
                incident.severity.value,
                incident.status.value,
                incident.service_name,
                incident.alert_source,
                incident.assignee,
                incident.resolution,
                incident.resolved_at,
                json.dumps(incident.metadata),
                json.dumps(incident.timeline),
                json.dumps([_serialize_action(a) for a in incident.actions_taken] if incident.actions_taken else []),
                json.dumps(incident.ai_analysis.model_dump() if incident.ai_analysis else None),
                datetime.now(UTC),
            )

        logger.info(f"Updated incident {incident.id} in database")
        return incident

    @staticmethod
    async def list(
        page: int = 1,
        page_size: int = 20,
        status: IncidentStatus | None = None,
        severity: Severity | None = None,
        service: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> tuple[list[Incident], int]:
        """List incidents with filtering and pagination."""
        pool = await get_pool()

        # Build query dynamically
        conditions = []
        params = []
        param_count = 0

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status.value)

        if severity:
            param_count += 1
            conditions.append(f"severity = ${param_count}")
            params.append(severity.value)

        if service:
            param_count += 1
            conditions.append(f"service_name = ${param_count}")
            params.append(service)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Validate sort_by to prevent SQL injection
        valid_sort_columns = {"created_at", "updated_at", "severity"}
        if sort_by not in valid_sort_columns:
            sort_by = "created_at"

        sort_direction = "DESC" if sort_order == "desc" else "ASC"

        async with pool.acquire() as conn:
            # Get total count
            count_query = f"SELECT COUNT(*) FROM incidents {where_clause}"
            total = await conn.fetchval(count_query, *params)

            # Get paginated results
            offset = (page - 1) * page_size
            param_count += 1
            limit_param = param_count
            param_count += 1
            offset_param = param_count

            query = f"""
                SELECT * FROM incidents
                {where_clause}
                ORDER BY {sort_by} {sort_direction}
                LIMIT ${limit_param} OFFSET ${offset_param}
            """

            rows = await conn.fetch(query, *params, page_size, offset)

        incidents = [_incident_from_row(row) for row in rows]
        return incidents, total

    @staticmethod
    async def delete(incident_id: str) -> bool:
        """Delete an incident."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM incidents WHERE id = $1",
                incident_id
            )

        deleted = result.split()[-1] != '0'
        if deleted:
            logger.info(f"Deleted incident {incident_id} from database")
        return deleted

    @staticmethod
    async def exists(incident_id: str) -> bool:
        """Check if an incident exists."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM incidents WHERE id = $1)",
                incident_id
            )

        return result


class AnalysisService:
    """Service for AI analysis database operations."""

    @staticmethod
    async def save(incident_id: str, analysis_data: dict[str, Any]) -> None:
        """Save AI analysis for an incident."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO incident_analysis (incident_id, analysis_data, created_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (incident_id) DO UPDATE SET
                    analysis_data = $2,
                    updated_at = $3
                """,
                incident_id,
                json.dumps(analysis_data),
                datetime.now(UTC),
            )

        logger.info(f"Saved analysis for incident {incident_id}")

    @staticmethod
    async def get(incident_id: str) -> dict[str, Any] | None:
        """Get AI analysis for an incident."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT analysis_data FROM incident_analysis WHERE incident_id = $1",
                incident_id
            )

        if not row:
            return None

        data = row['analysis_data']
        return data if isinstance(data, dict) else json.loads(data)

    @staticmethod
    async def delete(incident_id: str) -> bool:
        """Delete analysis for an incident."""
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM incident_analysis WHERE incident_id = $1",
                incident_id
            )

        return result.split()[-1] != '0'


class ReportService:
    """Service for incident report generation and storage."""

    @staticmethod
    async def generate_and_save(incident_id: str) -> dict[str, Any]:
        """Generate and save both JSON and Markdown reports for an incident."""
        # Get incident data
        incident = await IncidentService.get(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")

        # Get AI analysis
        analysis = await AnalysisService.get(incident_id) or {}

        # Generate JSON report
        json_report = ReportService._generate_json_report(incident, analysis)

        # Generate Markdown report
        md_report = ReportService._generate_markdown_report(incident, analysis)

        # Save to database
        pool = await get_pool()
        now = datetime.now(UTC)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO incident_reports (incident_id, json_report, markdown_report, generated_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (incident_id) DO UPDATE SET
                    json_report = $2,
                    markdown_report = $3,
                    generated_at = $4
                """,
                incident_id,
                json.dumps(json_report),
                md_report,
                now,
            )

        logger.info(f"Generated and saved reports for incident {incident_id}")
        return {"json_report": json_report, "markdown_report": md_report}

    @staticmethod
    def _generate_json_report(incident: Incident, analysis: dict) -> dict:
        """Generate JSON report content."""
        return {
            "report_generated_at": datetime.now(UTC).isoformat(),
            "report_type": "incident_resolution",
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
                "duration_minutes": (
                    (incident.resolved_at - incident.created_at).total_seconds() / 60
                    if incident.resolved_at and incident.created_at else None
                ),
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

    @staticmethod
    def _generate_markdown_report(incident: Incident, analysis: dict) -> str:
        """Generate Markdown report content."""
        # Calculate duration
        duration_str = "N/A"
        if incident.resolved_at and incident.created_at:
            duration_minutes = (incident.resolved_at - incident.created_at).total_seconds() / 60
            if duration_minutes < 60:
                duration_str = f"{int(duration_minutes)} minutes"
            else:
                hours = int(duration_minutes / 60)
                mins = int(duration_minutes % 60)
                duration_str = f"{hours}h {mins}m"

        md_lines = [
            f"# Incident Resolution Report: {incident.title}",
            "",
            f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "---",
            "",
            "## Summary",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| **ID** | `{incident.id}` |",
            f"| **Severity** | {incident.severity.value if hasattr(incident.severity, 'value') else str(incident.severity)} |",
            f"| **Status** | {incident.status.value if hasattr(incident.status, 'value') else str(incident.status)} |",
            f"| **Service** | {incident.service_name} |",
            f"| **Alert Source** | {incident.alert_source} |",
            f"| **Assignee** | {incident.assignee or 'Unassigned'} |",
            f"| **Created** | {incident.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if incident.created_at else 'N/A'} |",
            f"| **Resolved** | {incident.resolved_at.strftime('%Y-%m-%d %H:%M:%S UTC') if incident.resolved_at else 'N/A'} |",
            f"| **Duration** | {duration_str} |",
            "",
            "## Description",
            "",
            incident.description or "No description provided.",
            "",
        ]

        # Add AI Analysis section
        ai_data = analysis if analysis else (incident.ai_analysis.model_dump() if incident.ai_analysis else None)
        if ai_data:
            md_lines.extend(["## AI Analysis", ""])
            if isinstance(ai_data, dict):
                if 'analysis' in ai_data:
                    md_lines.append(ai_data['analysis'])
                else:
                    if ai_data.get('summary'):
                        md_lines.extend(["### Summary", "", ai_data['summary'], ""])
                    if ai_data.get('root_cause'):
                        md_lines.extend(["### Root Cause", "", ai_data['root_cause'], ""])
                    if ai_data.get('impact_assessment'):
                        md_lines.extend(["### Impact Assessment", "", ai_data['impact_assessment'], ""])
                    if ai_data.get('recommended_actions'):
                        md_lines.extend(["### Recommended Actions", ""])
                        for i, action in enumerate(ai_data['recommended_actions'], 1):
                            if isinstance(action, dict):
                                md_lines.append(f"{i}. **{action.get('action', 'Unknown')}**: {action.get('reason', '')}")
                            else:
                                md_lines.append(f"{i}. {action}")
                        md_lines.append("")
            md_lines.append("")

        # Add Timeline section
        if incident.timeline:
            md_lines.extend(["## Timeline", ""])
            for event in incident.timeline:
                timestamp = event.get('timestamp', 'N/A')
                event_type = event.get('event', 'unknown')
                description = event.get('description', '')
                user = event.get('user', 'system')
                md_lines.append(f"- **{timestamp}** - `{event_type}` - {description} (by {user})")
            md_lines.append("")

        # Add Actions Taken section
        if incident.actions_taken:
            md_lines.extend(["## Actions Taken", ""])
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
            md_lines.extend(["## Resolution", "", incident.resolution, ""])

        md_lines.extend([
            "---",
            "",
            "*Report auto-generated by DreamOps AI Incident Management Platform upon incident resolution*",
        ])

        return "\n".join(md_lines)

    @staticmethod
    async def get_saved_report(incident_id: str) -> dict[str, Any] | None:
        """Get saved reports for an incident."""
        try:
            pool = await get_pool()

            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT json_report, markdown_report, generated_at FROM incident_reports WHERE incident_id = $1",
                    incident_id
                )

            if not row:
                return None

            json_data = row['json_report']
            return {
                "json_report": json_data if isinstance(json_data, dict) else json.loads(json_data),
                "markdown_report": row['markdown_report'],
                "generated_at": row['generated_at'].isoformat() if row['generated_at'] else None,
            }
        except asyncpg.exceptions.UndefinedTableError:
            # Table doesn't exist yet - return None and let caller generate on-the-fly
            logger.warning(f"incident_reports table does not exist, returning None for incident {incident_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting saved report for {incident_id}: {e}")
            return None


async def check_database_health() -> dict[str, Any]:
    """Check database connection health."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # Test query
            await conn.fetchval("SELECT 1")

            # Get some stats
            incident_count = await conn.fetchval("SELECT COUNT(*) FROM incidents")
            analysis_count = await conn.fetchval("SELECT COUNT(*) FROM incident_analysis")

        return {
            "status": "healthy",
            "connected": True,
            "pool_size": pool.get_size(),
            "pool_free": pool.get_idle_size(),
            "incident_count": incident_count,
            "analysis_count": analysis_count,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connected": False,
            "error": str(e),
        }
