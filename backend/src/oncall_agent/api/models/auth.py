"""Authentication and setup flow models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


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
    key_name: str | None = Field(None, max_length=100, description="Optional name for the key")
    model: str | None = Field(None, max_length=50, description="Specific model to use")


class LLMConfigResponse(BaseModel):
    """Response model for LLM configuration."""
    id: int
    provider: LLMProvider
    key_name: str
    model: str | None
    is_validated: bool
    validated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TestLLMRequest(BaseModel):
    """Request model for testing LLM connection."""
    provider: LLMProvider
    api_key: str = Field(..., min_length=1)
    model: str | None = None


class TestLLMResponse(BaseModel):
    """Response model for LLM connection test."""
    valid: bool
    error: str | None = None
    model_info: dict[str, Any] | None = None
    rate_limit_info: dict[str, Any] | None = None


class SetupRequirement(BaseModel):
    """Model for a setup requirement."""
    requirement_type: SetupRequirementType
    is_required: bool
    is_completed: bool
    completed_at: datetime | None = None
    error_message: str | None = None


class SetupStatusResponse(BaseModel):
    """Response model for setup status."""
    is_setup_complete: bool
    llm_configured: bool
    llm_provider: LLMProvider | None = None
    integrations_configured: dict[str, bool]
    setup_requirements: list[SetupRequirement]
    missing_requirements: list[str]
    setup_progress_percentage: float


class ValidationResult(BaseModel):
    """Result of a validation check."""
    validation_type: str
    target: str
    is_successful: bool
    error_message: str | None = None
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
    setup_completed_at: datetime | None = None


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
    name: str | None
    role: str
    llm_provider: LLMProvider | None
    llm_model: str | None
    is_setup_complete: bool
    setup_completed_at: datetime | None
    last_validation_at: datetime | None
    created_at: datetime
    updated_at: datetime


class APIKeyCreateRequest(BaseModel):
    """Request model for creating API keys."""
    provider: LLMProvider
    name: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)
    is_primary: bool = Field(False, description="Set as primary key for this provider")
    model: str | None = Field(None, max_length=50)


class APIKeyUpdateRequest(BaseModel):
    """Request model for updating API keys."""
    name: str | None = Field(None, min_length=1, max_length=100)
    is_primary: bool | None = None
    status: str | None = Field(None, pattern="^(active|exhausted|invalid)$")


class APIKeyResponse(BaseModel):
    """Response model for API keys."""
    id: int
    provider: LLMProvider
    name: str
    key_masked: str
    is_primary: bool
    status: str
    model: str | None
    is_validated: bool
    validated_at: datetime | None
    error_count: int
    last_error: str | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class APIKeyListResponse(BaseModel):
    """Response model for listing API keys."""
    api_keys: list[APIKeyResponse]
    total: int
    has_active_keys: bool
    providers_configured: list[LLMProvider]
