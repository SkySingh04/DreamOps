"""API Key management models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class APIKeyStatus(str, Enum):
    """API Key status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXHAUSTED = "exhausted"
    INVALID = "invalid"


class APIKeyCreate(BaseModel):
    """API Key creation request."""
    provider: LLMProvider
    api_key: str
    name: str | None = None
    is_primary: bool = False


class APIKeyUpdate(BaseModel):
    """API Key update request."""
    name: str | None = None
    is_primary: bool | None = None
    status: APIKeyStatus | None = None


class APIKey(BaseModel):
    """API Key model."""
    id: str
    provider: LLMProvider
    api_key_masked: str  # Only show last 4 characters
    name: str | None = None
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    is_primary: bool = False
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None
    error_count: int = 0
    last_error: str | None = None

    class Config:
        from_attributes = True


class APIKeySettings(BaseModel):
    """API Key settings for the agent."""
    active_key_id: str
    fallback_key_ids: list[str] = Field(default_factory=list)
    auto_fallback_enabled: bool = True
    max_retries_before_fallback: int = 3
