"""Authentication and setup flow models."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class SetupRequirementType(str, Enum):
    """Types of setup requirements."""
    LLM_CONFIG = "llm_config"
    PAGERDUTY = "pagerduty"
    KUBERNETES = "kubernetes"
    GITHUB = "github"
    NOTION = "notion"
    GRAFANA = "grafana"
    DATADOG = "datadog"


class LLMConfigRequest(BaseModel):
    """Request model for LLM configuration."""
    provider: LLMProvider
    api_key: str = Field(..., min_length=1, description="API key for the provider")
    key_name: Optional[str] = Field(None, max_length=100, description="Optional name for the key")
    model: Optional[str] = Field(None, max_length=50, description="Specific model to use")


class LLMConfigResponse(BaseModel):
    """Response model for LLM configuration."""
    id: int
    provider: LLMProvider
    key_name: str
    model: Optional[str]
    is_validated: bool
    validated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class TestLLMRequest(BaseModel):
    """Request model for testing LLM connection."""
    provider: LLMProvider
    api_key: str = Field(..., min_length=1)
    model: Optional[str] = None


class TestLLMResponse(BaseModel):
    """Response model for LLM connection test."""
    valid: bool
    error: Optional[str] = None
    model_info: Optional[dict[str, Any]] = None
    rate_limit_info: Optional[dict[str, Any]] = None


class SetupRequirement(BaseModel):
    """Model for a setup requirement."""
    requirement_type: SetupRequirementType
    is_required: bool
    is_completed: bool
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SetupStatusResponse(BaseModel):
    """Response model for setup status."""
    is_setup_complete: bool
    llm_configured: bool
    llm_provider: Optional[LLMProvider] = None
    integrations_configured: dict[str, bool]
    setup_requirements: list[SetupRequirement]
    missing_requirements: list[str]
    setup_progress_percentage: float


class ValidationResult(BaseModel):
    """Result of a validation check."""
    validation_type: str
    target: str
    is_successful: bool
    error_message: Optional[str] = None
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSetupValidationResponse(BaseModel):
    """Response model for user setup validation."""
    is_valid: bool
    validation_results: list[ValidationResult]
    requires_fix: list[str]
    last_validation_at: datetime


class CompleteSetupRequest(BaseModel):
    """Request to mark setup as complete."""
    force: bool = Field(
        False, 
        description="Force completion even if some optional requirements are incomplete"
    )


class CompleteSetupResponse(BaseModel):
    """Response for setup completion."""
    success: bool
    is_setup_complete: bool
    message: str
    setup_completed_at: Optional[datetime] = None


class SetupRequirementsResponse(BaseModel):
    """Response model for setup requirements."""
    required: list[str]
    optional: list[str]
    coming_soon: list[str]


# Extended user model with setup fields
class UserWithSetup(BaseModel):
    """User model with setup information."""
    id: int
    email: EmailStr
    name: Optional[str]
    role: str
    llm_provider: Optional[LLMProvider]
    llm_model: Optional[str]
    is_setup_complete: bool
    setup_completed_at: Optional[datetime]
    last_validation_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class APIKeyCreateRequest(BaseModel):
    """Request model for creating API keys."""
    provider: LLMProvider
    name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)
    is_primary: bool = Field(False, description="Set as primary key for this provider")
    model: Optional[str] = Field(None, max_length=50)


class APIKeyUpdateRequest(BaseModel):
    """Request model for updating API keys."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_primary: Optional[bool] = None
    status: Optional[str] = Field(None, pattern="^(active|exhausted|invalid)$")


class APIKeyResponse(BaseModel):
    """Response model for API keys."""
    id: int
    provider: LLMProvider
    name: str
    key_masked: str
    is_primary: bool
    status: str
    model: Optional[str]
    is_validated: bool
    validated_at: Optional[datetime]
    error_count: int
    last_error: Optional[str]
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class APIKeyListResponse(BaseModel):
    """Response model for listing API keys."""
    api_keys: list[APIKeyResponse]
    total: int
    has_active_keys: bool
    providers_configured: list[LLMProvider]