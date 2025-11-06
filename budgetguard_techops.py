#!/usr/bin/env python3
"""
BudgetGuard TechOps - NIM Deployment Automation Tool

Python application for automating NIM deployment across multiple cloud providers
(AWS, Azure, GCP) for VFX studios.

Usage:
    python budgetguard_techops.py gui          # Launch GUI
    python budgetguard_techops.py deploy ...   # Command line deployment
    python budgetguard_techops.py install-credentials ...  # Install credentials
"""

import sys
import argparse
import logging
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gui.main_window import BudgetGuardTechOpsGUI
    from config.config_manager import ConfigManager
    from utils.logger import setup_logging
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def main():
    """Main entry point for BudgetGuard TechOps"""
    parser = argparse.ArgumentParser(
        description='BudgetGuard TechOps - NIM Deployment Automation',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # GUI command
    gui_parser = subparsers.add_parser('gui', help='Launch the GUI application')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy NIM instances')
    deploy_parser.add_argument('--provider', choices=['aws', 'azure', 'gcp', 'all'], 
                               help='Cloud provider to deploy to')
    deploy_parser.add_argument('--nodes', type=str,
                               help='Comma-separated list of nodes (e.g., "FLUX Dev,FLUX Canny")')
    deploy_parser.add_argument('--region', type=str, default='us-east-1',
                               help='Region for deployment')
    
    # Install credentials command
    install_parser = subparsers.add_parser('install-credentials', 
                                          help='Install credentials to ComfyUI')
    install_parser.add_argument('--comfyui-path', type=str, required=True,
                               help='Path to ComfyUI installation')
    install_parser.add_argument('--workstation', type=str,
                               help='Workstation identifier')
    
    # Export endpoints command
    export_parser = subparsers.add_parser('export', help='Export endpoint configuration')
    export_parser.add_argument('--output', type=str, default='endpoints.json',
                               help='Output file path')
    
    # List deployments command
    list_parser = subparsers.add_parser('list', help='List all deployments')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Initialize config manager
    config_manager = ConfigManager()
    
    # Handle commands
    if args.command == 'gui' or args.command is None:
        # Launch GUI
        logger.info("Launching BudgetGuard TechOps GUI...")
        app = BudgetGuardTechOpsGUI(config_manager)
        app.run()
    elif args.command == 'deploy':
        logger.info(f"Deploy command: provider={args.provider}, nodes={args.nodes}")
        # TODO: Implement deployment logic
        print("Deployment functionality not yet implemented")
    elif args.command == 'install-credentials':
        logger.info(f"Installing credentials to: {args.comfyui_path}")
        # TODO: Implement credential installation
        print("Credential installation not yet implemented")
    elif args.command == 'export':
        logger.info(f"Exporting endpoints to: {args.output}")
        # TODO: Implement export logic
        print("Export functionality not yet implemented")
    elif args.command == 'list':
        logger.info("Listing deployments...")
        # TODO: Implement list logic
        print("List functionality not yet implemented")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

