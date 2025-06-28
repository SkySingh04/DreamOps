"""
Kubernetes Credentials Management Service

This service handles the storage and retrieval of encrypted Kubernetes credentials
from the database.
"""

import uuid
from datetime import UTC, datetime
from typing import Any, Optional

import asyncpg
from pydantic import BaseModel

from src.oncall_agent.config import get_config
from src.oncall_agent.services.kubernetes_auth import AuthMethod, K8sCredentials, KubernetesAuthService
from src.oncall_agent.utils.logger import get_logger


class K8sCredentialRecord(BaseModel):
    """Database record for Kubernetes credentials"""
    id: str
    user_id: int
    cluster_name: str
    auth_method: str
    encrypted_credentials: str
    namespace: str
    created_at: datetime
    updated_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool
    connection_status: str
    last_error: Optional[str]
    metadata: dict[str, Any]


class KubernetesCredentialsService:
    """Service for managing Kubernetes credentials in the database"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.auth_service = KubernetesAuthService()
    
    async def save_credentials(
        self,
        user_id: int,
        credentials: K8sCredentials,
        test_result: dict[str, Any]
    ) -> str:
        """Save encrypted Kubernetes credentials to database"""
        try:
            # Encrypt credentials
            encrypted_data = self.auth_service.encrypt_credentials(credentials)
            
            # Generate unique ID
            cred_id = f"k8s_{credentials.auth_method.value}_{credentials.cluster_name}_{uuid.uuid4().hex[:8]}"
            
            # Extract connection status from test result
            connection_status = "connected" if test_result.get("connected") else "failed"
            last_error = test_result.get("error") if not test_result.get("connected") else None
            
            # Prepare metadata
            metadata = {
                "cluster_version": test_result.get("cluster_version"),
                "platform": test_result.get("platform"),
                "can_list_namespaces": test_result.get("can_list_namespaces", False),
                "test_timestamp": datetime.now(UTC).isoformat()
            }
            
            # Insert into database
            async with self.db_pool.acquire() as conn:
                # First, deactivate any existing credentials for this user/cluster
                await conn.execute("""
                    UPDATE kubernetes_credentials 
                    SET is_active = false, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = $1 AND cluster_name = $2 AND is_active = true
                """, user_id, credentials.cluster_name)
                
                # Insert new credentials
                await conn.execute("""
                    INSERT INTO kubernetes_credentials (
                        id, user_id, cluster_name, auth_method, encrypted_credentials,
                        namespace, connection_status, last_error, metadata, is_active
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, true)
                """, cred_id, user_id, credentials.cluster_name, credentials.auth_method.value,
                    encrypted_data, credentials.namespace, connection_status, last_error, metadata)
            
            self.logger.info(f"Saved K8s credentials for user {user_id}, cluster {credentials.cluster_name}")
            return cred_id
            
        except Exception as e:
            self.logger.error(f"Failed to save K8s credentials: {e}")
            raise
    
    async def get_credentials(self, user_id: int, cluster_name: str) -> Optional[K8sCredentials]:
        """Retrieve and decrypt Kubernetes credentials"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM kubernetes_credentials
                    WHERE user_id = $1 AND cluster_name = $2 AND is_active = true
                    ORDER BY created_at DESC
                    LIMIT 1
                """, user_id, cluster_name)
                
                if not row:
                    return None
                
                # Decrypt credentials
                credentials = self.auth_service.decrypt_credentials(row['encrypted_credentials'])
                
                # Update last used timestamp
                await conn.execute("""
                    UPDATE kubernetes_credentials
                    SET last_used_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, row['id'])
                
                return credentials
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve K8s credentials: {e}")
            return None
    
    async def list_clusters(self, user_id: int) -> list[dict[str, Any]]:
        """List all clusters for a user"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, cluster_name, auth_method, namespace, 
                           connection_status, last_used_at, created_at, metadata
                    FROM kubernetes_credentials
                    WHERE user_id = $1 AND is_active = true
                    ORDER BY last_used_at DESC NULLS LAST, created_at DESC
                """, user_id)
                
                clusters = []
                for row in rows:
                    clusters.append({
                        "id": row['id'],
                        "cluster_name": row['cluster_name'],
                        "auth_method": row['auth_method'],
                        "namespace": row['namespace'],
                        "connection_status": row['connection_status'],
                        "last_used_at": row['last_used_at'].isoformat() if row['last_used_at'] else None,
                        "created_at": row['created_at'].isoformat(),
                        "cluster_version": row['metadata'].get('cluster_version'),
                        "platform": row['metadata'].get('platform')
                    })
                
                return clusters
                
        except Exception as e:
            self.logger.error(f"Failed to list K8s clusters: {e}")
            return []
    
    async def update_connection_status(
        self,
        credential_id: str,
        status: str,
        error: Optional[str] = None
    ) -> None:
        """Update connection status for credentials"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE kubernetes_credentials
                    SET connection_status = $2, 
                        last_error = $3,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, credential_id, status, error)
                
        except Exception as e:
            self.logger.error(f"Failed to update connection status: {e}")
    
    async def delete_credentials(self, user_id: int, credential_id: str) -> bool:
        """Delete (deactivate) Kubernetes credentials"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute("""
                    UPDATE kubernetes_credentials
                    SET is_active = false, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1 AND user_id = $2 AND is_active = true
                """, credential_id, user_id)
                
                return result.split()[-1] == '1'  # Check if one row was updated
                
        except Exception as e:
            self.logger.error(f"Failed to delete K8s credentials: {e}")
            return False
    
    async def get_active_credential_for_integration(
        self,
        user_id: int,
        integration_id: str
    ) -> Optional[K8sCredentials]:
        """Get active credentials linked to a specific integration"""
        try:
            # First get the integration config to find the cluster name
            async with self.db_pool.acquire() as conn:
                integration = await conn.fetchrow("""
                    SELECT config FROM integrations
                    WHERE id = $1 AND user_id = $2 AND is_enabled = true
                """, integration_id, user_id)
                
                if not integration or not integration['config']:
                    return None
                
                cluster_name = integration['config'].get('cluster_name')
                if not cluster_name:
                    return None
                
                # Get credentials for this cluster
                return await self.get_credentials(user_id, cluster_name)
                
        except Exception as e:
            self.logger.error(f"Failed to get credentials for integration: {e}")
            return None