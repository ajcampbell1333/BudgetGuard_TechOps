"""
Azure Deployment Module for BudgetGuard TechOps

Handles deployment of NVIDIA NIM instances to Azure AKS (Azure Kubernetes Service) with GPU support.

Note: GPU workloads require AKS with GPU node pools (NC-series, ND-series).
Container Apps and Container Instances do not support GPUs.

Phase 3.5: Migrated from Container Instances to AKS with GPU node pools.

See PLATFORM_SELECTION_GPU_REQUIREMENTS.md for details.
"""

import logging
import time
import base64
import yaml
from typing import Dict, List, Optional
from datetime import datetime

try:
    from azure.identity import DefaultAzureCredential, ClientSecretCredential
    from azure.mgmt.containerservice import ContainerServiceClient
    from azure.mgmt.containerservice.models import (
        ManagedCluster, ContainerServiceNetworkProfile, ManagedClusterAgentPoolProfile,
        AgentPoolMode, AgentPoolType, ScaleSetPriority, ScaleSetEvictionPolicy,
        ManagedClusterLoadBalancerProfile, ManagedClusterLoadBalancerProfileManagedOutboundIPs,
        ManagedClusterServicePrincipalProfile, ContainerServiceLinuxProfile,
        ContainerServiceSshConfiguration, ContainerServiceSshPublicKey
    )
    from azure.mgmt.resource import ResourceManagementClient
    from azure.core.exceptions import AzureError
    from kubernetes import client, config
    from kubernetes.client import V1Deployment, V1Service, V1ObjectMeta, V1PodSpec, \
        V1Container, V1ContainerPort, V1ResourceRequirements, V1ServicePort, \
        V1ServiceSpec, V1DeploymentSpec, V1PodTemplateSpec, V1LabelSelector, \
        V1EnvVar, AppsV1Api, CoreV1Api
    from kubernetes.client.rest import ApiException
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Azure/Kubernetes SDK not installed. Install with: pip install azure-identity azure-mgmt-containerservice kubernetes")
    raise

logger = logging.getLogger(__name__)


class AzureDeployer:
    """Deploys NIM instances to Azure AKS (Azure Kubernetes Service) with GPU support"""
    
    def __init__(self, subscription_id: str, tenant_id: str = None, 
                 client_id: str = None, client_secret: str = None,
                 resource_group: str = None, region: str = 'eastus',
                 gpu_vm_size: str = None):
        """
        Initialize Azure Deployer for AKS
        
        Args:
            subscription_id: Azure Subscription ID
            tenant_id: Azure Tenant ID (optional, uses DefaultAzureCredential if not provided)
            client_id: Azure Client ID (Service Principal)
            client_secret: Azure Client Secret (Service Principal)
            resource_group: Azure Resource Group name (default: budgetguard-nim-rg)
            region: Azure region (default: eastus)
            gpu_vm_size: GPU VM size for node pool (default: Standard_NC6s_v3 for T4/K80,
                        or Standard_ND96asr_v4 for A100 - recommended for SD/FLUX models)
        """
        self.subscription_id = subscription_id
        self.region = region
        self.resource_group = resource_group or "budgetguard-nim-rg"
        self.cluster_name = "budgetguard-nim-aks"
        
        # Default GPU VM size (can be overridden)
        # NC6s_v3: 6 vCPU, 112 GB RAM, 1x NVIDIA K80 GPU (older, cheaper)
        # ND96asr_v4: 96 vCPU, 900 GB RAM, 8x NVIDIA A100 GPU (best performance, expensive)
        # NC24s_v3: 24 vCPU, 448 GB RAM, 4x NVIDIA K80 GPU (good balance)
        # For production SD/FLUX, consider NC24s_v3 or ND96asr_v4
        if gpu_vm_size:
            self.gpu_vm_size = gpu_vm_size
        else:
            # Default to NC6s_v3 (K80) for cost-effectiveness
            # For production SD/FLUX, consider NC24s_v3 (4x K80) or ND96asr_v4 (8x A100)
            self.gpu_vm_size = 'Standard_NC6s_v3'  # 1x NVIDIA K80 GPU
        
        # Initialize Azure credentials
        if tenant_id and client_id and client_secret:
            # Use Service Principal
            self.credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret
            )
        else:
            # Use DefaultAzureCredential (works with Azure CLI, Managed Identity, etc.)
            self.credential = DefaultAzureCredential()
        
        # Initialize Azure AKS client
        self.aks_client = ContainerServiceClient(
            self.credential,
            self.subscription_id
        )
        
        # Initialize Resource Management client
        self.resource_client = ResourceManagementClient(
            self.credential,
            self.subscription_id
        )
        
        # Kubernetes client (will be initialized after cluster is created)
        self.k8s_client = None
        self.k8s_apps_api = None
        self.k8s_core_api = None
        
        logger.info(f"Azure AKS Deployer initialized for region: {region}, resource group: {resource_group}, GPU VM size: {self.gpu_vm_size}")
        
        # Ensure resource group exists
        self._ensure_resource_group()
    
    def _ensure_resource_group(self):
        """Ensure resource group exists"""
        try:
            # Check if resource group exists
            try:
                self.resource_client.resource_groups.get(self.resource_group)
                logger.info(f"Resource group {self.resource_group} exists")
            except AzureError:
                # Create resource group
                logger.info(f"Creating resource group: {self.resource_group}")
                self.resource_client.resource_groups.create_or_update(
                    self.resource_group,
                    {"location": self.region}
                )
                logger.info(f"Resource group {self.resource_group} created")
        except Exception as e:
            logger.warning(f"Could not ensure resource group exists: {e}")
    
    def deploy_nim_instance(self, node_type: str, instance_name: str = None,
                           scale_to_zero: bool = True, gpu_tier: str = None) -> Dict:
        """
        Deploy a NIM instance to Azure AKS
        
        Args:
            node_type: Type of NIM node (e.g., "FLUX Dev", "FLUX Canny")
            instance_name: Optional custom instance name
            scale_to_zero: If True, deployment starts with 0 replicas (stopped)
            gpu_tier: GPU tier (t4, a10g, a100) - used for naming, actual GPU depends on VM size
            
        Returns:
            Dictionary with deployment info including endpoint URL
        """
        if instance_name is None:
            gpu_suffix = f"-{gpu_tier}" if gpu_tier else ""
            instance_name = f"nim-{node_type.lower().replace(' ', '-')}{gpu_suffix}-{int(time.time())}"
        
        logger.info(f"Deploying {node_type} as {instance_name} to Azure AKS {self.region}")
        
        try:
            # Step 1: Get or create AKS cluster with GPU node pool
            cluster = self._get_or_create_aks_cluster()
            
            # Step 2: Initialize Kubernetes client
            self._initialize_k8s_client(cluster)
            
            # Step 3: Get NVIDIA NIM container image
            image_uri = self._get_nim_image_uri(node_type)
            
            # Step 4: Create Kubernetes deployment with GPU resources
            deployment = self._create_k8s_deployment(
                instance_name, node_type, image_uri, scale_to_zero
            )
            
            # Step 5: Create Kubernetes service (LoadBalancer) for endpoint access
            service = self._create_k8s_service(instance_name)
            
            # Step 6: Wait for deployment to be ready (if not scale_to_zero)
            if not scale_to_zero:
                self._wait_for_deployment_ready(instance_name)
            
            # Step 7: Get endpoint URL from LoadBalancer service
            endpoint_url = self._get_endpoint_url(instance_name)
            
            deployment_info = {
                "node_type": node_type,
                "instance_name": instance_name,
                "provider": "azure",
                "region": self.region,
                "resource_group": self.resource_group,
                "cluster": self.cluster_name,
                "endpoint": endpoint_url,
                "deployed_at": datetime.utcnow().isoformat() + "Z",
                "status": "stopped" if scale_to_zero else "running",
                "gpu_vm_size": self.gpu_vm_size,
                "gpu_tier": gpu_tier
            }
            
            logger.info(f"Successfully deployed {node_type} to Azure AKS. Endpoint: {endpoint_url}")
            return deployment_info
            
        except Exception as e:
            logger.error(f"Failed to deploy {node_type} to Azure AKS: {e}", exc_info=True)
            raise
    
    def _get_or_create_aks_cluster(self) -> ManagedCluster:
        """Get existing AKS cluster or create new one with GPU node pool"""
        try:
            # Check if cluster exists
            try:
                cluster = self.aks_client.managed_clusters.get(
                    self.resource_group,
                    self.cluster_name
                )
                logger.info(f"Using existing AKS cluster: {self.cluster_name}")
                
                # Check if GPU node pool exists
                if not self._has_gpu_node_pool(cluster):
                    logger.info("GPU node pool not found, creating...")
                    self._create_gpu_node_pool(cluster)
                
                return cluster
            except AzureError:
                pass  # Cluster doesn't exist, create it
        
        # Create new AKS cluster with GPU node pool
        logger.info(f"Creating new AKS cluster: {self.cluster_name} with GPU node pool")
        
        # Get or create service principal for AKS
        service_principal = self._get_or_create_service_principal()
        
        # Create AKS cluster configuration
        # Note: Service principal is required for AKS. If not provided, AKS will create one automatically
        # but it's recommended to create one explicitly for production use.
        cluster_config = {
            'location': self.region,
            'dns_prefix': self.cluster_name,
            'kubernetes_version': "1.28",  # Use latest stable version
            'network_profile': ContainerServiceNetworkProfile(
                network_plugin="kubenet",
                service_cidr="10.0.0.0/16",
                dns_service_ip="10.0.0.10"
            ),
        }
        
        # Add service principal if available (otherwise AKS will create one)
        if service_principal.get('client_id') != 'placeholder':
            cluster_config['service_principal_profile'] = ManagedClusterServicePrincipalProfile(
                client_id=service_principal['client_id'],
                secret=service_principal['client_secret']
            )
        
        # SSH key is optional - only add if needed
        # For most deployments, SSH access to nodes is not required
        
        # Add agent pool profiles
        cluster_config['agent_pool_profiles'] = [
            # Default system node pool (CPU-only, small)
            ManagedClusterAgentPoolProfile(
                name="systempool",
                count=1,
                vm_size="Standard_DS2_v2",  # 2 vCPU, 7 GB RAM (CPU-only)
                os_type="Linux",
                mode=AgentPoolMode.SYSTEM,
                type=AgentPoolType.VIRTUAL_MACHINE_SCALE_SETS,
                min_count=1,
                max_count=3
            ),
            # GPU node pool
            ManagedClusterAgentPoolProfile(
                name="gpunodepool",
                count=0,  # Start with 0 nodes (scale-to-zero)
                vm_size=self.gpu_vm_size,  # GPU instance
                os_type="Linux",
                mode=AgentPoolMode.USER,
                type=AgentPoolType.VIRTUAL_MACHINE_SCALE_SETS,
                min_count=0,  # Allow scale-to-zero
                max_count=10,  # Max nodes for manual scaling
                node_taints=["nvidia.com/gpu=true:NoSchedule"]  # Taint to require GPU workloads
            )
        ]
        
        # Add load balancer profile
        cluster_config['load_balancer_profile'] = ManagedClusterLoadBalancerProfile(
            managed_outbound_ips=ManagedClusterLoadBalancerProfileManagedOutboundIPs(
                count=1
            )
        )
        
        cluster = ManagedCluster(**cluster_config)
        
        # Create cluster (this takes 10-15 minutes)
        logger.info(f"Creating AKS cluster (this may take 10-15 minutes)...")
        poller = self.aks_client.managed_clusters.begin_create_or_update(
            self.resource_group,
            self.cluster_name,
            cluster
        )
        cluster = poller.result()
        
        logger.info(f"AKS cluster {self.cluster_name} created successfully")
        return cluster
    
    def _has_gpu_node_pool(self, cluster: ManagedCluster) -> bool:
        """Check if cluster has a GPU node pool"""
        if not cluster.agent_pool_profiles:
            return False
        for pool in cluster.agent_pool_profiles:
            if 'gpu' in pool.name.lower() or 'nc' in pool.vm_size.lower() or 'nd' in pool.vm_size.lower():
                return True
        return False
    
    def _create_gpu_node_pool(self, cluster: ManagedCluster):
        """Create GPU node pool in existing cluster"""
        logger.info(f"Creating GPU node pool in cluster: {self.cluster_name}")
        
        gpu_pool = ManagedClusterAgentPoolProfile(
            name="gpunodepool",
            count=0,  # Start with 0 nodes
            vm_size=self.gpu_vm_size,
            os_type="Linux",
            mode=AgentPoolMode.USER,
            type=AgentPoolType.VIRTUAL_MACHINE_SCALE_SETS,
            min_count=0,
            max_count=10,
            node_taints=["nvidia.com/gpu=true:NoSchedule"]
        )
        
        poller = self.aks_client.agent_pools.begin_create_or_update(
            self.resource_group,
            self.cluster_name,
            "gpunodepool",
            gpu_pool
        )
        poller.result()
        logger.info("GPU node pool created")
    
    def _get_or_create_service_principal(self) -> Dict:
        """Get or create service principal for AKS cluster"""
        # Note: AKS can create a service principal automatically if not provided
        # For production, it's recommended to create a dedicated service principal
        # This can be done via Azure CLI: `az ad sp create-for-rbac --name budgetguard-aks-sp`
        # Or via Azure Portal / Azure AD Graph API
        
        # For now, return placeholder - AKS will create one automatically
        # If you have a service principal, replace these with actual values
        logger.info("No service principal provided. AKS will create one automatically. "
                   "For production, consider creating a dedicated service principal.")
        
        return {
            'client_id': 'placeholder',  # AKS will create one if this is placeholder
            'client_secret': 'placeholder'
        }
    
    def _initialize_k8s_client(self, cluster: ManagedCluster):
        """Initialize Kubernetes client using AKS cluster credentials"""
        try:
            # Get AKS cluster admin credentials
            creds = self.aks_client.managed_clusters.list_cluster_admin_credentials(
                self.resource_group,
                self.cluster_name
            )
            
            if not creds.kubeconfigs or len(creds.kubeconfigs) == 0:
                raise Exception("No kubeconfig found in cluster credentials")
            
            # Extract kubeconfig from credentials
            kubeconfig = creds.kubeconfigs[0].value
            
            # Decode base64 kubeconfig
            kubeconfig_yaml = base64.b64decode(kubeconfig).decode('utf-8')
            
            # Parse kubeconfig YAML
            kubeconfig_dict = yaml.safe_load(kubeconfig_yaml)
            
            # Load kubeconfig into Kubernetes client
            config.load_kube_config_from_dict(kubeconfig_dict)
            
            # Initialize API clients
            self.k8s_client = client.ApiClient()
            self.k8s_apps_api = AppsV1Api()
            self.k8s_core_api = CoreV1Api()
            
            logger.info("Kubernetes client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}", exc_info=True)
            raise
    
    def _get_nim_image_uri(self, node_type: str) -> str:
        """Get container image URI for NIM node type"""
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
    
    def _create_k8s_deployment(self, instance_name: str, node_type: str,
                               image_uri: str, scale_to_zero: bool) -> V1Deployment:
        """Create Kubernetes deployment for NIM container with GPU resources"""
        namespace = "default"
        replicas = 0 if scale_to_zero else 1
        
        # Container with GPU resource requirements
        container = V1Container(
            name=instance_name,
            image=image_uri,
            ports=[V1ContainerPort(container_port=8000, protocol="TCP")],
            env=[
                V1EnvVar(name="NIM_MODEL", value=node_type)
            ],
            resources=V1ResourceRequirements(
                requests={
                    "nvidia.com/gpu": "1",  # Request 1 GPU
                    "cpu": "2",  # 2 CPU cores
                    "memory": "8Gi"  # 8 GB RAM
                },
                limits={
                    "nvidia.com/gpu": "1",  # Limit to 1 GPU
                    "cpu": "4",  # 4 CPU cores max
                    "memory": "16Gi"  # 16 GB RAM max
                }
            )
        )
        
        # Pod template with node selector for GPU nodes
        pod_template = V1PodTemplateSpec(
            metadata=V1ObjectMeta(
                labels={"app": instance_name}
            ),
            spec=V1PodSpec(
                containers=[container],
                node_selector={
                    "accelerator": "nvidia-gpu"  # Select GPU nodes
                },
                tolerations=[
                    {
                        "key": "nvidia.com/gpu",
                        "operator": "Equal",
                        "value": "true",
                        "effect": "NoSchedule"
                    }
                ]
            )
        )
        
        # Deployment
        deployment = V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=V1ObjectMeta(
                name=instance_name,
                namespace=namespace
            ),
            spec=V1DeploymentSpec(
                replicas=replicas,
                selector=V1LabelSelector(
                    match_labels={"app": instance_name}
                ),
                template=pod_template
            )
        )
        
        # Create deployment
        try:
            result = self.k8s_apps_api.create_namespaced_deployment(
                namespace=namespace,
                body=deployment
            )
            logger.info(f"Created Kubernetes deployment: {instance_name}")
            return result
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"Deployment {instance_name} already exists, updating...")
                result = self.k8s_apps_api.patch_namespaced_deployment(
                    name=instance_name,
                    namespace=namespace,
                    body=deployment
                )
                return result
            raise
    
    def _create_k8s_service(self, instance_name: str) -> V1Service:
        """Create Kubernetes LoadBalancer service for endpoint access"""
        namespace = "default"
        
        service = V1Service(
            api_version="v1",
            kind="Service",
            metadata=V1ObjectMeta(
                name=instance_name,
                namespace=namespace
            ),
            spec=V1ServiceSpec(
                type="LoadBalancer",
                selector={"app": instance_name},
                ports=[
                    V1ServicePort(
                        port=8000,
                        target_port=8000,
                        protocol="TCP"
                    )
                ]
            )
        )
        
        # Create service
        try:
            result = self.k8s_core_api.create_namespaced_service(
                namespace=namespace,
                body=service
            )
            logger.info(f"Created Kubernetes service: {instance_name}")
            return result
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"Service {instance_name} already exists")
                result = self.k8s_core_api.read_namespaced_service(
                    name=instance_name,
                    namespace=namespace
                )
                return result
            raise
    
    def _wait_for_deployment_ready(self, instance_name: str, timeout: int = 300):
        """Wait for Kubernetes deployment to be ready"""
        logger.info(f"Waiting for deployment {instance_name} to be ready...")
        start_time = time.time()
        namespace = "default"
        
        while time.time() - start_time < timeout:
            try:
                deployment = self.k8s_apps_api.read_namespaced_deployment(
                    name=instance_name,
                    namespace=namespace
                )
                
                if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
                    logger.info(f"Deployment {instance_name} is ready")
                    return
                
                time.sleep(5)
            except Exception as e:
                logger.warning(f"Error checking deployment status: {e}")
                time.sleep(5)
        
        logger.warning(f"Deployment {instance_name} did not become ready within {timeout} seconds")
    
    def _get_endpoint_url(self, instance_name: str) -> str:
        """Get endpoint URL from LoadBalancer service"""
        namespace = "default"
        max_retries = 30
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                service = self.k8s_core_api.read_namespaced_service(
                    name=instance_name,
                    namespace=namespace
                )
                
                if service.status.load_balancer and service.status.load_balancer.ingress:
                    ingress = service.status.load_balancer.ingress[0]
                    # Get IP or hostname from ingress
                    ip_or_hostname = ingress.ip or ingress.hostname
                    if ip_or_hostname:
                        return f"http://{ip_or_hostname}:8000"
                
                # LoadBalancer IP not ready yet, wait
                time.sleep(5)
                retry_count += 1
            except Exception as e:
                logger.warning(f"Error getting service endpoint: {e}")
                time.sleep(5)
                retry_count += 1
        
        # Fallback
        logger.warning(f"Could not get LoadBalancer IP for {instance_name}, using placeholder")
        return f"http://{instance_name}.{self.region}.cloudapp.azure.com:8000"
    
    def get_deployment_status(self, instance_name: str) -> Dict:
        """Get status of a deployed instance"""
        namespace = "default"
        try:
            deployment = self.k8s_apps_api.read_namespaced_deployment(
                name=instance_name,
                namespace=namespace
            )
            
            replicas = deployment.spec.replicas or 0
            ready_replicas = deployment.status.ready_replicas or 0
            
            endpoint = self._get_endpoint_url(instance_name)
            
            return {
                'status': 'running' if ready_replicas > 0 else 'stopped',
                'runningCount': ready_replicas,
                'desiredCount': replicas,
                'endpoint': endpoint
            }
        except ApiException as e:
            logger.error(f"Error getting deployment status: {e}", exc_info=True)
            return {'status': 'unknown', 'runningCount': 0, 'desiredCount': 0}
    
    def list_deployments(self) -> List[Dict]:
        """List all deployed NIM instances"""
        deployments = []
        namespace = "default"
        
        try:
            all_deployments = self.k8s_apps_api.list_namespaced_deployment(namespace=namespace)
            
            for deployment in all_deployments.items:
                if 'nim-' in deployment.metadata.name.lower():
                    status = self.get_deployment_status(deployment.metadata.name)
                    deployments.append({
                        'instance_name': deployment.metadata.name,
                        'status': status.get('status', 'unknown'),
                        'runningCount': status.get('runningCount', 0),
                        'endpoint': status.get('endpoint', ''),
                        'provider': 'azure',
                        'region': self.region,
                        'resource_group': self.resource_group,
                        'cluster': self.cluster_name
                    })
        except Exception as e:
            logger.error(f"Error listing deployments: {e}", exc_info=True)
        
        return deployments
    
    def start_deployment(self, instance_name: str) -> bool:
        """Start a stopped deployment by scaling to 1 replica"""
        namespace = "default"
        try:
            # Get current deployment
            deployment = self.k8s_apps_api.read_namespaced_deployment(
                name=instance_name,
                namespace=namespace
            )
            
            # Scale to 1 replica
            deployment.spec.replicas = 1
            
            self.k8s_apps_api.patch_namespaced_deployment_scale(
                name=instance_name,
                namespace=namespace,
                body={"spec": {"replicas": 1}}
            )
            
            logger.info(f"Started deployment: {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error starting deployment: {e}", exc_info=True)
            return False
    
    def stop_deployment(self, instance_name: str) -> bool:
        """Stop a deployed NIM instance by scaling to 0 replicas"""
        namespace = "default"
        try:
            # Scale to 0 replicas
            self.k8s_apps_api.patch_namespaced_deployment_scale(
                name=instance_name,
                namespace=namespace,
                body={"spec": {"replicas": 0}}
            )
            
            logger.info(f"Stopped deployment: {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error stopping deployment: {e}", exc_info=True)
            return False
    
    def delete_deployment(self, instance_name: str) -> bool:
        """Delete a deployed NIM instance"""
        namespace = "default"
        try:
            # Delete deployment
            self.k8s_apps_api.delete_namespaced_deployment(
                name=instance_name,
                namespace=namespace
            )
            
            # Delete service
            try:
                self.k8s_core_api.delete_namespaced_service(
                    name=instance_name,
                    namespace=namespace
                )
            except:
                pass  # Service may not exist
            
            logger.info(f"Deleted deployment: {instance_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting deployment: {e}", exc_info=True)
            return False
