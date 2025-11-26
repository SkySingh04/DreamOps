"""API dependencies for dependency injection."""

from dataclasses import dataclass
from typing import Optional

import asyncpg
from fastapi import Header, Request

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


@dataclass
class AuthenticatedUser:
    """User info from Authentik headers."""
    user_id: str
    email: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None
    groups: Optional[list[str]] = None

    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges."""
        return self.groups is not None and "admin" in self.groups


def get_current_user(
    x_authentik_username: Optional[str] = Header(None, alias="X-Authentik-Username"),
    x_authentik_email: Optional[str] = Header(None, alias="X-Authentik-Email"),
    x_authentik_name: Optional[str] = Header(None, alias="X-Authentik-Name"),
    x_authentik_uid: Optional[str] = Header(None, alias="X-Authentik-Uid"),
    x_authentik_groups: Optional[str] = Header(None, alias="X-Authentik-Groups"),
) -> AuthenticatedUser:
    """
    Extract user info from Authentik headers.

    When Authentik is not configured, returns a default demo user.
    In production with Authentik, the reverse proxy sets these headers.
    """
    # If Authentik headers are present, use them
    if x_authentik_email or x_authentik_uid:
        groups = x_authentik_groups.split("|") if x_authentik_groups else []
        return AuthenticatedUser(
            user_id=x_authentik_uid or "1",
            email=x_authentik_email,
            username=x_authentik_username,
            name=x_authentik_name,
            groups=groups,
        )

    # Default demo user when Authentik is not configured
    return AuthenticatedUser(
        user_id="1",
        email="demo@dreamops.local",
        username="demo",
        name="Demo User",
        groups=["admin"],
    )


async def get_user_from_request(request: Request) -> AuthenticatedUser:
    """
    Extract user from request headers (for use in non-dependency contexts).
    """
    return get_current_user(
        x_authentik_username=request.headers.get("X-Authentik-Username"),
        x_authentik_email=request.headers.get("X-Authentik-Email"),
        x_authentik_name=request.headers.get("X-Authentik-Name"),
        x_authentik_uid=request.headers.get("X-Authentik-Uid"),
        x_authentik_groups=request.headers.get("X-Authentik-Groups"),
    )
