"""Firebase authentication utilities for the backend."""

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
@lru_cache()
def get_firebase_app():
    """Initialize and return Firebase app instance."""
    try:
        # Check if already initialized
        if firebase_admin._apps:
            return firebase_admin.get_app()
            
        # Try to use service account key file if provided
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "./firebase-service-account-key.json")
        
        # Check both relative and absolute paths
        if not os.path.isabs(service_account_path):
            # Try relative to backend directory
            backend_dir = Path(__file__).parent.parent.parent.parent
            service_account_path = str(backend_dir / service_account_path)
        
        if os.path.exists(service_account_path):
            logger.info(f"Using Firebase service account key from: {service_account_path}")
            cred = credentials.Certificate(service_account_path)
            return firebase_admin.initialize_app(cred)
        else:
            logger.warning(f"Firebase service account key not found at: {service_account_path}")
            
        # Otherwise try to use Application Default Credentials
        # This works in Google Cloud environments
        cred = credentials.ApplicationDefault()
        return firebase_admin.initialize_app(cred, {
            'projectId': os.getenv('FIREBASE_PROJECT_ID', 'dreamops-558ef'),
        })
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        raise RuntimeError(f"Firebase initialization failed: {e}")

# Initialize on module load
try:
    firebase_app = get_firebase_app()
    logger.info("Firebase Admin SDK initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase on module load: {e}")
    firebase_app = None

# Security scheme for FastAPI
security = HTTPBearer()


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """Verify Firebase ID token and return decoded token."""
    token = credentials.credentials
    logger.info(f"Attempting to verify Firebase token (length: {len(token)})")
    
    if not firebase_app:
        logger.error("Firebase Admin SDK not initialized")
        raise HTTPException(status_code=500, detail="Authentication service not available")
    
    try:
        # Verify the ID token
        decoded_token = firebase_auth.verify_id_token(token)
        logger.debug(f"Successfully verified token for user: {decoded_token.get('email')}")
        return decoded_token
    except firebase_auth.ExpiredIdTokenError:
        logger.warning("Firebase token expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except firebase_auth.RevokedIdTokenError:
        logger.warning("Firebase token revoked")
        raise HTTPException(status_code=401, detail="Token has been revoked")
    except firebase_auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase token")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise HTTPException(status_code=401, detail="Could not validate credentials")


async def get_current_user_uid(
    decoded_token: Dict[str, Any] = Security(verify_firebase_token)
) -> str:
    """Get the current user's Firebase UID."""
    return decoded_token.get("uid")


async def get_current_user_email(
    decoded_token: Dict[str, Any] = Security(verify_firebase_token)
) -> Optional[str]:
    """Get the current user's email."""
    return decoded_token.get("email")


class FirebaseUser:
    """Firebase user information."""
    
    def __init__(self, uid: str, email: Optional[str] = None, 
                 display_name: Optional[str] = None, 
                 email_verified: bool = False):
        self.uid = uid
        self.email = email
        self.display_name = display_name
        self.email_verified = email_verified
    
    @classmethod
    def from_token(cls, decoded_token: Dict[str, Any]) -> "FirebaseUser":
        """Create FirebaseUser from decoded token."""
        return cls(
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email"),
            display_name=decoded_token.get("name"),
            email_verified=decoded_token.get("email_verified", False)
        )


async def get_current_firebase_user(
    decoded_token: Dict[str, Any] = Security(verify_firebase_token)
) -> FirebaseUser:
    """Get the current Firebase user."""
    return FirebaseUser.from_token(decoded_token)


# Optional: Function to verify without FastAPI dependency injection
def verify_token_manual(token: str) -> Dict[str, Any]:
    """Manually verify a Firebase token (useful for WebSocket connections)."""
    if not firebase_app:
        raise ValueError("Firebase Admin SDK not initialized")
    try:
        return firebase_auth.verify_id_token(token)
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise ValueError("Invalid token")


# Optional dependency for endpoints that don't require auth
async def get_optional_firebase_user(
    authorization: Optional[str] = None
) -> Optional[FirebaseUser]:
    """Get current Firebase user if token is provided, otherwise return None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    try:
        token = authorization.split(" ")[1]
        decoded = verify_token_manual(token)
        return FirebaseUser.from_token(decoded)
    except Exception:
        return None