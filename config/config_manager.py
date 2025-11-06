"""
Configuration Manager for BudgetGuard TechOps

Handles:
- Credential storage (encrypted)
- Configuration file management
- Endpoint storage
"""

import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages configuration and credentials for BudgetGuard TechOps"""
    
    def __init__(self, config_dir=None):
        """
        Initialize ConfigManager
        
        Args:
            config_dir: Directory for config files (default: ~/.budgetguard_techops)
        """
        if config_dir is None:
            # Use home directory for cross-platform compatibility
            home_dir = Path.home()
            config_dir = home_dir / ".budgetguard_techops"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.credentials_file = self.config_dir / "credentials.encrypted"
        self.config_file = self.config_dir / "config.json"
        self.endpoints_file = self.config_dir / "endpoints.json"
        
        # Initialize encryption key
        self._init_encryption_key()
    
    def _init_encryption_key(self):
        """Initialize or load encryption key"""
        key_file = self.config_dir / ".encryption_key"
        
        if key_file.exists():
            # Load existing key
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new key
            # Use a password-based key derivation (in production, use a secure password)
            password = b"budgetguard_techops_default_key"  # TODO: Allow custom password
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            self.encryption_key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Save key (in production, this should be more secure)
            with open(key_file, 'wb') as f:
                f.write(self.encryption_key)
            key_file.chmod(0o600)  # Restrict permissions (Unix/Linux)
        
        self.cipher = Fernet(self.encryption_key)
    
    def save_credentials(self, credentials):
        """
        Save credentials with encryption
        
        Args:
            credentials: Dictionary of provider -> credential fields
        """
        try:
            # Convert to JSON string
            credentials_json = json.dumps(credentials)
            
            # Encrypt
            encrypted_data = self.cipher.encrypt(credentials_json.encode())
            
            # Save to file
            with open(self.credentials_file, 'wb') as f:
                f.write(encrypted_data)
            
            # Restrict file permissions (Unix/Linux)
            if os.name != 'nt':  # Not Windows
                os.chmod(self.credentials_file, 0o600)
            
            logger.info("Credentials saved successfully")
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}", exc_info=True)
            raise
    
    def load_credentials(self):
        """
        Load credentials from encrypted storage
        
        Returns:
            Dictionary of provider -> credential fields
        """
        try:
            if not self.credentials_file.exists():
                logger.warning("No credentials file found")
                return {}
            
            # Read encrypted data
            with open(self.credentials_file, 'rb') as f:
                encrypted_data = f.read()
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            logger.info("Credentials loaded successfully")
            return credentials
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}", exc_info=True)
            raise
    
    def save_endpoints(self, endpoints):
        """
        Save endpoint configuration
        
        Args:
            endpoints: List or Dictionary of endpoint info
        """
        try:
            with open(self.endpoints_file, 'w') as f:
                json.dump(endpoints, f, indent=2)
            logger.info("Endpoints saved successfully")
        except Exception as e:
            logger.error(f"Failed to save endpoints: {e}", exc_info=True)
            raise
    
    def load_endpoints(self):
        """
        Load endpoint configuration
        
        Returns:
            List or Dictionary of endpoint info
        """
        try:
            if not self.endpoints_file.exists():
                return []
            
            with open(self.endpoints_file, 'r') as f:
                endpoints = json.load(f)
            
            logger.info("Endpoints loaded successfully")
            return endpoints
        except Exception as e:
            logger.error(f"Failed to load endpoints: {e}", exc_info=True)
            return []
    
    def get_endpoints(self):
        """Alias for load_endpoints for backward compatibility"""
        return self.load_endpoints()
    
    def save_endpoint(self, endpoint):
        """Save a single endpoint (append to list)"""
        endpoints = self.load_endpoints()
        if not isinstance(endpoints, list):
            endpoints = []
        endpoints.append(endpoint)
        self.save_endpoints(endpoints)
    
    def save_config(self, config):
        """
        Save general configuration
        
        Args:
            config: Dictionary of configuration settings
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Config saved successfully")
        except Exception as e:
            logger.error(f"Failed to save config: {e}", exc_info=True)
            raise
    
    def load_config(self):
        """
        Load general configuration
        
        Returns:
            Dictionary of configuration settings
        """
        try:
            if not self.config_file.exists():
                return {}
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            return {}

