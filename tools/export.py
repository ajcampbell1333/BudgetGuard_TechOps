"""
Export BudgetGuard data (config, endpoints, credentials, etc.)

Usage:
    python tools/export.py --config --out path/to/budgetguard_artists_config.json
    python tools/export.py --config  # Uses default output filename
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path so we can import ConfigManager
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_manager import ConfigManager


def _normalize_endpoints(endpoints):
    if isinstance(endpoints, dict):
        items = []
        for _, value in endpoints.items():
            if isinstance(value, list):
                items.extend(value)
            else:
                items.append(value)
        return items
    return endpoints if isinstance(endpoints, list) else []


def build_artist_config(config_manager: ConfigManager) -> dict:
    endpoints = config_manager.load_endpoints()
    endpoint_list = _normalize_endpoints(endpoints)

    nim_endpoints = {}
    for item in endpoint_list:
        # Expected keys from deployers: node_type, provider, endpoint, optional gpu_tier
        node = item.get('node_type') or item.get('node')
        provider = (item.get('provider') or '').lower()
        url = item.get('endpoint') or item.get('url')
        gpu_tier = item.get('gpu_tier')
        if not node or not provider or not url:
            continue
        nim_endpoints.setdefault(node, {}).setdefault(provider, []).append(
            {k: v for k, v in (('url', url), ('gpu_tier', gpu_tier)) if v}
        )

    # Credential status is a coarse boolean
    all_creds = config_manager.load_credentials()
    cred_status = {
        'nvidia': bool(all_creds.get('nvidia')),
        'aws': bool(all_creds.get('aws')),
        'azure': bool(all_creds.get('azure')),
        'gcp': bool(all_creds.get('gcp')),
    }

    cfg = {
        'version': '1.0',
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'nim_endpoints': nim_endpoints,
        'credentials_status': cred_status,
    }
    return cfg


def create_dummy_credentials():
    """Create dummy credentials for testing"""
    return {
        'nvidia': {
            'NVIDIA API Key / NGC API Key': 'dummy-nvidia-api-key-for-testing'
        },
        'aws': {
            'Access Key ID': 'AKIADUMMYTEST123',
            'Secret Access Key': 'dummy-secret-key-for-testing'
        },
        'azure': {
            'Subscription ID': '00000000-0000-0000-0000-000000000000',
            'Tenant ID': '00000000-0000-0000-0000-000000000000',
            'Client ID (Application ID)': '00000000-0000-0000-0000-000000000000',
            'Client Secret': 'dummy-client-secret',
            'Resource Group': 'budgetguard-test-rg',
            'Region': 'eastus'
        },
        'gcp': {
            'Project ID': 'dummy-project-id',
            'Service Account JSON File Path': '/path/to/dummy/service-account.json',
            'Region': 'us-central1',
            'Zone': 'us-central1-a'
        }
    }


def is_dummy_credentials(creds):
    """Check if credentials are dummy/test data"""
    if not creds:
        return False
    
    # Check for dummy markers
    dummy_markers = [
        'dummy',
        'AKIADUMMY',
        '00000000-0000-0000-0000-000000000000',  # All-zero GUIDs
        'budgetguard-test',
        '/path/to/dummy'
    ]
    
    creds_str = json.dumps(creds).lower()
    return any(marker.lower() in creds_str for marker in dummy_markers)


def main():
    parser = argparse.ArgumentParser(description='Export BudgetGuard data')
    parser.add_argument(
        '--config',
        action='store_true',
        help='Export artist config JSON (endpoints + credential status)'
    )
    parser.add_argument(
        '--out',
        help='Output path (default: budgetguard_artists_config.json in current directory, or tests/ if dummy credentials created)'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Skip prompts and use defaults (useful for scripts)'
    )
    args = parser.parse_args()
    
    # For now, only --config is supported
    if not args.config:
        parser.error("Please specify what to export (e.g., --config). More export types coming soon.")
    
    # Set default output if not provided
    if not args.out:
        args.out = 'budgetguard_artists_config.json'

    cfg_mgr = ConfigManager()
    
    # Check if credentials exist and if they're dummy
    dummy_created = False
    dummy_creds = None
    creds_exist = cfg_mgr.credentials_file.exists()
    
    if creds_exist:
        existing_creds = cfg_mgr.load_credentials()
        if is_dummy_credentials(existing_creds):
            # Existing credentials are dummy - ignore them and treat as if no credentials
            creds_exist = False
    
    if not creds_exist:
        if not args.non_interactive:
            response = input("No credentials file found. Generate dummy credentials for testing? (y/n): ").strip().lower()
            if response == 'y':
                print("Creating dummy credentials (in-memory only, not saved to storage)...")
                dummy_creds = create_dummy_credentials()
                dummy_created = True
        else:
            print("No credentials file found (non-interactive mode, skipping dummy creation)")
    
    # If dummy credentials were created and output is just a filename (no path), save to tests/ directory
    if dummy_created:
        output_path = Path(args.out)
        # Check if it's just a filename (no directory separators in the original string)
        if '/' not in args.out and '\\' not in args.out and str(output_path.parent) == '.':
            # Just a filename, no directory path - save to tests/ directory
            tests_dir = Path(__file__).parent.parent / 'tests'
            tests_dir.mkdir(exist_ok=True)
            output_path = tests_dir / output_path.name
            args.out = str(output_path)
    
    # Build config - use dummy creds if created, otherwise use ConfigManager
    if dummy_creds:
        # Temporarily inject dummy credentials for export only
        # Create a temporary config manager that uses dummy creds
        class TempConfigManager:
            def __init__(self, base_cfg_mgr, dummy_creds):
                self.base = base_cfg_mgr
                self._dummy_creds = dummy_creds
                self.credentials_file = base_cfg_mgr.credentials_file
                self.endpoints_file = base_cfg_mgr.endpoints_file
            
            def load_endpoints(self):
                return self.base.load_endpoints()
            
            def load_credentials(self):
                return self._dummy_creds
        
        temp_cfg_mgr = TempConfigManager(cfg_mgr, dummy_creds)
        cfg = build_artist_config(temp_cfg_mgr)
    else:
        cfg = build_artist_config(cfg_mgr)

    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

    if dummy_created:
        print(f'Wrote dummy config to {args.out}')
    else:
        print(f'Wrote Artists config to {args.out}')


if __name__ == '__main__':
    main()


