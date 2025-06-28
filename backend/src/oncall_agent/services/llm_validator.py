"""Service for validating LLM API keys and connections."""

import httpx
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from src.oncall_agent.api.models.auth import LLMProvider
from src.oncall_agent.utils.logger import get_logger


logger = get_logger(__name__)


class ValidationResult:
    """Result of LLM API key validation."""
    
    def __init__(
        self,
        valid: bool,
        error: Optional[str] = None,
        model_info: Optional[Dict[str, Any]] = None,
        rate_limit_info: Optional[Dict[str, Any]] = None
    ):
        self.valid = valid
        self.error = error
        self.model_info = model_info or {}
        self.rate_limit_info = rate_limit_info or {}


class LLMValidator:
    """Validates LLM API keys by testing connections."""
    
    def __init__(self):
        self.anthropic_base_url = "https://api.anthropic.com/v1"
        self.openai_base_url = "https://api.openai.com/v1"
        
    async def validate_api_key(
        self,
        provider: str,
        api_key: str,
        model: Optional[str] = None
    ) -> ValidationResult:
        """Validate an API key with the specified provider.
        
        Args:
            provider: The LLM provider (anthropic or openai)
            api_key: The API key to validate
            model: Optional specific model to test with
            
        Returns:
            ValidationResult with validation status and metadata
        """
        if provider == "anthropic" or provider == LLMProvider.ANTHROPIC:
            return await self._validate_anthropic_key(api_key, model)
        elif provider == "openai" or provider == LLMProvider.OPENAI:
            return await self._validate_openai_key(api_key, model)
        else:
            return ValidationResult(
                valid=False,
                error=f"Unknown provider: {provider}"
            )
    
    async def _validate_anthropic_key(
        self,
        api_key: str,
        model: Optional[str] = None
    ) -> ValidationResult:
        """Validate Anthropic API key."""
        try:
            async with httpx.AsyncClient() as client:
                # Use a minimal completion request to test the key
                response = await client.post(
                    f"{self.anthropic_base_url}/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": model or "claude-3-5-sonnet-20241022",
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 10
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract rate limit info from headers
                    rate_limit_info = {
                        "requests_limit": response.headers.get("anthropic-ratelimit-requests-limit"),
                        "requests_remaining": response.headers.get("anthropic-ratelimit-requests-remaining"),
                        "requests_reset": response.headers.get("anthropic-ratelimit-requests-reset"),
                        "tokens_limit": response.headers.get("anthropic-ratelimit-tokens-limit"),
                        "tokens_remaining": response.headers.get("anthropic-ratelimit-tokens-remaining"),
                        "tokens_reset": response.headers.get("anthropic-ratelimit-tokens-reset"),
                    }
                    
                    return ValidationResult(
                        valid=True,
                        model_info={
                            "model": data.get("model"),
                            "usage": data.get("usage", {})
                        },
                        rate_limit_info=rate_limit_info
                    )
                    
                elif response.status_code == 401:
                    return ValidationResult(
                        valid=False,
                        error="Invalid API key"
                    )
                    
                elif response.status_code == 429:
                    return ValidationResult(
                        valid=True,  # Key is valid but rate limited
                        error="Rate limit exceeded",
                        rate_limit_info={
                            "retry_after": response.headers.get("retry-after")
                        }
                    )
                    
                else:
                    error_data = response.json()
                    return ValidationResult(
                        valid=False,
                        error=error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    )
                    
        except httpx.TimeoutException:
            return ValidationResult(
                valid=False,
                error="Connection timeout - please try again"
            )
        except Exception as e:
            logger.error(f"Error validating Anthropic key: {str(e)}")
            return ValidationResult(
                valid=False,
                error=f"Validation failed: {str(e)}"
            )
    
    async def _validate_openai_key(
        self,
        api_key: str,
        model: Optional[str] = None
    ) -> ValidationResult:
        """Validate OpenAI API key."""
        try:
            async with httpx.AsyncClient() as client:
                # First, try to list models to validate the key
                response = await client.get(
                    f"{self.openai_base_url}/models",
                    headers={
                        "Authorization": f"Bearer {api_key}"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    models_data = response.json()
                    available_models = [m["id"] for m in models_data.get("data", [])]
                    
                    # Now make a minimal completion request
                    test_model = model or "gpt-4o-mini"
                    if test_model not in available_models and "gpt-3.5-turbo" in available_models:
                        test_model = "gpt-3.5-turbo"
                    
                    completion_response = await client.post(
                        f"{self.openai_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": test_model,
                            "messages": [{"role": "user", "content": "Hi"}],
                            "max_tokens": 10
                        },
                        timeout=10.0
                    )
                    
                    if completion_response.status_code == 200:
                        completion_data = completion_response.json()
                        
                        # Extract rate limit info
                        headers = completion_response.headers
                        rate_limit_info = {
                            "requests_limit": headers.get("x-ratelimit-limit-requests"),
                            "requests_remaining": headers.get("x-ratelimit-remaining-requests"),
                            "requests_reset": headers.get("x-ratelimit-reset-requests"),
                            "tokens_limit": headers.get("x-ratelimit-limit-tokens"),
                            "tokens_remaining": headers.get("x-ratelimit-remaining-tokens"),
                            "tokens_reset": headers.get("x-ratelimit-reset-tokens"),
                        }
                        
                        return ValidationResult(
                            valid=True,
                            model_info={
                                "model": completion_data.get("model"),
                                "available_models": available_models[:10],  # First 10 models
                                "usage": completion_data.get("usage", {})
                            },
                            rate_limit_info=rate_limit_info
                        )
                    else:
                        return ValidationResult(
                            valid=False,
                            error=f"Completion request failed: HTTP {completion_response.status_code}"
                        )
                        
                elif response.status_code == 401:
                    return ValidationResult(
                        valid=False,
                        error="Invalid API key"
                    )
                    
                else:
                    error_data = response.json()
                    return ValidationResult(
                        valid=False,
                        error=error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                    )
                    
        except httpx.TimeoutException:
            return ValidationResult(
                valid=False,
                error="Connection timeout - please try again"
            )
        except Exception as e:
            logger.error(f"Error validating OpenAI key: {str(e)}")
            return ValidationResult(
                valid=False,
                error=f"Validation failed: {str(e)}"
            )