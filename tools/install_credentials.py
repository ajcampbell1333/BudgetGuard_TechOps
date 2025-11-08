"""
Install credentials and endpoints into ComfyUI backend config.

This tool supports multiple deployment scenarios:
- Small studios: File share (TechOps exports files, artists copy to workstation)
- Mid-sized studios: RDP/SSH (TechOps connects, copies files, runs command)
- Large studios: Automation tools (Ansible/Puppet can script this)

Usage examples:
  # Using exported files (recommended for all scenarios)
  python -m BudgetGuard_TechOps.tools.install_credentials \
    --comfyui-path "C:\\ComfyUI" \
    --endpoints endpoints.json \
    --credentials credentials.json \
    --studio-wide

  # Using ConfigManager (only works when running on TechOps machine)
  python -m BudgetGuard_TechOps.tools.install_credentials \
    --comfyui-path "C:\\ComfyUI" \
    --from-config-manager \
    --studio-wide

  # Per-workstation installation
  python -m BudgetGuard_TechOps.tools.install_credentials \
    --comfyui-path "C:\\ComfyUI" \
    --endpoints endpoints.json \
    --credentials workstation-01-credentials.json \
    --workstation "workstation-01"
"""

import argparse
import json
import sys
import os
import base64
from pathlib import Path
from datetime import datetime, timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_manager import ConfigManager


def load_endpoints_from_file(endpoints_file: Path) -> dict:
    """Load endpoints from exported JSON file"""
    if not endpoints_file.exists():
        raise FileNotFoundError(f"Endpoints file not found: {endpoints_file}")
    
    with open(endpoints_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract nim_endpoints from exported config format
    if 'nim_endpoints' in data:
        return data['nim_endpoints']
    elif 'endpoints' in data:
        return data['endpoints']
    else:
        # Assume the file IS the endpoints structure
        return data


def load_credentials_from_file(credentials_file: Path) -> dict:
    """Load credentials from JSON file"""
    if not credentials_file.exists():
        raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
    
    with open(credentials_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_encryption_key(studio_key: str = None) -> bytes:
    """
    Get or generate encryption key for ComfyUI config.
    
    Uses a studio-wide encryption key so all workstations can decrypt.
    If studio_key is provided, uses that. Otherwise, uses a default studio-wide key.
    
    Args:
        studio_key: Optional studio-specific encryption key (password string)
        
    Returns:
        Fernet encryption key (bytes)
    """
    if studio_key:
        # Use provided studio key
        password = studio_key.encode()
    else:
        # Use default studio-wide key (same for all workstations in studio)
        # In production, TechOps should provide a secure studio-wide key
        password = b"budgetguard_studio_default_key"  # TODO: Allow custom studio key via config
    
    # Derive encryption key using PBKDF2 (same method as ConfigManager)
    salt = b"budgetguard_comfyui_salt"  # Fixed salt for studio-wide compatibility
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_credentials(creds: dict, encryption_key: bytes = None, studio_key: str = None) -> dict:
    """
    Encrypt credentials before writing to ComfyUI config.
    
    Uses Fernet encryption (same as ConfigManager) with a studio-wide key
    so all workstations can decrypt the credentials.
    
    Args:
        creds: Dictionary of credentials to encrypt
        encryption_key: Optional pre-computed Fernet key (bytes)
        studio_key: Optional studio-wide password string (used to derive key if encryption_key not provided)
        
    Returns:
        Dictionary with encrypted credentials and metadata
    """
    if encryption_key is None:
        encryption_key = get_encryption_key(studio_key)
    
    cipher = Fernet(encryption_key)
    
    # Convert credentials to JSON string
    creds_json = json.dumps(creds)
    
    # Encrypt
    encrypted_data = cipher.encrypt(creds_json.encode())
    
    # Return encrypted credentials with metadata
    return {
        'encrypted': True,
        'encryption_version': 1,
        'encryption_method': 'Fernet',
        'encrypted_data': base64.urlsafe_b64encode(encrypted_data).decode('utf-8'),
        'note': 'Credentials encrypted using Fernet. Artists node will decrypt using same studio-wide key.'
    }


def decrypt_credentials(encrypted_creds: dict, encryption_key: bytes = None, studio_key: str = None) -> dict:
    """
    Decrypt credentials from ComfyUI config.
    
    This is used by the Artists node to decrypt credentials.
    Uses the same studio-wide key that was used for encryption.
    
    Args:
        encrypted_creds: Dictionary with encrypted credentials (from config file)
        encryption_key: Optional pre-computed Fernet key (bytes)
        studio_key: Optional studio-wide password string (used to derive key if encryption_key not provided)
        
    Returns:
        Dictionary of decrypted credentials
    """
    if not encrypted_creds.get('encrypted', False):
        # Not encrypted (legacy format or placeholder)
        return encrypted_creds.get('credentials', encrypted_creds)
    
    if encryption_key is None:
        encryption_key = get_encryption_key(studio_key)
    
    cipher = Fernet(encryption_key)
    
    # Decode base64 encrypted data
    encrypted_data = base64.urlsafe_b64decode(encrypted_creds['encrypted_data'].encode('utf-8'))
    
    # Decrypt
    decrypted_data = cipher.decrypt(encrypted_data)
    creds = json.loads(decrypted_data.decode())
    
    return creds


def validate_credentials(creds: dict) -> bool:
    """
    Validate that credentials have required fields.
    
    Returns True if credentials appear valid, False otherwise.
    """
    if not isinstance(creds, dict):
        return False
    
    # Check for at least one provider's credentials
    providers = ['nvidia', 'aws', 'azure', 'gcp']
    has_any_creds = any(
        provider in creds and creds[provider] 
        for provider in providers
    )
    
    return has_any_creds


def build_comfyui_config(
    endpoints: dict,
    credentials: dict,
    mode: str,
    studio_key: str = None
) -> dict:
    """
    Build the ComfyUI backend config structure.
    
    This format is read by BudgetGuard Artists node on startup.
    Credentials are encrypted using a studio-wide key so all workstations can decrypt.
    
    Args:
        endpoints: Dictionary of NIM endpoints by node and provider
        credentials: Dictionary of credentials to encrypt
        mode: Installation mode ('studio-wide' or 'workstation:<id>')
        studio_key: Optional studio-wide encryption key (password string)
        
    Returns:
        Dictionary with config structure ready to write to ComfyUI backend config
    """
    # Encrypt credentials using studio-wide key
    encrypted_creds = encrypt_credentials(credentials, studio_key=studio_key)
    
    # Build credential status (booleans only, no secrets)
    cred_status = {
        'nvidia': bool(credentials.get('nvidia')),
        'aws': bool(credentials.get('aws')),
        'azure': bool(credentials.get('azure')),
        'gcp': bool(credentials.get('gcp')),
    }
    
    config = {
        'version': '1.0',
        'installed_at': datetime.now(timezone.utc).isoformat(),
        'mode': mode,
        'nim_endpoints': endpoints,
        'credentials': encrypted_creds,
        'credentials_status': cred_status,
    }
    
    return config


def main():
    parser = argparse.ArgumentParser(
        description='Install credentials and endpoints into ComfyUI backend config',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using exported files (recommended)
  python install_credentials.py \\
    --comfyui-path "C:\\ComfyUI" \\
    --endpoints endpoints.json \\
    --credentials credentials.json \\
    --studio-wide

  # With custom studio-wide encryption key (production)
  python install_credentials.py \\
    --comfyui-path "C:\\ComfyUI" \\
    --endpoints endpoints.json \\
    --credentials credentials.json \\
    --studio-wide \\
    --studio-key "your-secure-studio-password"

  # Per-workstation installation
  python install_credentials.py \\
    --comfyui-path "C:\\ComfyUI" \\
    --endpoints endpoints.json \\
    --credentials ws-01-creds.json \\
    --workstation "workstation-01"

  # Using ConfigManager (TechOps machine only)
  python install_credentials.py \\
    --comfyui-path "C:\\ComfyUI" \\
    --from-config-manager \\
    --studio-wide \\
    --studio-key "your-secure-studio-password"
        """
    )
    
    parser.add_argument(
        '--comfyui-path',
        required=True,
        help='Path to ComfyUI root directory'
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--studio-wide',
        action='store_true',
        help='Install shared studio-wide credentials'
    )
    mode_group.add_argument(
        '--workstation',
        help='Install per-workstation credentials (e.g., workstation-01)'
    )
    
    # Input source selection
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--from-config-manager',
        action='store_true',
        help='Read from ConfigManager (only works on TechOps machine)'
    )
    input_group.add_argument(
        '--endpoints',
        type=Path,
        help='Path to exported endpoints JSON file (from export.py)'
    )
    
    parser.add_argument(
        '--credentials',
        type=Path,
        help='Path to credentials JSON file (required if using --endpoints)'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Skip prompts and validation (useful for automation)'
    )
    
    parser.add_argument(
        '--studio-key',
        help='Studio-wide encryption key (password string). If not provided, uses default. All workstations must use the same key to decrypt.'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.endpoints and not args.credentials:
        parser.error("--credentials is required when using --endpoints")
    
    # Determine mode
    if args.studio_wide:
        mode = 'studio-wide'
    else:
        mode = f'workstation:{args.workstation}'
    
    # Load endpoints and credentials
    if args.from_config_manager:
        # Read from ConfigManager (TechOps machine only)
        cfg_mgr = ConfigManager()
        endpoints_data = cfg_mgr.load_endpoints()
        credentials_data = cfg_mgr.load_credentials()
        
        # Normalize endpoints to expected format
        # ConfigManager stores endpoints as list, need to convert to nim_endpoints format
        from tools.export import _normalize_endpoints, build_artist_config
        artist_config = build_artist_config(cfg_mgr)
        endpoints = artist_config.get('nim_endpoints', {})
        credentials = credentials_data
        
    else:
        # Read from files (works for all scenarios)
        endpoints = load_endpoints_from_file(args.endpoints)
        credentials = load_credentials_from_file(args.credentials)
    
    # Validate credentials
    if not args.non_interactive:
        if not validate_credentials(credentials):
            print("WARNING: Credentials appear to be invalid or empty.")
            response = input("Continue anyway? (y/n): ").strip().lower()
            if response != 'y':
                print("Installation cancelled.")
                sys.exit(1)
    
    # Build ComfyUI config
    comfyui_path = Path(args.comfyui_path).expanduser().resolve()
    if not comfyui_path.exists():
        raise FileNotFoundError(f"ComfyUI path does not exist: {comfyui_path}")
    
    # Warn if using default encryption key (in non-interactive mode, just proceed)
    if not args.studio_key and not args.non_interactive:
        print("WARNING: Using default studio-wide encryption key.")
        print("  For production use, specify --studio-key with a secure password.")
        print("  All workstations must use the same key to decrypt credentials.")
        response = input("Continue with default key? (y/n): ").strip().lower()
        if response != 'y':
            print("Installation cancelled.")
            sys.exit(1)
    
    config_data = build_comfyui_config(endpoints, credentials, mode, studio_key=args.studio_key)
    
    # Write to ComfyUI backend config
    output_dir = comfyui_path / 'budgetguard'
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = output_dir / 'budgetguard_backend_config.json'
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"✓ Successfully installed BudgetGuard config to: {config_file}")
    print(f"  Mode: {mode}")
    print(f"  Endpoints: {len(endpoints)} node types configured")
    print(f"  Credentials: {sum(1 for v in config_data['credentials_status'].values() if v)} providers configured")
    print(f"\nNext steps:")
    print(f"  1. Restart ComfyUI")
    print(f"  2. Add a BudgetGuard node to your workflow")
    print(f"  3. Check credential status in BudgetGuard Settings panel")


if __name__ == '__main__':
    main()
