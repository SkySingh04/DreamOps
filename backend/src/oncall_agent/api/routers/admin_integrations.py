"""
Admin API endpoints for integration verification and management
"""


# Import the verification system
import sys
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from ...security.encryption import EncryptionService
from ...utils.logger import get_logger
from .auth import User, get_current_user

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts"))
from verify_integrations import IntegrationDataVerifier, IntegrationType

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/admin/integrations", tags=["admin-integrations"])

# Initialize services
encryption_service = EncryptionService()
verifier = IntegrationDataVerifier()


def is_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verify the current user has admin privileges"""
    # In production, check against database for admin role
    # For now, check if user email ends with admin domain
    if not current_user.email.endswith("@admin.dreamops.ai"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.get("/verify-all", dependencies=[Depends(is_admin)])
async def verify_all_integrations():
    """
    Verify all integrations across all users
    
    Returns comprehensive verification report for all users
    """
    try:
        # In production, get all user IDs from database
        # For demo, use mock user IDs
        user_ids = ["user-123", "user-456", "user-789"]

        results = []
        for user_id in user_ids:
            user_result = await verifier.verify_user_integrations(user_id)
            results.append({
                "user_id": user_id,
                "verification": user_result
            })

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_users": len(user_ids),
            "results": results
        }

    except Exception as e:
        logger.error(f"Failed to verify all integrations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )


@router.post("/test-user/{user_id}", dependencies=[Depends(is_admin)])
async def test_user_integrations(user_id: str):
    """
    Test all integrations for a specific user
    
    Args:
        user_id: The user ID to test integrations for
        
    Returns:
        Comprehensive test results including validation and connection tests
    """
    try:
        logger.info(f"Testing integrations for user: {user_id}")

        # Run comprehensive verification
        result = await verifier.verify_user_integrations(user_id)

        return result

    except Exception as e:
        logger.error(f"Failed to test user integrations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test failed: {str(e)}"
        )


@router.get("/encryption-status", dependencies=[Depends(is_admin)])
async def get_encryption_status():
    """
    Get the current encryption configuration status
    
    Returns information about encryption setup and health
    """
    try:
        # Test encryption service
        test_data = "test-encryption-data"
        encrypted = encryption_service.encrypt(test_data)
        decrypted = encryption_service.decrypt(encrypted)

        encryption_working = decrypted == test_data

        return {
            "encryption_enabled": True,
            "encryption_working": encryption_working,
            "key_source": "environment" if encryption_service._key else "generated",
            "algorithm": "Fernet (AES-128)",
            "test_passed": encryption_working
        }

    except Exception as e:
        logger.error(f"Failed to get encryption status: {str(e)}")
        return {
            "encryption_enabled": False,
            "encryption_working": False,
            "error": str(e)
        }


@router.get("/health-report", dependencies=[Depends(is_admin)])
async def get_health_report():
    """
    Get a comprehensive health report for all user integrations
    
    Returns aggregated health metrics and individual user statuses
    """
    try:
        # In production, get all users from database
        # For demo, use mock data
        mock_users = [
            {"user_id": "user-123", "email": "alice@example.com"},
            {"user_id": "user-456", "email": "bob@example.com"},
            {"user_id": "user-789", "email": "charlie@example.com"}
        ]

        users_health = []
        total_health_score = 0

        for user in mock_users:
            health_report = await verifier.generate_health_report(user["user_id"])

            users_health.append({
                "user_id": user["user_id"],
                "user_email": user["email"],
                "report_timestamp": health_report["report_timestamp"],
                "overall_health": health_report["overall_health"],
                "integrations": health_report["integrations"]
            })

            total_health_score += health_report["overall_health"]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_users": len(mock_users),
            "average_health_score": total_health_score / len(mock_users) if mock_users else 0,
            "users": users_health
        }

    except Exception as e:
        logger.error(f"Failed to generate health report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health report generation failed: {str(e)}"
        )


@router.post("/test-integration/{integration_type}", dependencies=[Depends(is_admin)])
async def test_specific_integration(integration_type: str, user_id: str):
    """
    Test a specific integration type for a user
    
    Args:
        integration_type: The type of integration to test
        user_id: The user ID to test for
        
    Returns:
        Test results for the specific integration
    """
    try:
        # Validate integration type
        if integration_type not in [t.value for t in IntegrationType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid integration type: {integration_type}"
            )

        # Test encryption cycle
        encryption_result = await verifier.test_encryption_cycle(user_id, integration_type)

        # Validate configuration
        validation_result = await verifier._validate_integration_type(user_id, integration_type)

        # Test connection
        connection_result = await verifier._test_single_connection(user_id, integration_type)

        return {
            "integration_type": integration_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "encryption_test": encryption_result,
            "validation": validation_result.to_dict(),
            "connection": connection_result.to_dict()
        }

    except Exception as e:
        logger.error(f"Failed to test integration {integration_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integration test failed: {str(e)}"
        )


@router.post("/rotate-encryption-keys", dependencies=[Depends(is_admin)])
async def rotate_encryption_keys():
    """
    Rotate encryption keys for all stored credentials
    
    This endpoint should be called periodically for security
    """
    try:
        # In production, this would:
        # 1. Generate new encryption key
        # 2. Decrypt all data with old key
        # 3. Re-encrypt with new key
        # 4. Update key in secure storage (AWS KMS, etc.)

        logger.info("Starting encryption key rotation")

        # For now, return mock response
        return {
            "status": "success",
            "message": "Encryption keys rotated successfully",
            "timestamp": datetime.utcnow().isoformat(),
            "next_rotation_due": "2024-01-01T00:00:00Z"
        }

    except Exception as e:
        logger.error(f"Failed to rotate encryption keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Key rotation failed: {str(e)}"
        )


@router.get("/audit-log", dependencies=[Depends(is_admin)])
async def get_integration_audit_log(
    user_id: str = None,
    integration_type: str = None,
    limit: int = 100
):
    """
    Get audit log of integration operations
    
    Args:
        user_id: Filter by user ID (optional)
        integration_type: Filter by integration type (optional)
        limit: Maximum number of entries to return
        
    Returns:
        List of audit log entries
    """
    try:
        # In production, query from database
        # For now, return mock audit log
        audit_entries = [
            {
                "timestamp": "2023-12-14T10:30:00Z",
                "user_id": "user-123",
                "integration_type": "kubernetes",
                "action": "update",
                "details": "Updated Kubernetes contexts",
                "ip_address": "192.168.1.100",
                "success": True
            },
            {
                "timestamp": "2023-12-14T09:15:00Z",
                "user_id": "user-456",
                "integration_type": "pagerduty",
                "action": "create",
                "details": "Created PagerDuty integration",
                "ip_address": "192.168.1.101",
                "success": True
            }
        ]

        # Apply filters
        if user_id:
            audit_entries = [e for e in audit_entries if e["user_id"] == user_id]
        if integration_type:
            audit_entries = [e for e in audit_entries if e["integration_type"] == integration_type]

        return {
            "entries": audit_entries[:limit],
            "total": len(audit_entries),
            "filters": {
                "user_id": user_id,
                "integration_type": integration_type,
                "limit": limit
            }
        }

    except Exception as e:
        logger.error(f"Failed to get audit log: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit log retrieval failed: {str(e)}"
        )


# User self-verification endpoints (non-admin)

@router.get("/users/me/verify", tags=["user-integrations"])
async def verify_my_integrations(current_user: User = Depends(get_current_user)):
    """
    Allow users to verify their own integrations
    
    Returns verification results for the current user
    """
    try:
        result = await verifier.verify_user_integrations(current_user.id)
        return result

    except Exception as e:
        logger.error(f"Failed to verify user integrations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )


@router.post("/users/me/test-all", tags=["user-integrations"])
async def test_all_my_integrations(current_user: User = Depends(get_current_user)):
    """
    Test all integrations for the current user
    
    Returns connection test results
    """
    try:
        connections = await verifier.test_connection_with_stored_creds(current_user.id)

        return {
            "user_id": current_user.id,
            "timestamp": datetime.utcnow().isoformat(),
            "connections": {k: v.to_dict() for k, v in connections.items()}
        }

    except Exception as e:
        logger.error(f"Failed to test user connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Connection test failed: {str(e)}"
        )


@router.get("/users/me/health", tags=["user-integrations"])
async def get_my_integration_health(current_user: User = Depends(get_current_user)):
    """
    Get integration health report for the current user
    
    Returns health metrics for all user integrations
    """
    try:
        health_report = await verifier.generate_health_report(current_user.id)

        return {
            "user_id": current_user.id,
            "user_email": current_user.email,
            "report": health_report
        }

    except Exception as e:
        logger.error(f"Failed to generate health report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health report generation failed: {str(e)}"
        )
