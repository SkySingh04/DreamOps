"""Firebase authentication API endpoints."""

import os
from datetime import datetime
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from src.oncall_agent.utils.logger import get_logger

try:
    from src.oncall_agent.security.firebase_auth import (
        FirebaseUser,
        get_current_firebase_user,
    )
except Exception as e:
    logger = get_logger(__name__)
    logger.error(f"Failed to import Firebase auth utilities: {e}")
    raise


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["firebase-authentication"])

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", ""))


@router.get("/firebase-status")
async def firebase_status():
    """Check Firebase Admin SDK status."""
    try:
        from src.oncall_agent.security.firebase_auth import firebase_app
        return {
            "status": "ok" if firebase_app else "not_initialized",
            "firebase_project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "service_account_exists": os.path.exists(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "./firebase-service-account-key.json"))
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/test-db")
async def test_database_connection():
    """Test database connection and list users."""
    try:
        conn = await get_db()

        # Test connection
        version = await conn.fetchval("SELECT version()")

        # Count users
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")

        # Get all users with their setup status
        users = await conn.fetch("""
            SELECT u.id, u.firebase_uid, u.email, u.created_at,
                   COUNT(usr.id) as setup_requirements_count
            FROM users u
            LEFT JOIN user_setup_requirements usr ON u.id = usr.user_id
            GROUP BY u.id, u.firebase_uid, u.email, u.created_at
            ORDER BY u.created_at DESC
        """)

        await conn.close()

        return {
            "status": "connected",
            "database_version": version,
            "user_count": user_count,
            "users": [dict(u) for u in users] if users else []
        }
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


class FirebaseSignInRequest(BaseModel):
    uid: str
    email: EmailStr | None
    name: str | None


class FirebaseSignUpRequest(BaseModel):
    uid: str
    email: EmailStr
    name: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    user_id: int | None = None
    is_setup_complete: bool | None = None


class UserResponse(BaseModel):
    user: dict[str, Any]


class SetupStatusResponse(BaseModel):
    is_setup_complete: bool
    llm_configured: bool
    integrations_configured: dict[str, bool]
    missing_requirements: list[str]
    setup_progress_percentage: float


async def get_db():
    """Get database connection."""
    # Remove channel_binding parameter which asyncpg doesn't support
    clean_url = DATABASE_URL
    if "&channel_binding=require" in clean_url:
        clean_url = clean_url.replace("&channel_binding=require", "")
    elif "?channel_binding=require" in clean_url:
        clean_url = clean_url.replace("?channel_binding=require", "")

    logger.debug("Connecting to database...")
    return await asyncpg.connect(clean_url)


@router.post("/firebase-signin", response_model=AuthResponse)
async def firebase_sign_in(
    request: FirebaseSignInRequest,
    firebase_user: FirebaseUser = Depends(get_current_firebase_user)
) -> AuthResponse:
    """Handle Firebase sign in and sync with database."""
    conn = await get_db()
    try:
        # Ensure we're using the Firebase user's actual UID
        uid = firebase_user.uid

        # Check if user exists
        user = await conn.fetchrow(
            "SELECT id, firebase_uid, is_setup_complete FROM users WHERE firebase_uid = $1 OR email = $2",
            uid,
            firebase_user.email or request.email
        )

        if not user:
            # User doesn't exist in our database, create them
            logger.info(f"Creating new user for Firebase UID: {uid}")

            user_id = await conn.fetchval(
                """
                INSERT INTO users (
                    firebase_uid, email, name, password_hash, role, is_setup_complete, 
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                uid,
                firebase_user.email or request.email,
                firebase_user.display_name or request.name or "User",
                'firebase_auth',  # Placeholder for Firebase authenticated users
                'member',  # Default role
                False,
                datetime.utcnow(),
                datetime.utcnow()
            )

            # Create setup requirements record
            await conn.execute(
                """
                INSERT INTO user_setup_requirements (
                    user_id, requirement_type, is_completed, is_required,
                    created_at, updated_at
                ) VALUES 
                ($1, 'llm_config', false, true, $2, $3),
                ($1, 'pagerduty', false, true, $2, $3),
                ($1, 'kubernetes', false, true, $2, $3)
                """,
                user_id,
                datetime.utcnow(),
                datetime.utcnow()
            )

            return AuthResponse(
                success=True,
                message="Sign in successful",
                user_id=user_id,
                is_setup_complete=False
            )
        elif not user['firebase_uid']:
            # User exists but firebase_uid is null, update it
            logger.info(f"Updating null firebase_uid for existing user {user['id']}")
            await conn.execute(
                "UPDATE users SET firebase_uid = $1, updated_at = $2 WHERE id = $3",
                uid,
                datetime.utcnow(),
                user['id']
            )
            return AuthResponse(
                success=True,
                message="Sign in successful",
                user_id=user['id'],
                is_setup_complete=user['is_setup_complete']
            )
        else:
            # User exists with firebase_uid
            logger.info(f"User {user['id']} signing in")

        # Update last login
        await conn.execute(
            "UPDATE users SET updated_at = $1 WHERE id = $2",
            datetime.utcnow(),
            user['id']
        )

        return AuthResponse(
            success=True,
            message="Sign in successful",
            user_id=user['id'],
            is_setup_complete=user['is_setup_complete'] or False
        )

    except Exception as e:
        logger.error(f"Firebase sign in error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await conn.close()


@router.post("/firebase-signup", response_model=AuthResponse)
async def firebase_sign_up(
    request: FirebaseSignUpRequest,
    firebase_user: FirebaseUser = Depends(get_current_firebase_user)
) -> AuthResponse:
    """Handle Firebase sign up and create user in database."""
    logger.info(f"Firebase signup called for UID: {firebase_user.uid}, email: {firebase_user.email}")
    conn = await get_db()
    try:
        # Use the Firebase user's actual UID
        uid = firebase_user.uid

        # Check if user already exists
        existing_user = await conn.fetchrow(
            "SELECT id, firebase_uid FROM users WHERE firebase_uid = $1 OR email = $2",
            uid,
            firebase_user.email or request.email
        )

        if existing_user:
            # User already exists
            logger.info(f"User already exists with ID: {existing_user['id']}")
            # Update the firebase_uid if it's null
            if not existing_user.get('firebase_uid'):
                logger.info(f"Updating null firebase_uid for user {existing_user['id']}")
                await conn.execute(
                    "UPDATE users SET firebase_uid = $1, updated_at = $2 WHERE id = $3",
                    uid,
                    datetime.utcnow(),
                    existing_user['id']
                )
            return AuthResponse(
                success=True,
                message="User already exists",
                user_id=existing_user['id'],
                is_setup_complete=False
            )

        # Create new user with Firebase UID (password_hash is required, so set a placeholder)
        logger.info(f"Creating new user with Firebase UID: {uid}, email: {firebase_user.email or request.email}")

        # Start a transaction to ensure atomicity
        async with conn.transaction():
            user_id = await conn.fetchval(
                """
                INSERT INTO users (
                    firebase_uid, email, name, password_hash, role, is_setup_complete, 
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                uid,
                firebase_user.email or request.email,
                firebase_user.display_name or request.name,
                'firebase_auth',  # Placeholder for Firebase authenticated users
                'member',  # Default role
                False,
                datetime.utcnow(),
                datetime.utcnow()
            )
            logger.info(f"Successfully created user with ID: {user_id}")

            # Create setup requirements record
            try:
                await conn.execute(
                    """
                    INSERT INTO user_setup_requirements (
                        user_id, requirement_type, is_completed, is_required,
                        created_at, updated_at
                    ) VALUES 
                    ($1, 'llm_config', false, true, $2, $3),
                    ($1, 'pagerduty', false, true, $2, $3),
                    ($1, 'kubernetes', false, true, $2, $3)
                    """,
                    user_id,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
            except Exception as req_error:
                logger.warning(f"Failed to create setup requirements: {req_error}")
                # Continue anyway - the user was created successfully

        logger.info(f"Successfully created setup requirements for user {user_id}")

        return AuthResponse(
            success=True,
            message="Account created successfully",
            user_id=user_id,
            is_setup_complete=False
        )

    except asyncpg.UniqueViolationError as e:
        logger.error(f"Unique constraint violation during signup: {e}")
        # Try to find the existing user
        existing = await conn.fetchrow(
            "SELECT id, firebase_uid FROM users WHERE email = $1",
            firebase_user.email or request.email
        )
        if existing and not existing['firebase_uid']:
            # Update firebase_uid for existing user
            logger.info(f"Updating firebase_uid for existing user {existing['id']}")
            await conn.execute(
                "UPDATE users SET firebase_uid = $1, updated_at = $2 WHERE id = $3",
                uid,
                datetime.utcnow(),
                existing['id']
            )
            await conn.close()
            return AuthResponse(
                success=True,
                message="User updated with Firebase UID",
                user_id=existing['id'],
                is_setup_complete=False
            )
        raise HTTPException(status_code=409, detail="User already exists")
    except Exception as e:
        logger.error(f"Firebase sign up error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        await conn.close()


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    firebase_user: FirebaseUser = Depends(get_current_firebase_user)
) -> UserResponse:
    """Get current user information."""
    conn = await get_db()
    try:
        user = await conn.fetchrow(
            """
            SELECT id, firebase_uid, email, name, llm_provider, 
                   is_setup_complete, created_at
            FROM users 
            WHERE firebase_uid = $1
            """,
            firebase_user.uid
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            user={
                "id": user['id'],
                "firebase_uid": user['firebase_uid'],
                "email": user['email'],
                "name": user['name'],
                "llm_provider": user['llm_provider'],
                "is_setup_complete": user['is_setup_complete'],
                "created_at": user['created_at'].isoformat() if user['created_at'] else None
            }
        )

    except Exception as e:
        logger.error(f"Get current user error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await conn.close()


@router.get("/setup-status", response_model=SetupStatusResponse)
async def get_setup_status(
    firebase_user: FirebaseUser = Depends(get_current_firebase_user)
) -> SetupStatusResponse:
    """Get user's setup completion status."""
    conn = await get_db()
    try:
        # Get user
        user = await conn.fetchrow(
            "SELECT id, is_setup_complete FROM users WHERE firebase_uid = $1",
            firebase_user.uid
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get setup requirements
        requirements_rows = await conn.fetch(
            """
            SELECT requirement_type, is_completed
            FROM user_setup_requirements 
            WHERE user_id = $1
            """,
            user['id']
        )

        # Convert to dict
        requirements = {
            'llm_provider_configured': False,
            'pagerduty_configured': False,
            'kubernetes_configured': False,
            'github_configured': False,
            'notion_configured': False
        }

        for row in requirements_rows:
            if row['requirement_type'] == 'llm_config':
                requirements['llm_provider_configured'] = row['is_completed']
            elif row['requirement_type'] == 'pagerduty':
                requirements['pagerduty_configured'] = row['is_completed']
            elif row['requirement_type'] == 'kubernetes':
                requirements['kubernetes_configured'] = row['is_completed']
            elif row['requirement_type'] == 'github':
                requirements['github_configured'] = row['is_completed']
            elif row['requirement_type'] == 'notion':
                requirements['notion_configured'] = row['is_completed']

        if not requirements:
            # Create default requirements if not exist
            await conn.execute(
                """
                INSERT INTO user_setup_requirements (
                    user_id, requirement_type, is_completed, is_required,
                    created_at, updated_at
                ) VALUES 
                ($1, 'llm_config', false, true, $2, $3),
                ($1, 'pagerduty', false, true, $2, $3),
                ($1, 'kubernetes', false, true, $2, $3)
                """,
                user['id'],
                datetime.utcnow(),
                datetime.utcnow()
            )
            requirements = {
                'llm_provider_configured': False,
                'pagerduty_configured': False,
                'kubernetes_configured': False,
                'github_configured': False,
                'notion_configured': False
            }

        # Calculate setup progress
        required_items = ['llm_provider_configured', 'pagerduty_configured', 'kubernetes_configured']
        completed_required = sum(1 for item in required_items if requirements.get(item, False))
        progress = (completed_required / len(required_items)) * 100

        # Determine missing requirements
        missing = []
        if not requirements['llm_provider_configured']:
            missing.append('llm_provider')
        if not requirements['pagerduty_configured']:
            missing.append('pagerduty')
        if not requirements['kubernetes_configured']:
            missing.append('kubernetes')

        return SetupStatusResponse(
            is_setup_complete=user['is_setup_complete'] or False,
            llm_configured=requirements['llm_provider_configured'] or False,
            integrations_configured={
                'pagerduty': requirements['pagerduty_configured'] or False,
                'kubernetes': requirements['kubernetes_configured'] or False,
                'github': requirements.get('github_configured', False),
                'notion': requirements.get('notion_configured', False)
            },
            missing_requirements=missing,
            setup_progress_percentage=progress
        )

    except Exception as e:
        logger.error(f"Get setup status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        await conn.close()



# Note: The /llm-config endpoint has been moved to auth_setup.py to avoid duplication
# This entire function has been removed to prevent route conflicts


# Remove the old JWT-based endpoints and keep only Firebase-based ones
