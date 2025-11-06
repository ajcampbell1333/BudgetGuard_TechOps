"""
Install credentials and endpoints into ComfyUI backend config (scaffold).

Usage examples:
  python -m BudgetGuard_TechOps.tools.install_credentials --comfyui-path "C:\\ComfyUI" --studio-wide
  python -m BudgetGuard_TechOps.tools.install_credentials --comfyui-path "C:\\ComfyUI" --workstation "artist-01"

This is a scaffold: encryption and ComfyUI-specific integration will be implemented next.
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

from BudgetGuard_TechOps.config_manager import ConfigManager


def main():
    parser = argparse.ArgumentParser(description='Install credentials and endpoints into ComfyUI config (scaffold)')
    parser.add_argument('--comfyui-path', required=True, help='Path to ComfyUI root directory')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--studio-wide', action='store_true', help='Install shared studio-wide credentials')
    group.add_argument('--workstation', help='Install per-workstation credentials (e.g., artist-01)')
    args = parser.parse_args()

    cfg_mgr = ConfigManager()

    # Load endpoints saved by the GUI
    endpoints = cfg_mgr.load_endpoints()
    # Load credentials (placeholder: in real impl, pick studio-wide or workstation-specific files)
    creds = cfg_mgr.load_credentials()

    output_dir = Path(args.comfyui_path).expanduser().resolve() / 'budgetguard'
    output_dir.mkdir(parents=True, exist_ok=True)
    config_out = output_dir / 'budgetguard_backend_config.json'

    payload = {
        'installed_at': datetime.now().isoformat(timespec='seconds'),
        'mode': 'studio-wide' if args.studio-wide else f'workstation:{args.workstation}',
        'endpoints': endpoints,
        'credentials': creds,  # TODO: encrypt before writing
        'encryption': {
            'version': 0,
            'note': 'PLACEHOLDER - credentials are not yet encrypted in this scaffold.'
        }
    }

    with open(config_out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

    print(f'Wrote scaffold config to {config_out}')
    print('NOTE: Encryption and ComfyUI integration will be implemented next.')


if __name__ == '__main__':
    main()


