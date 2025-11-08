"""
Install local install package for NIM nodes.

This tool extracts a ZIP package created by create-install-package and runs
the installation script to load Docker images and create Docker Compose configuration.

Usage:
    python install_package.py --package ./install-package.zip
"""

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_docker() -> bool:
    """Check if Docker is running"""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def extract_package(zip_path: Path, extract_dir: Path) -> Path:
    """
    Extract ZIP package to directory.
    
    Args:
        zip_path: Path to ZIP file
        extract_dir: Directory to extract to
        
    Returns:
        Path to extracted package directory
    """
    logger.info(f"Extracting package: {zip_path}")
    
    if not zip_path.exists():
        raise FileNotFoundError(f"Package file not found: {zip_path}")
    
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(extract_dir)
    
    logger.info(f"Extracted package to: {extract_dir}")
    
    # Find install.py in extracted directory
    install_script = extract_dir / "install.py"
    if not install_script.exists():
        # Try to find it in a subdirectory
        install_scripts = list(extract_dir.rglob("install.py"))
        if install_scripts:
            install_script = install_scripts[0]
        else:
            raise FileNotFoundError(f"install.py not found in extracted package")
    
    return extract_dir


def run_install_script(package_dir: Path, compose_dir: Path = None) -> bool:
    """
    Run the install.py script from the extracted package.
    
    Args:
        package_dir: Directory containing extracted package
        compose_dir: Optional custom compose directory
        
    Returns:
        True if successful, False otherwise
    """
    install_script = package_dir / "install.py"
    
    if not install_script.exists():
        raise FileNotFoundError(f"install.py not found in package directory: {package_dir}")
    
    logger.info(f"Running installation script: {install_script}")
    
    # Build command
    cmd = [sys.executable, str(install_script)]
    if compose_dir:
        cmd.extend(["--compose-dir", str(compose_dir)])
    
    try:
        result = subprocess.run(
            cmd,
            cwd=package_dir,
            check=True,
            capture_output=False,  # Show output to user
            text=True
        )
        logger.info("Installation script completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Installation script failed with exit code {e.returncode}")
        return False


def install_package(zip_path: Path, compose_dir: Path = None, keep_extracted: bool = False) -> bool:
    """
    Install package from ZIP file.
    
    Args:
        zip_path: Path to ZIP package file
        compose_dir: Optional custom Docker Compose directory
        keep_extracted: If True, don't delete extracted files after installation
        
    Returns:
        True if successful, False otherwise
    """
    # Check Docker
    if not check_docker():
        logger.error("Docker is not running. Please start Docker and try again.")
        return False
    
    # Create temp directory for extraction
    temp_dir = Path(tempfile.mkdtemp(prefix="budgetguard_install_"))
    
    try:
        # Extract package
        package_dir = extract_package(zip_path, temp_dir)
        
        # Run installation script
        success = run_install_script(package_dir, compose_dir)
        
        if success:
            logger.info("Package installation completed successfully!")
            logger.info("Containers are left stopped - artists control via BudgetGuard GUI")
        else:
            logger.error("Package installation failed")
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to install package: {e}", exc_info=True)
        return False
    finally:
        # Cleanup temp directory unless requested to keep
        if not keep_extracted and temp_dir.exists():
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temp directory: {temp_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Install local install package for NIM nodes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install package (default compose dir: ~/.budgetguard_local)
  python install_package.py --package ./install-package.zip

  # Install package with custom compose directory
  python install_package.py --package ./install-package.zip --compose-dir /path/to/compose

  # Keep extracted files for debugging
  python install_package.py --package ./install-package.zip --keep-extracted
        """
    )
    
    parser.add_argument(
        '--package',
        type=Path,
        required=True,
        help='Path to ZIP package file (created by create-install-package)'
    )
    parser.add_argument(
        '--compose-dir',
        type=Path,
        help='Directory for Docker Compose configuration (default: ~/.budgetguard_local)'
    )
    parser.add_argument(
        '--keep-extracted',
        action='store_true',
        help='Keep extracted files after installation (for debugging)'
    )
    
    args = parser.parse_args()
    
    # Validate package file
    if not args.package.exists():
        logger.error(f"Package file not found: {args.package}")
        sys.exit(1)
    
    if not args.package.suffix.lower() == '.zip':
        logger.warning(f"Package file does not have .zip extension: {args.package}")
    
    # Install package
    success = install_package(
        args.package,
        compose_dir=args.compose_dir,
        keep_extracted=args.keep_extracted
    )
    
    if success:
        logger.info("✓ Package installation completed successfully!")
        sys.exit(0)
    else:
        logger.error("✗ Package installation failed")
        sys.exit(1)


if __name__ == '__main__':
    main()

