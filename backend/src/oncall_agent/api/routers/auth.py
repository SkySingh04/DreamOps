"""Authentication API endpoints."""

import os
from datetime import datetime, timedelta

import asyncpg
import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr

from src.oncall_agent.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# JWT settings
JWT_SECRET = os.getenv("AUTH_SECRET", "your-super-secret-jwt-signing-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 1

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", ""))


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    invite_id: int | None = None


class SignInResponse(BaseModel):
    success: bool
    message: str
    user_id: int | None = None
    token: str | None = None
    is_setup_complete: bool | None = None


class SignUpResponse(BaseModel):
    success: bool
    message: str
    user_id: int | None = None
    token: str | None = None


class UserInfo(BaseModel):
    id: int
    email: str
    name: str | None
    role: str
    team_id: int | None
    is_setup_complete: bool
    llm_provider: str | None


async def get_db_connection():
    """Get database connection."""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection failed")


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_jwt_token(user_id: int, is_setup_complete: bool) -> str:
    """Create JWT token for user."""
    payload = {
        "user": {"id": user_id},
        "isSetupComplete": is_setup_complete,
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request) -> dict:
    """Get current user from JWT token in cookies."""
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_jwt_token(session_cookie)
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")


@router.post("/signin", response_model=SignInResponse)
async def sign_in(
    request: SignInRequest,
    response: Response
) -> SignInResponse:
    """Sign in user."""
    conn = await get_db_connection()

    try:
        # Get user with team information
        query = """
            SELECT u.id, u.name, u.email, u.password_hash, u.role, 
                   u.is_setup_complete, u.llm_provider,
                   tm.team_id, t.id as team_id_check
            FROM users u
            LEFT JOIN team_members tm ON u.id = tm.user_id
            LEFT JOIN teams t ON tm.team_id = t.id
            WHERE u.email = $1 AND u.deleted_at IS NULL
            LIMIT 1
        """

        user_row = await conn.fetchrow(query, request.email)

        if not user_row:
            return SignInResponse(
                success=False,
                message="Invalid email or password"
            )

        # Verify password
        if not verify_password(request.password, user_row['password_hash']):
            return SignInResponse(
                success=False,
                message="Invalid email or password"
            )

        # Log activity
        if user_row['team_id']:
            await conn.execute(
                """
                INSERT INTO activity_logs (team_id, user_id, action, ip_address)
                VALUES ($1, $2, 'SIGN_IN', '')
                """,
                user_row['team_id'], user_row['id']
            )

        # Create JWT token
        token = create_jwt_token(user_row['id'], user_row['is_setup_complete'])

        # Set session cookie
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400  # 1 day
        )

        return SignInResponse(
            success=True,
            message="Sign in successful",
            user_id=user_row['id'],
            token=token,
            is_setup_complete=user_row['is_setup_complete']
        )

    except Exception as e:
        logger.error(f"Sign in error: {str(e)}")
        return SignInResponse(
            success=False,
            message="An error occurred during sign in"
        )
    finally:
        await conn.close()


@router.post("/signup", response_model=SignUpResponse)
async def sign_up(
    request: SignUpRequest,
    response: Response
) -> SignUpResponse:
    """Sign up new user."""
    conn = await get_db_connection()

    try:
        # Check if user already exists
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1",
            request.email
        )

        if existing:
            return SignUpResponse(
                success=False,
                message="User with this email already exists"
            )

        # Hash password
        password_hash = hash_password(request.password)

        # Start transaction
        async with conn.transaction():
            # Create user
            user_id = await conn.fetchval(
                """
                INSERT INTO users (name, email, password_hash, role)
                VALUES ($1, $2, $3, 'owner')
                RETURNING id
                """,
                request.name, request.email, password_hash
            )

            team_id = None

            # Handle invitation if provided
            if request.invite_id:
                invitation = await conn.fetchrow(
                    """
                    SELECT team_id, role FROM invitations
                    WHERE id = $1 AND email = $2 AND status = 'pending'
                    """,
                    request.invite_id, request.email
                )

                if invitation:
                    team_id = invitation['team_id']
                    role = invitation['role']

                    # Update invitation status
                    await conn.execute(
                        """
                        UPDATE invitations SET status = 'accepted'
                        WHERE id = $1
                        """,
                        request.invite_id
                    )
                else:
                    # Invalid invitation
                    raise Exception("Invalid or expired invitation")
            else:
                # Create new team
                team_id = await conn.fetchval(
                    """
                    INSERT INTO teams (name, subscription_status)
                    VALUES ($1, 'trial')
                    RETURNING id
                    """,
                    f"{request.email}'s Team"
                )
                role = 'owner'

            # Add user to team
            await conn.execute(
                """
                INSERT INTO team_members (user_id, team_id, role)
                VALUES ($1, $2, $3)
                """,
                user_id, team_id, role
            )

            # Initialize setup requirements
            requirements = [
                ('llm_config', True),
                ('pagerduty', True),
                ('kubernetes', True),
                ('github', False),
                ('notion', False),
                ('grafana', False)
            ]

            for req_type, is_required in requirements:
                await conn.execute(
                    """
                    INSERT INTO user_setup_requirements 
                    (user_id, requirement_type, is_required, is_completed)
                    VALUES ($1, $2, $3, false)
                    """,
                    user_id, req_type, is_required
                )

            # Log activity
            await conn.execute(
                """
                INSERT INTO activity_logs (team_id, user_id, action, ip_address)
                VALUES ($1, $2, 'SIGN_UP', '')
                """,
                team_id, user_id
            )

        # Create JWT token
        token = create_jwt_token(user_id, False)  # New users need setup

        # Set session cookie
        response.set_cookie(
            key="session",
            value=token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=86400  # 1 day
        )

        return SignUpResponse(
            success=True,
            message="Sign up successful",
            user_id=user_id,
            token=token
        )

    except Exception as e:
        logger.error(f"Sign up error: {str(e)}")
        return SignUpResponse(
            success=False,
            message=str(e) if "invitation" in str(e).lower() else "Failed to create account"
        )
    finally:
        await conn.close()


@router.post("/signout")
async def sign_out(
    response: Response,
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Sign out user."""
    conn = await get_db_connection()

    try:
        # Log activity
        user_id = current_user["user"]["id"]

        # Get user's team
        team_id = await conn.fetchval(
            """
            SELECT team_id FROM team_members WHERE user_id = $1 LIMIT 1
            """,
            user_id
        )

        if team_id:
            await conn.execute(
                """
                INSERT INTO activity_logs (team_id, user_id, action, ip_address)
                VALUES ($1, $2, 'SIGN_OUT', '')
                """,
                team_id, user_id
            )

        # Clear session cookie
        response.delete_cookie("session")

        return {"success": True, "message": "Signed out successfully"}

    except Exception as e:
        logger.error(f"Sign out error: {str(e)}")
        return {"success": False, "message": "Error during sign out"}
    finally:
        await conn.close()


@router.get("/me", response_model=UserInfo)
async def get_me(
    current_user: dict = Depends(get_current_user)
) -> UserInfo:
    """Get current user information."""
    conn = await get_db_connection()

    try:
        user_id = current_user["user"]["id"]

        query = """
            SELECT u.id, u.name, u.email, u.role, u.is_setup_complete, u.llm_provider,
                   tm.team_id
            FROM users u
            LEFT JOIN team_members tm ON u.id = tm.user_id
            WHERE u.id = $1 AND u.deleted_at IS NULL
            LIMIT 1
        """

        user_row = await conn.fetchrow(query, user_id)

        if not user_row:
            raise HTTPException(status_code=404, detail="User not found")

        return UserInfo(
            id=user_row['id'],
            email=user_row['email'],
            name=user_row['name'],
            role=user_row['role'],
            team_id=user_row['team_id'],
            is_setup_complete=user_row['is_setup_complete'],
            llm_provider=user_row['llm_provider']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user information")
    finally:
        await conn.close()


@router.get("/check-session")
async def check_session(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Check if user session is valid."""
    return {
        "valid": True,
        "user_id": current_user["user"]["id"],
        "is_setup_complete": current_user.get("isSetupComplete", False)
    }
