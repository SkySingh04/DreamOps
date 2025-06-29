"""API dependencies for dependency injection."""

import asyncpg

# Placeholder for database pool
# In production, this would be initialized properly
_db_pool = None


async def get_db_pool() -> asyncpg.Pool | None:
    """Get database connection pool."""
    return _db_pool


def set_db_pool(pool: asyncpg.Pool) -> None:
    """Set database connection pool."""
    global _db_pool
    _db_pool = pool