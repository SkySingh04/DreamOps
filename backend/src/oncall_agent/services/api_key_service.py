"""API Key management service."""

import json
import os
from datetime import datetime
from uuid import uuid4

from ..models.api_key import (
    APIKey,
    APIKeyCreate,
    APIKeySettings,
    APIKeyStatus,
    APIKeyUpdate,
    LLMProvider,
)
from ..utils.logger import get_logger

logger = get_logger(__name__)


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, storage_path: str = None):
        """Initialize the API key service."""
        self.storage_path = storage_path or os.path.join(
            os.path.expanduser("~"), ".dreamops", "api_keys.json"
        )
        self._ensure_storage_dir()
        self._keys: dict[str, dict] = self._load_keys()
        self._settings: APIKeySettings = self._load_settings()

    def _ensure_storage_dir(self):
        """Ensure storage directory exists."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

    def _load_keys(self) -> dict[str, dict]:
        """Load API keys from storage."""
        if not os.path.exists(self.storage_path):
            return {}

        try:
            with open(self.storage_path) as f:
                data = json.load(f)
                return data.get('keys', {})
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            return {}

    def _load_settings(self) -> APIKeySettings:
        """Load API key settings."""
        if not os.path.exists(self.storage_path):
            return None

        try:
            with open(self.storage_path) as f:
                data = json.load(f)
                settings_data = data.get('settings')
                if settings_data:
                    return APIKeySettings(**settings_data)
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

        return None

    def _save(self):
        """Save keys and settings to storage."""
        data = {
            'keys': self._keys,
            'settings': self._settings.model_dump() if self._settings else None
        }

        try:
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")
            raise

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key showing only last 4 characters."""
        if len(api_key) <= 8:
            return "*" * len(api_key)
        return "*" * (len(api_key) - 4) + api_key[-4:]

    def create_key(self, key_data: APIKeyCreate) -> APIKey:
        """Create a new API key."""
        key_id = str(uuid4())
        now = datetime.utcnow()

        # Store the actual key (in production, this should be encrypted)
        key_record = {
            'id': key_id,
            'provider': key_data.provider,
            'api_key': key_data.api_key,  # Store actual key
            'api_key_masked': self._mask_api_key(key_data.api_key),
            'name': key_data.name or f"{key_data.provider} key",
            'status': APIKeyStatus.ACTIVE,
            'is_primary': key_data.is_primary,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'last_used_at': None,
            'error_count': 0,
            'last_error': None
        }

        # If this is set as primary, update other keys
        if key_data.is_primary:
            for k_id, k_data in self._keys.items():
                k_data['is_primary'] = False

        self._keys[key_id] = key_record

        # If this is the first key or is primary, update settings
        if not self._settings or key_data.is_primary:
            self._settings = APIKeySettings(
                active_key_id=key_id,
                fallback_key_ids=[k for k in self._keys.keys() if k != key_id]
            )
        else:
            # Add to fallback keys
            self._settings.fallback_key_ids.append(key_id)

        self._save()

        # Return without the actual key
        return APIKey(**{k: v for k, v in key_record.items() if k != 'api_key'})

    def get_key(self, key_id: str) -> APIKey | None:
        """Get a specific API key (without the actual key)."""
        key_data = self._keys.get(key_id)
        if not key_data:
            return None

        return APIKey(**{k: v for k, v in key_data.items() if k != 'api_key'})

    def get_actual_key(self, key_id: str) -> str | None:
        """Get the actual API key value (for internal use only)."""
        key_data = self._keys.get(key_id)
        return key_data.get('api_key') if key_data else None

    def list_keys(self) -> list[APIKey]:
        """List all API keys (without actual keys)."""
        keys = []
        for key_data in self._keys.values():
            keys.append(APIKey(**{k: v for k, v in key_data.items() if k != 'api_key'}))
        return keys

    def update_key(self, key_id: str, update_data: APIKeyUpdate) -> APIKey | None:
        """Update an API key."""
        if key_id not in self._keys:
            return None

        key_data = self._keys[key_id]

        if update_data.name is not None:
            key_data['name'] = update_data.name

        if update_data.status is not None:
            key_data['status'] = update_data.status

        if update_data.is_primary is not None:
            if update_data.is_primary:
                # Set all others to non-primary
                for k_id, k_data in self._keys.items():
                    k_data['is_primary'] = False
                # Update settings
                self._settings.active_key_id = key_id
            key_data['is_primary'] = update_data.is_primary

        key_data['updated_at'] = datetime.utcnow().isoformat()

        self._save()
        return APIKey(**{k: v for k, v in key_data.items() if k != 'api_key'})

    def delete_key(self, key_id: str) -> bool:
        """Delete an API key."""
        if key_id not in self._keys:
            return False

        # Don't delete if it's the only key
        if len(self._keys) == 1:
            raise ValueError("Cannot delete the only API key")

        # If deleting active key, switch to another
        if self._settings and self._settings.active_key_id == key_id:
            # Find another active key
            for k_id, k_data in self._keys.items():
                if k_id != key_id and k_data['status'] == APIKeyStatus.ACTIVE:
                    self._settings.active_key_id = k_id
                    k_data['is_primary'] = True
                    break

        del self._keys[key_id]

        # Remove from fallback keys
        if self._settings and key_id in self._settings.fallback_key_ids:
            self._settings.fallback_key_ids.remove(key_id)

        self._save()
        return True

    def get_active_key(self) -> tuple[str, str, LLMProvider] | None:
        """Get the currently active API key (id, key, provider)."""
        if not self._settings or not self._settings.active_key_id:
            return None

        key_data = self._keys.get(self._settings.active_key_id)
        if not key_data or key_data['status'] != APIKeyStatus.ACTIVE:
            return None

        return (
            key_data['id'],
            key_data['api_key'],
            key_data['provider']
        )

    def record_key_usage(self, key_id: str, success: bool = True, error: str = None):
        """Record API key usage."""
        if key_id not in self._keys:
            return

        key_data = self._keys[key_id]
        key_data['last_used_at'] = datetime.utcnow().isoformat()

        if not success:
            key_data['error_count'] += 1
            key_data['last_error'] = error

            # Check if we should mark as exhausted
            if "rate limit" in (error or "").lower() or "quota" in (error or "").lower():
                key_data['status'] = APIKeyStatus.EXHAUSTED
            elif key_data['error_count'] > 5:
                key_data['status'] = APIKeyStatus.INVALID
        else:
            # Reset error count on success
            key_data['error_count'] = 0

        self._save()

    def get_next_fallback_key(self) -> tuple[str, str, LLMProvider] | None:
        """Get the next available fallback key."""
        if not self._settings:
            return None

        for key_id in self._settings.fallback_key_ids:
            key_data = self._keys.get(key_id)
            if key_data and key_data['status'] == APIKeyStatus.ACTIVE:
                # Set as new active key
                self._settings.active_key_id = key_id
                self._save()
                return (
                    key_data['id'],
                    key_data['api_key'],
                    key_data['provider']
                )

        return None

    def get_settings(self) -> APIKeySettings | None:
        """Get current API key settings."""
        return self._settings

    def update_settings(self, settings: APIKeySettings):
        """Update API key settings."""
        self._settings = settings
        self._save()
