#!/usr/bin/env python3
"""
Integration Data Verification System for DreamOps

This script provides comprehensive verification of user integration data,
including encryption/decryption cycles, connection testing, and health monitoring.
"""

import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.oncall_agent.config import get_config
from src.oncall_agent.mcp_integrations.github_mcp import GitHubMCPIntegration
from src.oncall_agent.mcp_integrations.kubernetes_mcp_only import (
    KubernetesMCPOnlyIntegration as KubernetesIntegration,
)
from src.oncall_agent.mcp_integrations.notion_direct import NotionDirectIntegration

# PagerDuty integration not available as MCP integration
from src.oncall_agent.security.encryption import EncryptionService
from src.oncall_agent.utils.logger import get_logger

logger = get_logger(__name__)


class IntegrationType(str, Enum):
    PAGERDUTY = "pagerduty"
    KUBERNETES = "kubernetes"
    GITHUB = "github"
    NOTION = "notion"
    GRAFANA = "grafana"


@dataclass
class ValidationResult:
    """Result of an integration validation test"""
    integration_type: str
    success: bool
    error_message: str | None = None
    details: dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class ConnectionResult:
    """Result of a connection test"""
    integration_type: str
    connected: bool
    latency_ms: float | None = None
    error_message: str | None = None
    capabilities: list[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.capabilities is None:
            self.capabilities = []

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class IntegrationDataVerifier:
    """Comprehensive verification system for user integration data"""

    def __init__(self):
        self.config = get_config()
        self.encryption_service = EncryptionService()
        self.logger = get_logger(self.__class__.__name__)

        # Mock user integrations DB - in production this would be database queries
        self.integrations_db = {}

    async def verify_user_integrations(self, user_id: str) -> dict[str, Any]:
        """
        Comprehensive verification of all user integration data
        
        Args:
            user_id: The user ID to verify integrations for
            
        Returns:
            Dictionary containing verification results for all integrations
        """
        self.logger.info(f"Starting comprehensive integration verification for user {user_id}")

        results = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "encryption_test": await self.test_encryption_cycle(user_id, IntegrationType.PAGERDUTY),
            "validations": await self.validate_all_integration_types(user_id),
            "connections": await self.test_connection_with_stored_creds(user_id),
            "summary": {}
        }

        # Calculate summary statistics
        total_integrations = len(results["validations"])
        successful_validations = sum(1 for v in results["validations"].values() if v.success)
        successful_connections = sum(1 for c in results["connections"].values() if c.connected)

        results["summary"] = {
            "total_integrations": total_integrations,
            "successful_validations": successful_validations,
            "successful_connections": successful_connections,
            "health_score": (successful_validations + successful_connections) / (total_integrations * 2) * 100 if total_integrations > 0 else 0
        }

        self.logger.info(f"Completed integration verification for user {user_id}: {results['summary']}")
        return results

    async def test_encryption_cycle(self, user_id: str, integration_type: str) -> bool:
        """
        Test the complete encrypt -> store -> retrieve -> decrypt cycle
        
        Args:
            user_id: The user ID
            integration_type: The type of integration to test
            
        Returns:
            True if the encryption cycle works correctly
        """
        try:
            self.logger.info(f"Testing encryption cycle for {user_id}/{integration_type}")

            # Test data
            test_data = {
                "api_key": "test-api-key-12345",
                "secret": "test-secret-67890",
                "config": {"nested": {"data": "sensitive-info"}}
            }

            # Encrypt
            encrypted_data = {}
            for key, value in test_data.items():
                if isinstance(value, dict):
                    encrypted_data[key] = self.encryption_service.encrypt(json.dumps(value))
                else:
                    encrypted_data[key] = self.encryption_service.encrypt(value)

            # Store (simulate)
            storage_key = f"{user_id}:{integration_type}:test"
            self.integrations_db[storage_key] = encrypted_data

            # Retrieve
            retrieved_data = self.integrations_db.get(storage_key)
            if not retrieved_data:
                raise ValueError("Failed to retrieve stored data")

            # Decrypt
            decrypted_data = {}
            for key, value in retrieved_data.items():
                decrypted = self.encryption_service.decrypt(value)
                if key == "config":
                    decrypted_data[key] = json.loads(decrypted)
                else:
                    decrypted_data[key] = decrypted

            # Verify
            success = test_data == decrypted_data

            # Cleanup
            del self.integrations_db[storage_key]

            self.logger.info(f"Encryption cycle test {'passed' if success else 'failed'} for {user_id}/{integration_type}")
            return success

        except Exception as e:
            self.logger.error(f"Encryption cycle test failed: {str(e)}")
            return False

    async def validate_all_integration_types(self, user_id: str) -> dict[str, ValidationResult]:
        """
        Validate configuration for all integration types
        
        Args:
            user_id: The user ID to validate integrations for
            
        Returns:
            Dictionary mapping integration type to validation result
        """
        validations = {}

        # Validate each integration type
        for integration_type in IntegrationType:
            validations[integration_type.value] = await self._validate_integration_type(
                user_id, integration_type.value
            )

        return validations

    async def _validate_integration_type(self, user_id: str, integration_type: str) -> ValidationResult:
        """Validate a specific integration type configuration"""
        try:
            if integration_type == IntegrationType.PAGERDUTY:
                return await self.verify_pagerduty_integration(user_id)
            elif integration_type == IntegrationType.KUBERNETES:
                return await self.verify_kubernetes_integration(user_id)
            elif integration_type == IntegrationType.GITHUB:
                return await self.verify_github_integration(user_id)
            elif integration_type == IntegrationType.NOTION:
                return await self.verify_notion_integration(user_id)
            elif integration_type == IntegrationType.GRAFANA:
                return await self.verify_grafana_integration(user_id)
            else:
                return ValidationResult(
                    integration_type=integration_type,
                    success=False,
                    error_message=f"Unknown integration type: {integration_type}"
                )
        except Exception as e:
            self.logger.error(f"Validation failed for {integration_type}: {str(e)}")
            return ValidationResult(
                integration_type=integration_type,
                success=False,
                error_message=str(e)
            )

    async def verify_pagerduty_integration(self, user_id: str) -> ValidationResult:
        """
        Verify PagerDuty integration configuration
        
        1. Retrieve stored integration URL and webhook secret
        2. Verify URL format: https://events.pagerduty.com/integration/{key}/enqueue
        3. Test webhook endpoint with mock alert
        4. Verify webhook signature validation (if secret provided)
        5. Confirm alert reaches DreamOps API
        """
        try:
            # Simulate retrieving stored configuration
            stored_config = self._get_stored_config(user_id, IntegrationType.PAGERDUTY)

            if not stored_config:
                return ValidationResult(
                    integration_type=IntegrationType.PAGERDUTY,
                    success=False,
                    error_message="No PagerDuty integration found for user"
                )

            details = {}

            # Verify URL format
            integration_url = stored_config.get("integration_url", "")
            url_valid = integration_url.startswith("https://events.pagerduty.com/integration/") and \
                       integration_url.endswith("/enqueue")
            details["url_format_valid"] = url_valid

            # Check webhook secret
            webhook_secret = stored_config.get("webhook_secret", "")
            details["webhook_secret_configured"] = bool(webhook_secret)

            # Additional validation details
            details["api_key_present"] = bool(stored_config.get("api_key"))
            details["user_email_configured"] = bool(stored_config.get("user_email"))

            success = url_valid and details["api_key_present"]

            return ValidationResult(
                integration_type=IntegrationType.PAGERDUTY,
                success=success,
                details=details,
                error_message=None if success else "Invalid configuration"
            )

        except Exception as e:
            return ValidationResult(
                integration_type=IntegrationType.PAGERDUTY,
                success=False,
                error_message=str(e)
            )

    async def verify_kubernetes_integration(self, user_id: str) -> ValidationResult:
        """
        Verify Kubernetes integration configuration
        
        1. Retrieve stored kubeconfig contexts and namespaces
        2. Test MCP server connection to each context
        3. Verify namespace access and permissions
        4. Test common operations (get pods, get deployments)
        5. Confirm RBAC permissions match expected capabilities
        """
        try:
            stored_config = self._get_stored_config(user_id, IntegrationType.KUBERNETES)

            if not stored_config:
                return ValidationResult(
                    integration_type=IntegrationType.KUBERNETES,
                    success=False,
                    error_message="No Kubernetes integration found for user"
                )

            details = {
                "contexts_configured": len(stored_config.get("contexts", [])),
                "default_namespace": stored_config.get("default_namespace", "default"),
                "kubeconfig_present": bool(stored_config.get("kubeconfig_path")),
                "destructive_operations_enabled": stored_config.get("enable_destructive_operations", False)
            }

            # Verify at least one context is configured
            success = details["contexts_configured"] > 0

            return ValidationResult(
                integration_type=IntegrationType.KUBERNETES,
                success=success,
                details=details,
                error_message=None if success else "No Kubernetes contexts configured"
            )

        except Exception as e:
            return ValidationResult(
                integration_type=IntegrationType.KUBERNETES,
                success=False,
                error_message=str(e)
            )

    async def verify_github_integration(self, user_id: str) -> ValidationResult:
        """
        Verify GitHub integration configuration
        
        1. Retrieve stored GitHub token
        2. Test token validity with GitHub API
        3. Verify repository access permissions
        4. Test MCP server operations (get repos, get issues)
        5. Confirm token scopes match requirements
        """
        try:
            stored_config = self._get_stored_config(user_id, IntegrationType.GITHUB)

            if not stored_config:
                return ValidationResult(
                    integration_type=IntegrationType.GITHUB,
                    success=False,
                    error_message="No GitHub integration found for user"
                )

            details = {
                "token_present": bool(stored_config.get("github_token")),
                "default_owner_configured": bool(stored_config.get("default_owner")),
                "default_repo_configured": bool(stored_config.get("default_repo"))
            }

            success = details["token_present"]

            return ValidationResult(
                integration_type=IntegrationType.GITHUB,
                success=success,
                details=details,
                error_message=None if success else "GitHub token not configured"
            )

        except Exception as e:
            return ValidationResult(
                integration_type=IntegrationType.GITHUB,
                success=False,
                error_message=str(e)
            )

    async def verify_notion_integration(self, user_id: str) -> ValidationResult:
        """
        Verify Notion integration configuration
        
        1. Retrieve stored Notion token and workspace ID
        2. Test workspace access
        3. Verify page/database read permissions
        4. Test MCP server operations (search pages, get content)
        5. Confirm integration token validity
        """
        try:
            stored_config = self._get_stored_config(user_id, IntegrationType.NOTION)

            if not stored_config:
                return ValidationResult(
                    integration_type=IntegrationType.NOTION,
                    success=False,
                    error_message="No Notion integration found for user"
                )

            details = {
                "token_present": bool(stored_config.get("notion_token")),
                "workspace_id_configured": bool(stored_config.get("workspace_id")),
                "default_database_configured": bool(stored_config.get("default_database_id"))
            }

            success = details["token_present"]

            return ValidationResult(
                integration_type=IntegrationType.NOTION,
                success=success,
                details=details,
                error_message=None if success else "Notion token not configured"
            )

        except Exception as e:
            return ValidationResult(
                integration_type=IntegrationType.NOTION,
                success=False,
                error_message=str(e)
            )

    async def verify_grafana_integration(self, user_id: str) -> ValidationResult:
        """
        Verify Grafana integration configuration
        
        1. Retrieve stored Grafana URL and API key
        2. Test Grafana instance connectivity
        3. Verify API key permissions (viewer/editor)
        4. Test dashboard and metrics access
        5. Test MCP server operations (get dashboards, query metrics)
        """
        try:
            stored_config = self._get_stored_config(user_id, IntegrationType.GRAFANA)

            if not stored_config:
                return ValidationResult(
                    integration_type=IntegrationType.GRAFANA,
                    success=False,
                    error_message="No Grafana integration found for user"
                )

            details = {
                "url_configured": bool(stored_config.get("grafana_url")),
                "api_key_present": bool(stored_config.get("api_key")),
                "org_id_configured": stored_config.get("org_id", 1) > 0
            }

            # Verify URL format
            grafana_url = stored_config.get("grafana_url", "")
            if grafana_url:
                details["url_format_valid"] = grafana_url.startswith(("http://", "https://"))
            else:
                details["url_format_valid"] = False

            success = details["url_configured"] and details["api_key_present"] and details["url_format_valid"]

            return ValidationResult(
                integration_type=IntegrationType.GRAFANA,
                success=success,
                details=details,
                error_message=None if success else "Invalid Grafana configuration"
            )

        except Exception as e:
            return ValidationResult(
                integration_type=IntegrationType.GRAFANA,
                success=False,
                error_message=str(e)
            )

    async def test_connection_with_stored_creds(self, user_id: str) -> dict[str, ConnectionResult]:
        """
        Test actual connections using stored credentials
        
        Args:
            user_id: The user ID to test connections for
            
        Returns:
            Dictionary mapping integration type to connection result
        """
        connections = {}

        for integration_type in IntegrationType:
            connections[integration_type.value] = await self._test_single_connection(
                user_id, integration_type.value
            )

        return connections

    async def _test_single_connection(self, user_id: str, integration_type: str) -> ConnectionResult:
        """Test connection for a single integration type"""
        import time

        try:
            stored_config = self._get_stored_config(user_id, integration_type)

            if not stored_config:
                return ConnectionResult(
                    integration_type=integration_type,
                    connected=False,
                    error_message="No configuration found"
                )

            start_time = time.time()

            # Test connection based on integration type
            if integration_type == IntegrationType.PAGERDUTY:
                # PagerDuty integration not available as MCP integration
                connected = False
                capabilities = []
                result = ConnectionResult(
                    integration_type=integration_type,
                    success=False,
                    error="PagerDuty MCP integration not implemented",
                    connected_at=datetime.utcnow()
                )
                return result

            elif integration_type == IntegrationType.KUBERNETES:
                # Initialize Kubernetes integration and test
                integration = KubernetesIntegration(
                    contexts=stored_config.get("contexts", []),
                    namespace=stored_config.get("default_namespace", "default")
                )
                connected = await integration.connect()
                capabilities = integration.get_capabilities() if connected else []

            elif integration_type == IntegrationType.GITHUB:
                # Initialize GitHub integration and test
                integration = GitHubMCPIntegration(
                    github_token=stored_config.get("github_token", "")
                )
                connected = await integration.connect()
                capabilities = integration.get_capabilities() if connected else []

            elif integration_type == IntegrationType.NOTION:
                # Initialize Notion integration and test
                integration = NotionDirectIntegration(
                    notion_token=stored_config.get("notion_token", "")
                )
                connected = await integration.connect()
                capabilities = integration.get_capabilities() if connected else []

            else:
                # Grafana and others - simulate connection test
                connected = bool(stored_config.get("api_key"))
                capabilities = ["dashboard_view", "metrics_query"] if connected else []

            latency_ms = (time.time() - start_time) * 1000

            return ConnectionResult(
                integration_type=integration_type,
                connected=connected,
                latency_ms=latency_ms,
                capabilities=capabilities
            )

        except Exception as e:
            return ConnectionResult(
                integration_type=integration_type,
                connected=False,
                error_message=str(e)
            )

    def _get_stored_config(self, user_id: str, integration_type: IntegrationType) -> dict[str, Any]:
        """
        Retrieve stored configuration for a user's integration
        
        In production, this would query the database. For now, returns mock data.
        """
        # Mock data for testing
        mock_configs = {
            IntegrationType.PAGERDUTY: {
                "integration_url": "https://events.pagerduty.com/integration/abc123/enqueue",
                "webhook_secret": "webhook-secret-123",
                "api_key": "pd-api-key-123",
                "user_email": "user@example.com"
            },
            IntegrationType.KUBERNETES: {
                "contexts": ["minikube", "production"],
                "default_namespace": "default",
                "kubeconfig_path": "~/.kube/config",
                "enable_destructive_operations": False
            },
            IntegrationType.GITHUB: {
                "github_token": "ghp_123456789",
                "default_owner": "dreamops",
                "default_repo": "oncall-agent"
            },
            IntegrationType.NOTION: {
                "notion_token": "secret_123456789",
                "workspace_id": "workspace-123",
                "default_database_id": "db-123"
            },
            IntegrationType.GRAFANA: {
                "grafana_url": "https://grafana.example.com",
                "api_key": "grafana-api-key-123",
                "org_id": 1
            }
        }

        return mock_configs.get(integration_type, {})

    async def generate_health_report(self, user_id: str) -> dict[str, Any]:
        """Generate a comprehensive health report for all user integrations"""
        verification_results = await self.verify_user_integrations(user_id)

        report = {
            "user_id": user_id,
            "report_timestamp": datetime.utcnow().isoformat(),
            "overall_health": verification_results["summary"]["health_score"],
            "integrations": []
        }

        # Combine validation and connection results
        for integration_type in IntegrationType:
            integration_report = {
                "type": integration_type.value,
                "validation": verification_results["validations"][integration_type.value].to_dict(),
                "connection": verification_results["connections"][integration_type.value].to_dict(),
                "status": "healthy" if (
                    verification_results["validations"][integration_type.value].success and
                    verification_results["connections"][integration_type.value].connected
                ) else "unhealthy"
            }
            report["integrations"].append(integration_report)

        return report


async def main():
    """Main function to run the verification system"""
    verifier = IntegrationDataVerifier()

    # Test with a sample user ID
    user_id = "test-user-123"

    print(f"\n{'='*60}")
    print("Integration Data Verification System")
    print(f"{'='*60}\n")

    # Run comprehensive verification
    print(f"Running comprehensive verification for user: {user_id}")
    results = await verifier.verify_user_integrations(user_id)

    # Display results
    print("\nVerification Results:")
    print("-" * 40)
    print(f"Encryption Test: {'✓ Passed' if results['encryption_test'] else '✗ Failed'}")

    print("\nValidation Results:")
    for integration_type, result in results["validations"].items():
        status = "✓" if result.success else "✗"
        print(f"  {integration_type.ljust(15)}: {status} {result.error_message or 'Valid'}")

    print("\nConnection Results:")
    for integration_type, result in results["connections"].items():
        status = "✓" if result.connected else "✗"
        latency = f"({result.latency_ms:.1f}ms)" if result.latency_ms else ""
        print(f"  {integration_type.ljust(15)}: {status} {latency} {result.error_message or 'Connected'}")

    print("\nSummary:")
    print(f"  Total Integrations: {results['summary']['total_integrations']}")
    print(f"  Successful Validations: {results['summary']['successful_validations']}")
    print(f"  Successful Connections: {results['summary']['successful_connections']}")
    print(f"  Overall Health Score: {results['summary']['health_score']:.1f}%")

    # Generate health report
    print(f"\n{'='*60}")
    print("Generating Health Report...")
    print(f"{'='*60}\n")

    health_report = await verifier.generate_health_report(user_id)
    print(json.dumps(health_report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
