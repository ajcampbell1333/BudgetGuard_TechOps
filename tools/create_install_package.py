"""
Create local install package for NIM nodes.

This tool creates a distributable ZIP package containing:
- Docker images (as tar files)
- Docker Compose YAML files
- Installation script

Usage:
    python create_install_package.py --nodes "FLUX Dev,FLUX Canny" --output ./install-package.zip
"""

import argparse
import json
import logging
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Dict

try:
    import yaml
except ImportError:
    yaml = None

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from deployment.local_deployer import LocalDeployer

logger = logging.getLogger(__name__)


# NIM node image mapping (same as LocalDeployer)
NIM_IMAGE_MAP = {
    "FLUX Dev": "nvcr.io/nim/nim_flux_dev",
    "FLUX Canny": "nvcr.io/nim/nim_flux_canny",
    "FLUX Depth": "nvcr.io/nim/nim_flux_depth",
    "FLUX Kontext": "nvcr.io/nim/nim_flux_kontext",
    "SDXL": "nvcr.io/nim/nim_sdxl",
    "Llama 3": "nvcr.io/nim/nim_llama3",
    "Mixtral": "nvcr.io/nim/nim_mixtral",
    "Phi-3": "nvcr.io/nim/nim_phi3"
}


def get_nim_image_uri(node_type: str) -> str:
    """Get Docker image URI for NIM node type"""
    return NIM_IMAGE_MAP.get(node_type, f"nvcr.io/nim/nim_{node_type.lower().replace(' ', '_')}")


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


def pull_docker_image(image_uri: str) -> bool:
    """Pull Docker image"""
    logger.info(f"Pulling Docker image: {image_uri}")
    try:
        result = subprocess.run(
            ["docker", "pull", image_uri],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Successfully pulled image: {image_uri}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to pull image {image_uri}: {e.stderr}")
        return False


def save_docker_image(image_uri: str, output_path: Path) -> bool:
    """Export Docker image to tar file"""
    logger.info(f"Exporting Docker image: {image_uri} to {output_path}")
    try:
        result = subprocess.run(
            ["docker", "save", image_uri, "-o", str(output_path)],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Successfully exported image to {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to export image {image_uri}: {e.stderr}")
        return False


def create_docker_compose_yaml(node_type: str, image_uri: str, port: int) -> str:
    """
    Create Docker Compose YAML for a NIM node.
    
    Args:
        node_type: Name of the NIM node (e.g., "FLUX Dev")
        image_uri: Docker image URI
        port: Port number for the service (8000 + index)
        
    Returns:
        YAML string for docker-compose.yml
    """
    # Sanitize node type for service name
    service_name = node_type.lower().replace(' ', '-').replace('_', '-')
    
    yaml_content = f"""version: '3.8'

services:
  {service_name}:
    image: {image_uri}
    container_name: budgetguard-{service_name}
    ports:
      - "{port}:8000"
    environment:
      - NIM_MODEL={node_type}
    restart: unless-stopped
    # GPU support (requires nvidia-docker or Docker with GPU support)
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
"""
    return yaml_content


def create_installation_script(node_types: List[str], ports: Dict[str, int], compose_files: Dict[str, str]) -> str:
    """
    Create Python installation script that loads images and starts containers.
    
    Args:
        node_types: List of NIM node types
        ports: Dictionary mapping node_type -> port number
        compose_files: Dictionary mapping node_type -> compose YAML content
        
    Returns:
        Python script content as string
    """
    script_content = '''#!/usr/bin/env python3
"""
BudgetGuard Local Install Package - Installation Script

This script loads Docker images and creates Docker Compose configuration
for local NIM node deployment.

Usage:
    python install.py [--compose-dir COMPOSE_DIR]
    
Note: Containers are always left stopped after installation.
      Artists control container start/stop via BudgetGuard GUI.
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def check_docker():
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


def load_docker_image(tar_path: Path) -> bool:
    """Load Docker image from tar file"""
    logger.info(f"Loading Docker image from {tar_path}")
    try:
        result = subprocess.run(
            ["docker", "load", "-i", str(tar_path)],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Successfully loaded image from {tar_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to load image from {tar_path}: {e.stderr}")
        return False


def create_compose_config(compose_dir: Path, compose_files: Dict[str, str]):
    """Create Docker Compose configuration directory"""
    if yaml is None:
        raise ImportError("PyYAML is required for Docker Compose file generation")
    
    compose_dir.mkdir(parents=True, exist_ok=True)
    
    # Create main docker-compose.yml with all services merged
    main_compose = compose_dir / "docker-compose.yml"
    
    # Merge all services into one compose file
    merged_services = {}
    
    for node_type, yaml_content in compose_files.items():
        # Parse individual compose file
        node_compose = yaml.safe_load(yaml_content)
        if 'services' in node_compose:
            merged_services.update(node_compose['services'])
    
    # Write merged compose file
    merged_compose = {
        'version': '3.8',
        'services': merged_services
    }
    
    with open(main_compose, 'w') as f:
        yaml.dump(merged_compose, f, default_flow_style=False, sort_keys=False)
    
    logger.info(f"Created main compose file: {main_compose}")
    
    # Also save individual files for reference
    for node_type, yaml_content in compose_files.items():
        compose_file = compose_dir / f"{node_type.lower().replace(' ', '-')}.yml"
        with open(compose_file, 'w') as f:
            f.write(yaml_content)
        logger.info(f"Created individual compose file: {compose_file}")


def main():
    parser = argparse.ArgumentParser(description='Install BudgetGuard local NIM nodes')
    parser.add_argument(
        '--compose-dir',
        type=Path,
        default=Path.home() / '.budgetguard_local',
        help='Directory for Docker Compose configuration (default: ~/.budgetguard_local)'
    )
    
    args = parser.parse_args()
    
    # Check Docker
    if not check_docker():
        logger.error("Docker is not running. Please start Docker and try again.")
        sys.exit(1)
    
    # Get package directory (where this script is located)
    package_dir = Path(__file__).parent
    
    # Load manifest
    manifest_file = package_dir / "manifest.json"
    if not manifest_file.exists():
        logger.error(f"Manifest file not found: {manifest_file}")
        sys.exit(1)
    
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    node_types = manifest.get('nodes', [])
    ports = manifest.get('ports', {})
    
    logger.info(f"Installing {len(node_types)} NIM nodes: {', '.join(node_types)}")
    
    # Load Docker images
    images_dir = package_dir / "images"
    for node_type in node_types:
        image_uri = manifest['images'].get(node_type)
        if not image_uri:
            logger.warning(f"No image URI found for {node_type}, skipping")
            continue
        
        # Find tar file (image name without registry)
        image_name = image_uri.split('/')[-1]
        tar_file = images_dir / f"{image_name}.tar"
        
        if not tar_file.exists():
            logger.warning(f"Image tar file not found: {tar_file}, skipping")
            continue
        
        if not load_docker_image(tar_file):
            logger.error(f"Failed to load image for {node_type}")
            continue
    
    # Create Docker Compose configuration
    compose_files = {}
    for node_type in node_types:
        # Read compose YAML from package
        compose_file = package_dir / "compose" / f"{node_type.lower().replace(' ', '-')}.yml"
        if compose_file.exists():
            with open(compose_file, 'r') as f:
                compose_files[node_type] = f.read()
        else:
            logger.warning(f"Compose file not found: {compose_file}")
    
    if compose_files:
        try:
            create_compose_config(args.compose_dir, compose_files)
        except ImportError as e:
            logger.error(f"PyYAML is required for Docker Compose file generation. Install with: pip install pyyaml")
            logger.error(f"Error: {e}")
            sys.exit(1)
    else:
        logger.error("No compose files found in package")
        sys.exit(1)
    
    # Containers are always left stopped - artists control via GUI
    logger.info("Installation complete. Containers are not started (artists control via BudgetGuard GUI).")
    logger.info(f"Compose configuration created at: {args.compose_dir}")
    
    logger.info("Installation complete!")


if __name__ == '__main__':
    main()
'''
    
    # Add node-specific information to script
    script_content = script_content.replace(
        '# Add node-specific information to script',
        f'# Nodes: {", ".join(node_types)}'
    )
    
    return script_content


def create_install_package(node_types: List[str], output_path: Path, temp_dir: Path = None) -> bool:
    """
    Create install package ZIP file.
    
    Args:
        node_types: List of NIM node types to include
        output_path: Path to output ZIP file
        temp_dir: Temporary directory for building package (if None, creates one)
        
    Returns:
        True if successful, False otherwise
    """
    # Check Docker
    if not check_docker():
        logger.error("Docker is not running. Please start Docker and try again.")
        return False
    
    # Create temp directory if not provided
    if temp_dir is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="budgetguard_package_"))
        cleanup_temp = True
    else:
        temp_dir = Path(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        cleanup_temp = False
    
    try:
        # Package structure
        images_dir = temp_dir / "images"
        compose_dir = temp_dir / "compose"
        images_dir.mkdir(exist_ok=True)
        compose_dir.mkdir(exist_ok=True)
        
        manifest = {
            "version": "1.0",
            "nodes": node_types,
            "images": {},
            "ports": {}
        }
        
        # Process each node
        port = 8001  # Start at 8001 (8000 is often used)
        for idx, node_type in enumerate(node_types):
            logger.info(f"Processing node {idx + 1}/{len(node_types)}: {node_type}")
            
            # Get image URI
            image_uri = get_nim_image_uri(node_type)
            manifest["images"][node_type] = image_uri
            
            # Pull image
            if not pull_docker_image(image_uri):
                logger.error(f"Failed to pull image for {node_type}, skipping")
                continue
            
            # Save image to tar file
            image_name = image_uri.split('/')[-1]
            tar_file = images_dir / f"{image_name}.tar"
            if not save_docker_image(image_uri, tar_file):
                logger.error(f"Failed to export image for {node_type}, skipping")
                continue
            
            # Create Docker Compose YAML
            compose_yaml = create_docker_compose_yaml(node_type, image_uri, port)
            compose_file = compose_dir / f"{node_type.lower().replace(' ', '-')}.yml"
            with open(compose_file, 'w') as f:
                f.write(compose_yaml)
            
            manifest["ports"][node_type] = port
            port += 1
        
        # Store compose files for installation script
        compose_files_dict = {}
        for node_type in node_types:
            compose_file = compose_dir / f"{node_type.lower().replace(' ', '-')}.yml"
            if compose_file.exists():
                with open(compose_file, 'r') as f:
                    compose_files_dict[node_type] = f.read()
        
        # Create installation script
        install_script = temp_dir / "install.py"
        script_content = create_installation_script(node_types, manifest["ports"], compose_files_dict)
        with open(install_script, 'w') as f:
            f.write(script_content)
        # Make executable (Unix/Linux) - Windows will ignore this
        try:
            install_script.chmod(0o755)
        except Exception:
            pass  # Windows doesn't support chmod
        
        # Create manifest.json
        manifest_file = temp_dir / "manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create README
        readme_content = f"""# BudgetGuard Local Install Package

This package contains Docker images and configuration for local NIM node deployment.

## Contents

- `images/` - Docker images as tar files
- `compose/` - Docker Compose YAML files for each node
- `install.py` - Installation script
- `manifest.json` - Package metadata

## Installation

1. Extract this ZIP file to a directory
2. Run the installation script:
   ```bash
   python install.py
   ```

To specify a custom Docker Compose directory:
```bash
python install.py --compose-dir /path/to/compose
```

**Note:** Containers are left stopped after installation. Artists control container start/stop via BudgetGuard GUI.

## Included Nodes

{chr(10).join(f"- {node}" for node in node_types)}

## Default Ports

{chr(10).join(f"- {node}: {manifest['ports'][node]}" for node in node_types)}

## Notes

- Docker must be installed and running
- GPU support requires nvidia-docker or Docker with GPU support
- Containers are created but not started by default (use --start to start immediately)
"""
        readme_file = temp_dir / "README.md"
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        # Create ZIP file
        logger.info(f"Creating ZIP package: {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add all files recursively
            for file_path in temp_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
                    logger.debug(f"Added to ZIP: {arcname}")
        
        logger.info(f"Successfully created install package: {output_path}")
        logger.info(f"Package size: {output_path.stat().st_size / (1024 * 1024):.2f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to create install package: {e}", exc_info=True)
        return False
    finally:
        # Cleanup temp directory if we created it
        if cleanup_temp and temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temp directory: {temp_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Create local install package for NIM nodes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create package with specific nodes
  python create_install_package.py --nodes "FLUX Dev,FLUX Canny" --output ./install-package.zip

  # Create package with all available nodes
  python create_install_package.py --nodes "FLUX Dev,FLUX Canny,FLUX Depth,SDXL" --output ./install-package.zip
        """
    )
    
    parser.add_argument(
        '--nodes',
        type=str,
        required=True,
        help='Comma-separated list of NIM node types (e.g., "FLUX Dev,FLUX Canny")'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output path for ZIP package'
    )
    parser.add_argument(
        '--temp-dir',
        type=Path,
        help='Temporary directory for building package (optional, creates temp dir if not specified)'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse node types
    node_types = [node.strip() for node in args.nodes.split(',')]
    
    # Validate node types
    invalid_nodes = [node for node in node_types if node not in NIM_IMAGE_MAP]
    if invalid_nodes:
        logger.error(f"Invalid node types: {', '.join(invalid_nodes)}")
        logger.info(f"Available node types: {', '.join(NIM_IMAGE_MAP.keys())}")
        sys.exit(1)
    
    # Create package
    success = create_install_package(node_types, args.output, args.temp_dir)
    
    if success:
        logger.info("Install package created successfully!")
        sys.exit(0)
    else:
        logger.error("Failed to create install package")
        sys.exit(1)


if __name__ == '__main__':
    main()

