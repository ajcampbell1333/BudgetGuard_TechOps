"""
Deployment Handlers for BudgetGuard TechOps GUI

Provider-specific deployment methods with GPU tier mapping.
"""

import logging
import time

logger = logging.getLogger(__name__)


def deploy_to_aws(node_type: str, gpu_tier: str, config_manager):
    """
    Deploy a NIM node to AWS
    
    Args:
        node_type: Type of NIM node (e.g., "FLUX Dev")
        gpu_tier: GPU tier (t4, a10g, a100)
        config_manager: ConfigManager instance for credentials
        
    Returns:
        dict: Deployment info including endpoint URL
    """
    try:
        from deployment.aws_deployer import AWSDeployer
        
        # Get AWS credentials
        creds = config_manager.get_credentials('aws')
        if not creds or 'access_key_id' not in creds or 'secret_access_key' not in creds:
            raise Exception("AWS credentials not found. Please configure in Credentials tab.")
        
        # Map GPU tier to instance type if provided
        gpu_instance_type = None
        if gpu_tier:
            gpu_instance_type_map = {
                "t4": "g4dn.xlarge",
                "a10g": "g5.xlarge",
                "a100": "p4d.24xlarge"  # Note: This is 8x A100
            }
            gpu_instance_type = gpu_instance_type_map.get(gpu_tier.lower(), "g4dn.xlarge")
        
        # Initialize deployer with GPU instance type
        region = creds.get('region', 'us-east-1')
        deployer = AWSDeployer(
            access_key_id=creds['access_key_id'],
            secret_access_key=creds['secret_access_key'],
            region=region,
            gpu_instance_type=gpu_instance_type
        )
        
        # Create instance name with GPU tier suffix
        instance_name = None
        if gpu_tier:
            instance_name = f"{node_type.lower().replace(' ', '-')}-{gpu_tier}-aws-{int(time.time())}"
        
        # Deploy with scale_to_zero=True by default (containers start stopped)
        result = deployer.deploy_nim_instance(node_type, instance_name=instance_name, scale_to_zero=True)
        
        # Add GPU tier to result metadata
        if result and gpu_tier:
            result['gpu_tier'] = gpu_tier
            result['gpu_instance_type'] = gpu_instance_type
        
        return result
        
    except Exception as e:
        logger.error(f"AWS deployment failed: {e}", exc_info=True)
        raise


def deploy_to_azure(node_type: str, gpu_tier: str, config_manager):
    """
    Deploy a NIM node to Azure AKS
    
    Args:
        node_type: Type of NIM node (e.g., "FLUX Dev")
        gpu_tier: GPU tier (t4, a10g, a100)
        config_manager: ConfigManager instance for credentials
        
    Returns:
        dict: Deployment info including endpoint URL
    """
    try:
        from deployment.azure_deployer import AzureDeployer
        
        # Get Azure credentials
        creds = config_manager.get_credentials('azure')
        if not creds:
            raise Exception("Azure credentials not found. Please configure in Credentials tab.")
        
        # Map GUI field names to deployer parameters
        subscription_id = creds.get('Subscription ID') or creds.get('subscription_id')
        tenant_id = creds.get('Tenant ID') or creds.get('tenant_id')
        client_id = creds.get('Client ID (Application ID)') or creds.get('client_id') or creds.get('Application ID')
        client_secret = creds.get('Client Secret') or creds.get('client_secret')
        resource_group = creds.get('Resource Group') or creds.get('resource_group', 'budgetguard-nim-rg')
        region = creds.get('Region') or creds.get('region', 'eastus')
        
        if not subscription_id:
            raise Exception("Azure Subscription ID is required.")
        
        # Map GPU tier to Azure VM size
        # T4 -> NC6s_v3 (K80, cost-effective)
        # A10G -> NC24s_v3 (4x K80, recommended for SD/FLUX)
        # A100 -> ND96asr_v4 (8x A100, fastest)
        gpu_vm_size_map = {
            "t4": "Standard_NC6s_v3",      # 1x NVIDIA K80 GPU, 6 vCPU, 112 GB RAM
            "a10g": "Standard_NC24s_v3",   # 4x NVIDIA K80 GPU, 24 vCPU, 448 GB RAM (recommended)
            "a100": "Standard_ND96asr_v4"  # 8x NVIDIA A100 GPU, 96 vCPU, 900 GB RAM
        }
        
        gpu_vm_size = None
        if gpu_tier:
            gpu_vm_size = gpu_vm_size_map.get(gpu_tier.lower(), "Standard_NC6s_v3")
        
        # Initialize deployer with GPU VM size
        deployer = AzureDeployer(
            subscription_id=subscription_id,
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            resource_group=resource_group,
            region=region,
            gpu_vm_size=gpu_vm_size
        )
        
        # Create instance name with GPU tier suffix
        instance_name = None
        if gpu_tier:
            instance_name = f"{node_type.lower().replace(' ', '-')}-{gpu_tier}-azure-{int(time.time())}"
        
        # Deploy with scale_to_zero=True by default (containers start stopped)
        result = deployer.deploy_nim_instance(node_type, instance_name=instance_name, 
                                            scale_to_zero=True, gpu_tier=gpu_tier)
        
        # Add GPU tier to result metadata
        if result and gpu_tier:
            result['gpu_tier'] = gpu_tier
        
        return result
        
    except Exception as e:
        logger.error(f"Azure deployment failed: {e}", exc_info=True)
        raise


def deploy_to_gcp(node_type: str, gpu_tier: str, config_manager):
    """
    Deploy a NIM node to GCP GKE
    
    Args:
        node_type: Type of NIM node (e.g., "FLUX Dev")
        gpu_tier: GPU tier (t4, a10g, a100)
        config_manager: ConfigManager instance for credentials
        
    Returns:
        dict: Deployment info including endpoint URL
    """
    try:
        from deployment.gcp_deployer import GCPDeployer
        
        # Get GCP credentials
        creds = config_manager.get_credentials('gcp')
        if not creds:
            raise Exception("GCP credentials not found. Please configure in Credentials tab.")
        
        # Map GUI field names to deployer parameters
        project_id = creds.get('Project ID') or creds.get('project_id')
        credentials_path = creds.get('Service Account JSON Path') or creds.get('credentials_path')
        region = creds.get('Region') or creds.get('region', 'us-central1')
        zone = creds.get('Zone') or creds.get('zone')
        
        if not project_id:
            raise Exception("GCP Project ID is required.")
        
        # Map GPU tier to GCP machine type and GPU type
        # T4 -> n1-standard-4 + nvidia-tesla-t4 (cost-effective)
        # A10G -> a2-highgpu-1g + nvidia-a10 (recommended for SD/FLUX)
        # A100 -> a2-highgpu-4g + nvidia-a100 (fastest)
        gpu_config_map = {
            "t4": {
                "machine_type": "n1-standard-4",  # 4 vCPU, 15 GB RAM
                "gpu_type": "nvidia-tesla-t4"  # 1x NVIDIA T4 GPU
            },
            "a10g": {
                "machine_type": "a2-highgpu-1g",  # 12 vCPU, 85 GB RAM
                "gpu_type": "nvidia-a10"  # 1x NVIDIA A10G GPU (recommended)
            },
            "a100": {
                "machine_type": "a2-highgpu-4g",  # 48 vCPU, 340 GB RAM
                "gpu_type": "nvidia-a100"  # 4x NVIDIA A100 GPU (fastest)
            }
        }
        
        gpu_machine_type = None
        gpu_type = None
        if gpu_tier:
            gpu_config = gpu_config_map.get(gpu_tier.lower(), gpu_config_map["t4"])
            gpu_machine_type = gpu_config["machine_type"]
            gpu_type = gpu_config["gpu_type"]
        
        # Initialize deployer with GPU configuration
        deployer = GCPDeployer(
            project_id=project_id,
            credentials_path=credentials_path,
            region=region,
            zone=zone,
            gpu_machine_type=gpu_machine_type,
            gpu_type=gpu_type
        )
        
        # Create instance name with GPU tier suffix
        instance_name = None
        if gpu_tier:
            instance_name = f"{node_type.lower().replace(' ', '-')}-{gpu_tier}-gcp-{int(time.time())}"
        
        # Deploy with scale_to_zero=True by default (containers start stopped)
        result = deployer.deploy_nim_instance(node_type, instance_name=instance_name, 
                                            scale_to_zero=True, gpu_tier=gpu_tier)
        
        # Add GPU tier to result metadata
        if result and gpu_tier:
            result['gpu_tier'] = gpu_tier
        
        return result
        
    except Exception as e:
        logger.error(f"GCP deployment failed: {e}", exc_info=True)
        raise


def deploy_to_local(node_type: str, config_manager):
    """
    Deploy a NIM node locally
    
    Args:
        node_type: Type of NIM node (e.g., "FLUX Dev")
        config_manager: ConfigManager instance (not used for local, but kept for consistency)
        
    Returns:
        dict: Deployment info including endpoint URL
    """
    try:
        from deployment.local_deployer import LocalDeployer
        
        # Deploy locally
        deployer = LocalDeployer()
        result = deployer.deploy_nim_instance(node_type)
        return result
        
    except Exception as e:
        logger.error(f"Local deployment failed: {e}", exc_info=True)
        raise

