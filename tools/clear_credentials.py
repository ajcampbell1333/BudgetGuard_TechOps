"""
Clear credentials from ConfigManager storage.

Usage:
    python tools/clear_credentials.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_manager import ConfigManager


def main():
    cfg_mgr = ConfigManager()
    
    if cfg_mgr.credentials_file.exists():
        cfg_mgr.credentials_file.unlink()
        print(f"Cleared credentials file: {cfg_mgr.credentials_file}")
    else:
        print("No credentials file found - nothing to clear.")


if __name__ == '__main__':
    main()

