"""
Authentication utilities for API routes
"""


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

security = HTTPBearer()


class User(BaseModel):
    """User model for authentication"""
    id: str
    email: str
    name: str | None = None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get the current authenticated user from the JWT token
    
    In production, this would:
    1. Verify the JWT token
    2. Extract user information
    3. Check against database
    
    For now, returns a mock user for testing
    """
    # Mock implementation - in production, verify JWT and get user from DB
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Mock user based on token
    # In production, decode JWT and get user info
    return User(
        id="user-123",
        email="test@example.com",
        name="Test User"
    )
