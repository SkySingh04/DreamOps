"""API Key management router."""


from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse

from ...models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeySettings,
    APIKeyUpdate,
    LLMProvider,
)
from ...services.api_key_service import APIKeyService
from ...utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])

# Dependency to get API key service instance
_api_key_service = None


def get_api_key_service() -> APIKeyService:
    """Get or create API key service instance."""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service


@router.post("", response_model=APIKey)
async def create_api_key(
    key_data: APIKeyCreate,
    service: APIKeyService = Depends(get_api_key_service)
) -> APIKey:
    """Create a new API key."""
    try:
        logger.info(f"Creating new API key for provider: {key_data.provider}")
        key = service.create_key(key_data)
        return key
    except Exception as e:
        logger.error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[APIKey])
async def list_api_keys(
    service: APIKeyService = Depends(get_api_key_service)
) -> list[APIKey]:
    """List all API keys (with masked values)."""
    try:
        keys = service.list_keys()
        return keys
    except Exception as e:
        logger.error(f"Failed to list API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings", response_model=APIKeySettings)
async def get_api_key_settings(
    service: APIKeyService = Depends(get_api_key_service)
) -> APIKeySettings:
    """Get current API key settings."""
    settings = service.get_settings()
    if not settings:
        raise HTTPException(status_code=404, detail="No settings configured")
    return settings


@router.put("/settings", response_model=APIKeySettings)
async def update_api_key_settings(
    settings: APIKeySettings,
    service: APIKeyService = Depends(get_api_key_service)
) -> APIKeySettings:
    """Update API key settings."""
    try:
        service.update_settings(settings)
        return settings
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key_id}", response_model=APIKey)
async def get_api_key(
    key_id: str,
    service: APIKeyService = Depends(get_api_key_service)
) -> APIKey:
    """Get a specific API key details."""
    key = service.get_key(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key


@router.put("/{key_id}", response_model=APIKey)
async def update_api_key(
    key_id: str,
    update_data: APIKeyUpdate,
    service: APIKeyService = Depends(get_api_key_service)
) -> APIKey:
    """Update an API key."""
    try:
        key = service.update_key(key_id, update_data)
        if not key:
            raise HTTPException(status_code=404, detail="API key not found")
        return key
    except Exception as e:
        logger.error(f"Failed to update API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    service: APIKeyService = Depends(get_api_key_service)
) -> JSONResponse:
    """Delete an API key."""
    try:
        success = service.delete_key(key_id)
        if not success:
            raise HTTPException(status_code=404, detail="API key not found")
        return JSONResponse(content={"message": "API key deleted successfully"})
    except ValueError as e:
        # Cannot delete last key
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{key_id}/validate")
async def validate_api_key(
    key_id: str,
    background_tasks: BackgroundTasks,
    service: APIKeyService = Depends(get_api_key_service)
) -> JSONResponse:
    """Validate an API key by testing it with the provider."""
    key_data = service.get_key(key_id)
    if not key_data:
        raise HTTPException(status_code=404, detail="API key not found")

    # Get the actual key for validation
    actual_key = service.get_actual_key(key_id)
    if not actual_key:
        raise HTTPException(status_code=404, detail="API key not found")

    # Validate based on provider
    try:
        if key_data.provider == LLMProvider.ANTHROPIC:
            # Test with Anthropic API
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": actual_key,
                        "anthropic-version": "2023-06-01"
                    }
                )

                if response.status_code == 401:
                    # Invalid key
                    background_tasks.add_task(
                        service.record_key_usage,
                        key_id,
                        False,
                        "Invalid API key"
                    )
                    return JSONResponse(
                        status_code=400,
                        content={"valid": False, "error": "Invalid API key"}
                    )
                elif response.status_code == 200:
                    # Valid key
                    background_tasks.add_task(
                        service.record_key_usage,
                        key_id,
                        True
                    )
                    return JSONResponse(content={"valid": True})
                else:
                    # Other error
                    error_msg = f"Validation failed: {response.status_code}"
                    background_tasks.add_task(
                        service.record_key_usage,
                        key_id,
                        False,
                        error_msg
                    )
                    return JSONResponse(
                        status_code=400,
                        content={"valid": False, "error": error_msg}
                    )

        elif key_data.provider == LLMProvider.OPENAI:
            # Test with OpenAI API
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={
                        "Authorization": f"Bearer {actual_key}"
                    }
                )

                if response.status_code == 401:
                    background_tasks.add_task(
                        service.record_key_usage,
                        key_id,
                        False,
                        "Invalid API key"
                    )
                    return JSONResponse(
                        status_code=400,
                        content={"valid": False, "error": "Invalid API key"}
                    )
                elif response.status_code == 200:
                    background_tasks.add_task(
                        service.record_key_usage,
                        key_id,
                        True
                    )
                    return JSONResponse(content={"valid": True})
                else:
                    error_msg = f"Validation failed: {response.status_code}"
                    background_tasks.add_task(
                        service.record_key_usage,
                        key_id,
                        False,
                        error_msg
                    )
                    return JSONResponse(
                        status_code=400,
                        content={"valid": False, "error": error_msg}
                    )

        else:
            # Provider not yet supported for validation
            return JSONResponse(content={
                "valid": "unknown",
                "message": f"Validation not implemented for {key_data.provider}"
            })

    except Exception as e:
        logger.error(f"Failed to validate API key: {e}")
        background_tasks.add_task(
            service.record_key_usage,
            key_id,
            False,
            str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/active")
async def get_active_key_status(
    service: APIKeyService = Depends(get_api_key_service)
) -> JSONResponse:
    """Get the status of the currently active key."""
    active_key = service.get_active_key()
    if not active_key:
        return JSONResponse(
            status_code=404,
            content={"error": "No active API key configured"}
        )

    key_id, _, provider = active_key
    key_details = service.get_key(key_id)

    return JSONResponse(content={
        "active_key_id": key_id,
        "provider": provider,
        "status": key_details.status,
        "name": key_details.name,
        "last_used_at": key_details.last_used_at.isoformat() if key_details.last_used_at else None,
        "error_count": key_details.error_count
    })
