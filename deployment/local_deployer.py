"""
Local Deployment Module for BudgetGuard TechOps

Handles deployment of NVIDIA NIM instances to localhost (Docker)
"""

import logging
import subprocess
import time
import json
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalDeployer:
    """Deploys NIM instances locally using Docker"""
    
    def __init__(self, docker_compose_path: Optional[str] = None):
        """
        Initialize Local Deployer
        
        Args:
            docker_compose_path: Optional path to docker-compose.yml file
        """
        self.docker_compose_path = docker_compose_path or Path.home() / ".budgetguard_techops" / "docker-compose.yml"
        self.docker_compose_path = Path(self.docker_compose_path)
        self.docker_compose_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Local Deployer initialized with docker-compose: {self.docker_compose_path}")
    
    def deploy_nim_instance(self, node_type: str, instance_name: str = None) -> Dict:
        """
        Deploy a NIM instance locally
        
        Args:
            node_type: Type of NIM node (e.g., "FLUX Dev", "FLUX Canny")
            instance_name: Optional custom instance name
            
        Returns:
            Dictionary with deployment info including endpoint URL
        """
        if instance_name is None:
            instance_name = f"nim-{node_type.lower().replace(' ', '-')}-local"
        
        logger.info(f"Deploying {node_type} as {instance_name} locally")
        
        try:
            # Step 1: Get NVIDIA NIM container image
            image_uri = self._get_nim_image_uri(node_type)
            
            # Step 2: Ensure Docker is running
            if not self._check_docker():
                raise Exception("Docker is not running. Please start Docker Desktop.")
            
            # Step 3: Pull NIM container image if needed
            self._pull_image(image_uri)
            
            # Step 4: Create or update docker-compose.yml
            self._update_docker_compose(node_type, instance_name, image_uri)
            
            # Step 5: Start the container
            self._start_container(instance_name)
            
            # Step 6: Get endpoint URL (typically localhost:8000 for first instance)
            endpoint_url = self._get_endpoint_url(instance_name)
            
            deployment_info = {
                "node_type": node_type,
                "instance_name": instance_name,
                "provider": "local",
                "endpoint": endpoint_url,
                "deployed_at": datetime.utcnow().isoformat() + "Z",
                "status": "running"
            }
            
            logger.info(f"Successfully deployed {node_type} locally. Endpoint: {endpoint_url}")
            return deployment_info
            
        except Exception as e:
            logger.error(f"Failed to deploy {node_type} locally: {e}", exc_info=True)
            raise
    
    def _get_nim_image_uri(self, node_type: str) -> str:
        """Get Docker image URI for NIM node type"""
        # Map node types to NVIDIA NIM container images
        nim_image_map = {
            "FLUX Dev": "nvcr.io/nim/nim_flux_dev",
            "FLUX Canny": "nvcr.io/nim/nim_flux_canny",
            "FLUX Depth": "nvcr.io/nim/nim_flux_depth",
            "FLUX Kontext": "nvcr.io/nim/nim_flux_kontext",
            "SDXL": "nvcr.io/nim/nim_sdxl",
            "Llama 3": "nvcr.io/nim/nim_llama3",
            "Mixtral": "nvcr.io/nim/nim_mixtral",
            "Phi-3": "nvcr.io/nim/nim_phi3"
        }
        
        return nim_image_map.get(node_type, f"nvcr.io/nim/nim_{node_type.lower().replace(' ', '_')}")
    
    def _check_docker(self) -> bool:
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
    
    def _pull_image(self, image_uri: str):
        """Pull Docker image"""
        logger.info(f"Pulling Docker image: {image_uri}")
        try:
            subprocess.run(
                ["docker", "pull", image_uri],
                check=True,
                capture_output=True
            )
            logger.info(f"Successfully pulled image: {image_uri}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to pull image: {e}")
            raise Exception(f"Failed to pull Docker image: {image_uri}")
    
    def _update_docker_compose(self, node_type: str, instance_name: str, image_uri: str):
        """Create or update docker-compose.yml with new service"""
        # Read existing docker-compose.yml if it exists
        services = {}
        if self.docker_compose_path.exists():
            try:
                import yaml
                with open(self.docker_compose_path, 'r') as f:
                    compose_data = yaml.safe_load(f) or {}
                    services = compose_data.get('services', {})
            except Exception as e:
                logger.warning(f"Failed to read existing docker-compose.yml: {e}")
        
        # Calculate port (8000 for first, 8001 for second, etc.)
        base_port = 8000
        existing_ports = []
        for service_name, service_config in services.items():
            if 'ports' in service_config and service_config['ports']:
                for port_mapping in service_config['ports']:
                    if ':' in str(port_mapping):
                        host_port = int(str(port_mapping).split(':')[0])
                        existing_ports.append(host_port)
        
        next_port = base_port
        while next_port in existing_ports:
            next_port += 1
        
        # Add new service
        services[instance_name] = {
            'image': image_uri,
            'ports': [f"{next_port}:8000"],
            'environment': [
                f'NIM_MODEL={node_type}',
            ],
            'restart': 'unless-stopped',
            'name': instance_name
        }
        
        # Write docker-compose.yml
        try:
            import yaml
            compose_data = {
                'version': '3.8',
                'services': services
            }
            
            with open(self.docker_compose_path, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False)
            
            logger.info(f"Updated docker-compose.yml with service: {instance_name}")
        except Exception as e:
            logger.error(f"Failed to write docker-compose.yml: {e}")
            raise
    
    def _start_container(self, instance_name: str):
        """Start Docker container using docker-compose"""
        logger.info(f"Starting container: {instance_name}")
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.docker_compose_path), "up", "-d", instance_name],
                check=True,
                capture_output=True,
                cwd=self.docker_compose_path.parent
            )
            logger.info(f"Successfully started container: {instance_name}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start container: {e}")
            raise Exception(f"Failed to start container: {instance_name}")
    
    def _get_endpoint_url(self, instance_name: str) -> str:
        """Get endpoint URL for deployed NIM instance"""
        # Read docker-compose.yml to get port
        try:
            import yaml
            with open(self.docker_compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)
                service_config = compose_data.get('services', {}).get(instance_name, {})
                ports = service_config.get('ports', [])
                if ports:
                    port_mapping = ports[0]
                    if ':' in str(port_mapping):
                        host_port = int(str(port_mapping).split(':')[0])
                        return f"http://localhost:{host_port}"
        except Exception:
            pass
        
        # Default fallback
        return "http://localhost:8000"
    
    def get_deployment_status(self, instance_name: str) -> Dict:
        """Get status of a deployed instance"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={instance_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                status_line = result.stdout.strip()
                if "Up" in status_line:
                    return {
                        'status': 'running',
                        'runningCount': 1,
                        'desiredCount': 1
                    }
                else:
                    return {
                        'status': 'stopped',
                        'runningCount': 0,
                        'desiredCount': 1
                    }
        except Exception as e:
            logger.error(f"Error getting deployment status: {e}", exc_info=True)
        
        return {'status': 'unknown', 'runningCount': 0, 'desiredCount': 0}
    
    def list_deployments(self) -> list:
        """List all deployed NIM instances"""
        deployments = []
        
        try:
            import yaml
            if self.docker_compose_path.exists():
                with open(self.docker_compose_path, 'r') as f:
                    compose_data = yaml.safe_load(f) or {}
                    services = compose_data.get('services', {})
                    
                    for service_name, service_config in services.items():
                        if 'nim-' in service_name.lower():
                            endpoint = self._get_endpoint_url(service_name)
                            status = self.get_deployment_status(service_name)
                            
                            deployments.append({
                                'instance_name': service_name,
                                'status': status.get('status', 'unknown'),
                                'runningCount': status.get('runningCount', 0),
                                'endpoint': endpoint,
                                'provider': 'local',
                                'region': 'localhost'
                            })
        except Exception as e:
            logger.error(f"Error listing deployments: {e}", exc_info=True)
        
        return deployments
    
    def stop_deployment(self, instance_name: str) -> bool:
        """Stop a deployed NIM instance"""
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.docker_compose_path), "stop", instance_name],
                check=True,
                capture_output=True,
                cwd=self.docker_compose_path.parent
            )
            logger.info(f"Stopped deployment: {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error stopping deployment: {e}", exc_info=True)
            return False
    
    def start_deployment(self, instance_name: str) -> bool:
        """Start a stopped deployment"""
        try:
            subprocess.run(
                ["docker-compose", "-f", str(self.docker_compose_path), "start", instance_name],
                check=True,
                capture_output=True,
                cwd=self.docker_compose_path.parent
            )
            logger.info(f"Started deployment: {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error starting deployment: {e}", exc_info=True)
            return False

