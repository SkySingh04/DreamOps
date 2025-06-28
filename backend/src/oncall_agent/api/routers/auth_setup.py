"""Authentication and setup flow API endpoints."""

import os
from datetime import datetime
from typing import Optional
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.oncall_agent.api.models.auth import (
    LLMConfigRequest,
    LLMConfigResponse,
    TestLLMRequest,
    TestLLMResponse,
    SetupStatusResponse,
    SetupRequirement,
    ValidationResult,
    UserSetupValidationResponse,
    CompleteSetupRequest,
    CompleteSetupResponse,
    SetupRequirementsResponse,
    UserWithSetup,
    LLMProvider,
    SetupRequirementType,
)
from src.oncall_agent.services.llm_validator import LLMValidator
from src.oncall_agent.services.user_config import UserConfigService
from src.oncall_agent.utils.logger import get_logger
from src.oncall_agent.security.firebase_auth import get_current_firebase_user, FirebaseUser
import asyncpg

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("POSTGRES_URL", ""))

async def get_db_connection():
    """Get database connection."""
    # Remove channel_binding parameter which asyncpg doesn't support
    clean_url = DATABASE_URL
    if "&channel_binding=require" in clean_url:
        clean_url = clean_url.replace("&channel_binding=require", "")
    elif "?channel_binding=require" in clean_url:
        clean_url = clean_url.replace("?channel_binding=require", "")
    
    return await asyncpg.connect(clean_url)

# This would normally come from your auth system
async def get_current_user(firebase_user: FirebaseUser = Depends(get_current_firebase_user)) -> dict:
    """Get current user from Firebase authentication.
    
    This fetches the user from the database based on their Firebase UID.
    """
    logger.info(f"Getting current user for Firebase UID: {firebase_user.uid}, email: {firebase_user.email}")
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow(
            "SELECT id, firebase_uid, email, name, team_id, role FROM users WHERE firebase_uid = $1",
            firebase_user.uid
        )
        
        if not user:
            logger.error(f"User not found in database for Firebase UID: {firebase_user.uid}")
            # Let's also check if there are any users in the database
            user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            logger.info(f"Total users in database: {user_count}")
            raise HTTPException(status_code=404, detail=f"User not found for Firebase UID: {firebase_user.uid}")
        
        logger.info(f"Found user: {user['email']} with ID: {user['id']}")
        return {
            "id": user['id'],
            "email": user['email'],
            "team_id": user['team_id'],
            "role": user['role']
        }
    finally:
        await conn.close()

# This would normally come from your database dependency
async def get_db() -> AsyncSession:
    """Get database session.
    
    In a real implementation, this would return an actual database session.
    """
    # TODO: Implement real database session
    pass


logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# Initialize services
llm_validator = LLMValidator()
user_config_service = UserConfigService()


@router.post("/llm-config", response_model=LLMConfigResponse)
async def setup_llm_config(
    config: LLMConfigRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> LLMConfigResponse:
    """Set up LLM configuration during signup/onboarding.
    
    This endpoint:
    1. Validates the API key with the provider
    2. Stores the encrypted configuration
    3. Updates user setup status
    4. Logs the configuration change
    """
    try:
        # Validate the API key
        validation_result = await llm_validator.validate_api_key(
            provider=config.provider,
            api_key=config.api_key,
            model=config.model
        )
        
        if not validation_result.valid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid API key: {validation_result.error}"
            )
        
        # Store the configuration
        stored_config = await user_config_service.store_llm_config(
            user_id=user["id"],
            team_id=user["team_id"],
            config=config,
            validation_result=validation_result
        )
        
        # Update setup requirement status
        background_tasks.add_task(
            user_config_service.mark_requirement_complete,
            user_id=user["id"],
            requirement_type=SetupRequirementType.LLM_CONFIG
        )
        
        logger.info(f"LLM configuration stored for user {user['id']}")
        
        return LLMConfigResponse(
            id=stored_config.id,
            provider=stored_config.provider,
            key_name=stored_config.name,
            model=stored_config.model,
            is_validated=stored_config.is_validated,
            validated_at=stored_config.validated_at,
            created_at=stored_config.created_at,
            updated_at=stored_config.updated_at
        )
        
    except Exception as e:
        logger.error(f"Failed to setup LLM config: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save configuration")


@router.post("/test-llm", response_model=TestLLMResponse)
async def test_llm_connection(
    request: TestLLMRequest,
    user: dict = Depends(get_current_user)
) -> TestLLMResponse:
    """Test LLM API key validity without storing it.
    
    Used during setup flow to validate keys before saving.
    """
    try:
        result = await llm_validator.validate_api_key(
            provider=request.provider,
            api_key=request.api_key,
            model=request.model
        )
        
        return TestLLMResponse(
            valid=result.valid,
            error=result.error,
            model_info=result.model_info,
            rate_limit_info=result.rate_limit_info
        )
        
    except Exception as e:
        logger.error(f"Error testing LLM connection: {str(e)}")
        return TestLLMResponse(
            valid=False,
            error=f"Connection test failed: {str(e)}"
        )


# Removed get_setup_status endpoint to avoid conflict with firebase_auth.py
# The setup-status endpoint is now handled in firebase_auth.py


@router.get("/validate-setup", response_model=UserSetupValidationResponse)
async def validate_user_setup(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserSetupValidationResponse:
    """Validate user's complete setup status.
    
    This endpoint:
    1. Tests LLM API key validity
    2. Tests all configured integrations
    3. Returns validation results
    4. Updates validation timestamps
    """
    try:
        validation_results = []
        requires_fix = []
        
        # Validate LLM configuration
        llm_validation = await user_config_service.validate_llm_config(
            user_id=user["id"]
        )
        
        validation_results.append(llm_validation)
        if not llm_validation.is_successful:
            requires_fix.append("llm_config")
        
        # Validate required integrations
        integration_validations = await user_config_service.validate_integrations(
            user_id=user["id"]
        )
        
        for validation in integration_validations:
            validation_results.append(validation)
            if not validation.is_successful and validation.target in ["pagerduty", "kubernetes"]:
                requires_fix.append(validation.target)
        
        # Update last validation timestamp
        background_tasks.add_task(
            user_config_service.update_last_validation,
            user_id=user["id"]
        )
        
        is_valid = len(requires_fix) == 0
        
        return UserSetupValidationResponse(
            is_valid=is_valid,
            validation_results=validation_results,
            requires_fix=requires_fix,
            last_validation_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error validating setup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate setup")


@router.get("/setup-requirements", response_model=SetupRequirementsResponse)
async def get_setup_requirements() -> SetupRequirementsResponse:
    """Get what's required for complete setup.
    
    Returns lists of required, optional, and coming soon integrations.
    """
    return SetupRequirementsResponse(
        required=["llm_config", "pagerduty", "kubernetes"],
        optional=["github", "notion", "grafana"],
        coming_soon=["datadog"]
    )


@router.post("/complete-setup", response_model=CompleteSetupResponse)
async def complete_user_setup(
    request: CompleteSetupRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CompleteSetupResponse:
    """Mark user setup as complete after all validations.
    
    This endpoint:
    1. Verifies all required items are configured
    2. Updates user's setup status
    3. Records completion timestamp
    """
    try:
        # Check if all requirements are met
        setup_status = await user_config_service.get_user_setup_status(
            user_id=user["id"]
        )
        
        if not request.force and len(setup_status.missing_requirements) > 0:
            return CompleteSetupResponse(
                success=False,
                is_setup_complete=False,
                message=f"Missing required items: {', '.join(setup_status.missing_requirements)}"
            )
        
        # Mark setup as complete
        completion_time = await user_config_service.mark_setup_complete(
            user_id=user["id"]
        )
        
        return CompleteSetupResponse(
            success=True,
            is_setup_complete=True,
            message="Setup completed successfully",
            setup_completed_at=completion_time
        )
        
    except Exception as e:
        logger.error(f"Error completing setup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to complete setup")


@router.get("/user-info", response_model=UserWithSetup)
async def get_user_with_setup_info(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserWithSetup:
    """Get current user information including setup status.
    
    Returns user profile with LLM configuration and setup completion status.
    """
    try:
        user_info = await user_config_service.get_user_with_setup(
            user_id=user["id"]
        )
        
        return user_info
        
    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user information")