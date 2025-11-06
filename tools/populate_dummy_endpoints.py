"""
Populate ConfigManager's local storage with dummy endpoint data for testing.

This fills the endpoints.json file (in ~/.budgetguard_techops/) with example
endpoint data that matches the format created by actual deployments.

Usage:
    python tools\populate_dummy_endpoints.py
    python tools\populate_dummy_endpoints.py --clear  # Clear existing endpoints first
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path so we can import ConfigManager
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_manager import ConfigManager


def create_dummy_endpoints():
    """Create dummy endpoint data matching the format from deployers"""
    
    # All NIM nodes we support
    nim_nodes = [
        "FLUX Dev",
        "FLUX Canny",
        "FLUX Depth",
        "FLUX Kontext",
        "SDXL",
        "Llama 3",
        "Mixtral",
        "Phi-3"
    ]
    
    # GPU tiers
    gpu_tiers = ["t4", "a10g", "a100"]
    
    # Providers
    providers = [
        ("aws", "us-east-1", "elb.amazonaws.com"),
        ("azure", "eastus", "cloudapp.azure.com"),
        ("gcp", "us-central1", "run.app"),
    ]
    
    endpoints = []
    
    for node in nim_nodes:
        node_key = node.lower().replace(' ', '-')
        
        # AWS endpoints
        for tier in gpu_tiers:
            endpoints.append({
                "node_type": node,
                "provider": "aws",
                "endpoint": f"https://nim-{node_key}-{tier}-aws-12345.us-east-1.elb.amazonaws.com:8000",
                "gpu_tier": tier,
                "region": "us-east-1",
                "instance_name": f"nim-{node_key}-{tier}-aws-12345",
                "deployed_at": "2025-11-06T16:00:00Z"
            })
        
        # Azure endpoints
        for tier in gpu_tiers:
            endpoints.append({
                "node_type": node,
                "provider": "azure",
                "endpoint": f"https://nim-{node_key}-{tier}-azure-12345.eastus.cloudapp.azure.com:8000",
                "gpu_tier": tier,
                "region": "eastus",
                "instance_name": f"nim-{node_key}-{tier}-azure-12345",
                "deployed_at": "2025-11-06T16:00:00Z"
            })
        
        # GCP endpoints
        for tier in gpu_tiers:
            endpoints.append({
                "node_type": node,
                "provider": "gcp",
                "endpoint": f"https://nim-{node_key}-{tier}-gcp-12345.us-central1.run.app:8000",
                "gpu_tier": tier,
                "region": "us-central1",
                "instance_name": f"nim-{node_key}-{tier}-gcp-12345",
                "deployed_at": "2025-11-06T16:00:00Z"
            })
        
        # NVIDIA-hosted (one per node, typically A10G)
        endpoints.append({
            "node_type": node,
            "provider": "nvidia-hosted",
            "endpoint": f"https://nim-{node_key}.ngc.nvidia.com/v1",
            "gpu_tier": "a10g",
            "deployed_at": "2025-11-06T16:00:00Z"
        })
        
        # Local (one per node, no GPU tier)
        endpoints.append({
            "node_type": node,
            "provider": "local",
            "endpoint": "http://localhost:8000",
            "gpu_tier": None,
            "deployed_at": "2025-11-06T16:00:00Z"
        })
    
    return endpoints


def main():
    parser = argparse.ArgumentParser(
        description='Populate ConfigManager local storage with dummy endpoint data for testing'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing endpoints before populating (default: append)'
    )
    args = parser.parse_args()
    
    cfg_mgr = ConfigManager()
    
    if args.clear:
        # Clear existing endpoints
        cfg_mgr.save_endpoints([])
        print("Cleared existing endpoints.")
    
    # Create dummy endpoints
    dummy_endpoints = create_dummy_endpoints()
    
    if not args.clear:
        # Append to existing endpoints
        existing = cfg_mgr.load_endpoints()
        if isinstance(existing, list):
            dummy_endpoints = existing + dummy_endpoints
        elif isinstance(existing, dict):
            # Convert dict to list if needed
            all_items = []
            for _, value in existing.items():
                if isinstance(value, list):
                    all_items.extend(value)
                else:
                    all_items.append(value)
            dummy_endpoints = all_items + dummy_endpoints
    
    # Save to ConfigManager storage
    cfg_mgr.save_endpoints(dummy_endpoints)
    
    print(f"Populated {len(dummy_endpoints)} dummy endpoints into ConfigManager storage.")
    print(f"Storage location: {cfg_mgr.endpoints_file}")
    print("\nYou can now test export_artist_config.py:")
    print("  python tools\\export_artist_config.py --out test_export.json")


if __name__ == '__main__':
    main()

