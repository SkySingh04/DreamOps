"""Encryption service for secure storage of sensitive data."""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

from src.oncall_agent.utils.logger import get_logger
from src.oncall_agent.config import get_config


logger = get_logger(__name__)
config = get_config()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data like API keys."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize the encryption service.
        
        Args:
            encryption_key: Base64 encoded encryption key. If not provided,
                          will use from environment or generate new one.
        """
        self._fernet = self._initialize_fernet(encryption_key)
        
    def _initialize_fernet(self, encryption_key: Optional[str] = None) -> Fernet:
        """Initialize Fernet cipher with encryption key."""
        if encryption_key:
            # Use provided key
            key = base64.urlsafe_b64decode(encryption_key)
        else:
            # Try to get from environment
            env_key = os.getenv("ENCRYPTION_KEY")
            if env_key:
                key = base64.urlsafe_b64decode(env_key)
            else:
                # Derive key from a passphrase (not recommended for production)
                passphrase = os.getenv("ENCRYPTION_PASSPHRASE", "dreamops-default-key-change-me")
                salt = os.getenv("ENCRYPTION_SALT", "dreamops-salt").encode()
                
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
                
                logger.warning(
                    "Using derived encryption key. Set ENCRYPTION_KEY environment "
                    "variable for production use."
                )
        
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string.
        
        Args:
            plaintext: The string to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise ValueError("Failed to encrypt data")
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt an encrypted string.
        
        Args:
            ciphertext: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValueError("Failed to decrypt data")
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key for storage.
        
        Args:
            api_key: The API key to encrypt
            
        Returns:
            Encrypted API key
        """
        if not api_key:
            raise ValueError("API key cannot be empty")
            
        return self.encrypt(api_key)
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key for use.
        
        Args:
            encrypted_key: The encrypted API key
            
        Returns:
            Decrypted API key
        """
        if not encrypted_key:
            raise ValueError("Encrypted key cannot be empty")
            
        return self.decrypt(encrypted_key)
    
    def mask_api_key(self, api_key: str) -> str:
        """Create a masked version of an API key for display.
        
        Args:
            api_key: The API key to mask
            
        Returns:
            Masked API key (e.g., "sk-...abc123")
        """
        if not api_key or len(api_key) < 8:
            return "***"
            
        # Show first few characters and last few characters
        if api_key.startswith(("sk-", "pk_", "api_")):
            # Common API key prefixes
            prefix_end = api_key.find("-") + 1 if "-" in api_key[:4] else 3
            return f"{api_key[:prefix_end]}...{api_key[-4:]}"
        else:
            # Generic masking
            return f"{api_key[:3]}...{api_key[-4:]}"
    
    @staticmethod
    def generate_encryption_key() -> str:
        """Generate a new encryption key.
        
        Returns:
            Base64 encoded encryption key
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode()
    
    def rotate_encryption_key(self, new_key: str, old_encrypted_data: list[str]) -> list[str]:
        """Rotate encryption key by re-encrypting data.
        
        Args:
            new_key: New encryption key (base64 encoded)
            old_encrypted_data: List of encrypted strings using current key
            
        Returns:
            List of re-encrypted strings using new key
        """
        # Decrypt with current key
        decrypted_data = []
        for encrypted in old_encrypted_data:
            try:
                decrypted_data.append(self.decrypt(encrypted))
            except Exception as e:
                logger.error(f"Failed to decrypt during rotation: {str(e)}")
                raise
        
        # Create new service with new key
        new_service = EncryptionService(new_key)
        
        # Re-encrypt with new key
        new_encrypted_data = []
        for plaintext in decrypted_data:
            new_encrypted_data.append(new_service.encrypt(plaintext))
        
        return new_encrypted_data


# Global instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions
def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key using the global encryption service."""
    return get_encryption_service().encrypt_api_key(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key using the global encryption service."""
    return get_encryption_service().decrypt_api_key(encrypted_key)


def mask_api_key(api_key: str) -> str:
    """Create a masked version of an API key."""
    return get_encryption_service().mask_api_key(api_key)