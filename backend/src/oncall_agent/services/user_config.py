"""Service for managing user configuration and setup status."""

from datetime import datetime
from typing import Any

from src.oncall_agent.api.models.auth import (
    LLMConfigRequest,
    SetupRequirement,
    SetupRequirementType,
    SetupStatusResponse,
    UserWithSetup,
    ValidationResult,
)
from src.oncall_agent.security.encryption import (
    encrypt_api_key,
    mask_api_key,
)
from src.oncall_agent.services.llm_validator import (
    ValidationResult as LLMValidationResult,
)
from src.oncall_agent.utils.logger import get_logger

logger = get_logger(__name__)


class StoredLLMConfig:
    """Stored LLM configuration."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.provider = kwargs.get('provider')
        self.name = kwargs.get('name')
        self.model = kwargs.get('model')
        self.is_validated = kwargs.get('is_validated', False)
        self.validated_at = kwargs.get('validated_at')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())


class UserConfigService:
    """Service for managing user configuration and setup."""

    def __init__(self):
        # In a real implementation, this would use the database
        # For now, we'll use in-memory storage for demonstration
        self._user_configs: dict[int, dict[str, Any]] = {}
        self._api_keys: dict[int, list[dict[str, Any]]] = {}
        self._setup_requirements: dict[int, dict[str, dict[str, Any]]] = {}

    async def store_llm_config(
        self,
        user_id: int,
        config: LLMConfigRequest,
        validation_result: LLMValidationResult
    ) -> StoredLLMConfig:
        """Store LLM configuration for a user.
        
        Args:
            user_id: User ID
            config: LLM configuration request
            validation_result: Result of API key validation
            
        Returns:
            Stored configuration
        """
        try:
            # Encrypt the API key
            encrypted_key = encrypt_api_key(config.api_key)
            masked_key = mask_api_key(config.api_key)

            # Create API key record
            api_key_data = {
                'id': len(self._api_keys.get(user_id, [])) + 1,
                'user_id': user_id,
                'provider': config.provider,
                'name': config.key_name or f"{config.provider} API Key",
                'key_masked': masked_key,
                'key_hash': encrypted_key,
                'model': config.model,
                'is_primary': True,  # First key is primary
                'status': 'active',
                'is_validated': validation_result.valid,
                'validated_at': datetime.utcnow() if validation_result.valid else None,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            # Store in our mock database
            if user_id not in self._api_keys:
                self._api_keys[user_id] = []

            # Mark other keys as non-primary
            for key in self._api_keys[user_id]:
                if key['provider'] == config.provider:
                    key['is_primary'] = False

            self._api_keys[user_id].append(api_key_data)

            # Update user config
            if user_id not in self._user_configs:
                self._user_configs[user_id] = {}

            self._user_configs[user_id]['llm_provider'] = config.provider
            self._user_configs[user_id]['llm_model'] = config.model
            self._user_configs[user_id]['last_validation_at'] = datetime.utcnow()

            logger.info(f"Stored LLM config for user {user_id}")

            return StoredLLMConfig(**api_key_data)

        except Exception as e:
            logger.error(f"Failed to store LLM config: {str(e)}")
            raise

    async def validate_llm_config(self, user_id: int) -> ValidationResult:
        """Validate stored LLM configuration for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Validation result
        """
        try:
            # Get primary API key
            user_keys = self._api_keys.get(user_id, [])
            primary_key = next(
                (key for key in user_keys if key['is_primary'] and key['status'] == 'active'),
                None
            )

            if not primary_key:
                return ValidationResult(
                    validation_type="llm_key",
                    target="llm_config",
                    is_successful=False,
                    error_message="No active LLM API key found"
                )

            # In a real implementation, we would decrypt and test the key
            # For now, we'll use the stored validation status
            return ValidationResult(
                validation_type="llm_key",
                target=primary_key['provider'],
                is_successful=primary_key.get('is_validated', False),
                error_message=None if primary_key.get('is_validated') else "API key validation failed"
            )

        except Exception as e:
            logger.error(f"Failed to validate LLM config: {str(e)}")
            return ValidationResult(
                validation_type="llm_key",
                target="llm_config",
                is_successful=False,
                error_message=str(e)
            )

    async def validate_integrations(self, user_id: int) -> list[ValidationResult]:
        """Validate all user integrations.
        
        Args:
            user_id: User ID
            
        Returns:
            List of validation results
        """
        # In a real implementation, this would check actual integrations
        # For now, return mock results
        return [
            ValidationResult(
                validation_type="integration",
                target="pagerduty",
                is_successful=True,
                error_message=None
            ),
            ValidationResult(
                validation_type="integration",
                target="kubernetes",
                is_successful=True,
                error_message=None
            )
        ]

    async def get_user_setup_status(self, user_id: int) -> SetupStatusResponse:
        """Get user's setup completion status.
        
        Args:
            user_id: User ID
            
        Returns:
            Setup status response
        """
        try:
            # Get user config
            user_config = self._user_configs.get(user_id, {})

            # Get setup requirements
            if user_id not in self._setup_requirements:
                # Initialize requirements
                self._setup_requirements[user_id] = {
                    'llm_config': {'is_required': True, 'is_completed': False},
                    'pagerduty': {'is_required': True, 'is_completed': False},
                    'kubernetes': {'is_required': True, 'is_completed': False},
                    'github': {'is_required': False, 'is_completed': False},
                    'notion': {'is_required': False, 'is_completed': False},
                    'grafana': {'is_required': False, 'is_completed': False},
                }

            requirements = self._setup_requirements[user_id]

            # Check LLM configuration
            has_llm = bool(self._api_keys.get(user_id))
            if has_llm:
                requirements['llm_config']['is_completed'] = True
                requirements['llm_config']['completed_at'] = datetime.utcnow()

            # Build setup requirements list
            setup_requirements = []
            for req_type, req_data in requirements.items():
                setup_requirements.append(SetupRequirement(
                    requirement_type=req_type,
                    is_required=req_data['is_required'],
                    is_completed=req_data['is_completed'],
                    completed_at=req_data.get('completed_at')
                ))

            # Calculate missing requirements
            missing_requirements = [
                req_type for req_type, req_data in requirements.items()
                if req_data['is_required'] and not req_data['is_completed']
            ]

            # Calculate progress
            required_count = sum(1 for r in requirements.values() if r['is_required'])
            completed_count = sum(
                1 for r in requirements.values()
                if r['is_required'] and r['is_completed']
            )
            progress = (completed_count / required_count * 100) if required_count > 0 else 0

            # Build integrations configured dict
            integrations_configured = {
                'pagerduty': requirements['pagerduty']['is_completed'],
                'kubernetes': requirements['kubernetes']['is_completed'],
                'github': requirements['github']['is_completed'],
                'notion': requirements['notion']['is_completed'],
                'grafana': requirements['grafana']['is_completed'],
            }

            return SetupStatusResponse(
                is_setup_complete=len(missing_requirements) == 0,
                llm_configured=has_llm,
                llm_provider=user_config.get('llm_provider'),
                integrations_configured=integrations_configured,
                setup_requirements=setup_requirements,
                missing_requirements=missing_requirements,
                setup_progress_percentage=progress
            )

        except Exception as e:
            logger.error(f"Failed to get setup status: {str(e)}")
            raise

    async def mark_requirement_complete(
        self,
        user_id: int,
        requirement_type: SetupRequirementType
    ) -> None:
        """Mark a setup requirement as complete.
        
        Args:
            user_id: User ID
            requirement_type: Type of requirement to mark complete
        """
        if user_id not in self._setup_requirements:
            self._setup_requirements[user_id] = {}

        if requirement_type not in self._setup_requirements[user_id]:
            self._setup_requirements[user_id][requirement_type] = {}

        self._setup_requirements[user_id][requirement_type]['is_completed'] = True
        self._setup_requirements[user_id][requirement_type]['completed_at'] = datetime.utcnow()

        logger.info(f"Marked {requirement_type} as complete for user {user_id}")

    async def mark_setup_complete(self, user_id: int) -> datetime:
        """Mark user setup as complete.
        
        Args:
            user_id: User ID
            
        Returns:
            Completion timestamp
        """
        completion_time = datetime.utcnow()

        if user_id not in self._user_configs:
            self._user_configs[user_id] = {}

        self._user_configs[user_id]['is_setup_complete'] = True
        self._user_configs[user_id]['setup_completed_at'] = completion_time

        logger.info(f"Marked setup complete for user {user_id}")

        return completion_time

    async def update_last_validation(self, user_id: int) -> None:
        """Update last validation timestamp for user.
        
        Args:
            user_id: User ID
        """
        if user_id not in self._user_configs:
            self._user_configs[user_id] = {}

        self._user_configs[user_id]['last_validation_at'] = datetime.utcnow()

    async def get_user_with_setup(self, user_id: int) -> UserWithSetup:
        """Get user information with setup status.
        
        Args:
            user_id: User ID
            
        Returns:
            User with setup information
        """
        # In a real implementation, this would fetch from database
        user_config = self._user_configs.get(user_id, {})

        return UserWithSetup(
            id=user_id,
            email="admin@oncall.ai",  # Mock data
            name="Test User",
            role="admin",
            llm_provider=user_config.get('llm_provider'),
            llm_model=user_config.get('llm_model'),
            is_setup_complete=user_config.get('is_setup_complete', False),
            setup_completed_at=user_config.get('setup_completed_at'),
            last_validation_at=user_config.get('last_validation_at'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
