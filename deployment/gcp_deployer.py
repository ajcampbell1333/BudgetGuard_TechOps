"""
GCP Deployment Module for BudgetGuard TechOps

Handles deployment of NVIDIA NIM instances to GCP GKE (Google Kubernetes Engine) with GPU support.

Note: GPU workloads require GKE with GPU node pools (T4, A10G, A100).
Cloud Run does not support GPUs.

Phase 4: Implemented GKE with GPU node pools from the start.

See PLATFORM_SELECTION_GPU_REQUIREMENTS.md for details.
"""

import logging
import time
import base64
import yaml
from typing import Dict, List, Optional
from datetime import datetime

try:
    from google.cloud import container_v1
    from google.cloud.container_v1.types import (
        Cluster, NodePool, NodeConfig, AcceleratorConfig,
        GcePersistentDiskCsiDriverConfig, NetworkConfig, MasterAuth,
        AddonsConfig, HttpLoadBalancing, NetworkPolicyConfig
    )
    from google.api_core import exceptions as gcp_exceptions
    from google.auth import default
    from google.auth.transport.requests import Request
    from kubernetes import client, config
    from kubernetes.client import V1Deployment, V1Service, V1ObjectMeta, V1PodSpec, \
        V1Container, V1ContainerPort, V1ResourceRequirements, V1ServicePort, \
        V1ServiceSpec, V1DeploymentSpec, V1PodTemplateSpec, V1LabelSelector, \
        V1EnvVar, AppsV1Api, CoreV1Api
    from kubernetes.client.rest import ApiException
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"GCP/Kubernetes SDK not installed. Install with: pip install google-cloud-container kubernetes")
    raise

logger = logging.getLogger(__name__)


class GCPDeployer:
    """Deploys NIM instances to GCP GKE (Google Kubernetes Engine) with GPU support"""
    
    def __init__(self, project_id: str, credentials_path: str = None,
                 region: str = 'us-central1', zone: str = None,
                 gpu_machine_type: str = None, gpu_type: str = None):
        """
        Initialize GCP Deployer for GKE
        
        Args:
            project_id: GCP Project ID
            credentials_path: Path to GCP service account JSON file (optional, uses ADC if not provided)
            region: GCP region (default: us-central1)
            zone: GCP zone (optional, uses region default if not provided)
            gpu_machine_type: GPU machine type (default: n1-standard-4 for T4,
                            or a2-highgpu-1g for A10G - recommended for SD/FLUX models)
            gpu_type: GPU type (default: nvidia-tesla-t4, or nvidia-a10 for A10G,
                     or nvidia-a100 for A100)
        """
        self.project_id = project_id
        self.region = region
        self.zone = zone or f"{region}-a"  # Default to first zone in region
        self.cluster_name = "budgetguard-nim-gke"
        
        # Default GPU machine type and GPU type (can be overridden)
        # T4: n1-standard-4 + nvidia-tesla-t4 (cost-effective)
        # A10G: a2-highgpu-1g + nvidia-a10 (recommended for SD/FLUX)
        # A100: a2-highgpu-4g + nvidia-a100 (fastest)
        if gpu_machine_type and gpu_type:
            self.gpu_machine_type = gpu_machine_type
            self.gpu_type = gpu_type
        else:
            # Default to T4 for cost-effectiveness
            # For production SD/FLUX, consider A10G (a2-highgpu-1g + nvidia-a10)
            self.gpu_machine_type = 'n1-standard-4'  # 4 vCPU, 15 GB RAM
            self.gpu_type = 'nvidia-tesla-t4'  # 1x NVIDIA T4 GPU
        
        # Initialize GCP Container client
        if credentials_path:
            from google.oauth2 import service_account
            self._credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.container_client = container_v1.ClusterManagerClient(credentials=self._credentials)
        else:
            # Use Application Default Credentials (ADC)
            self._credentials, _ = default()
            self.container_client = container_v1.ClusterManagerClient(credentials=self._credentials)
        
        # Kubernetes client (will be initialized after cluster is created)
        self.k8s_client = None
        self.k8s_apps_api = None
        self.k8s_core_api = None
        
        logger.info(f"GCP GKE Deployer initialized for project: {project_id}, region: {region}, "
                   f"GPU machine type: {self.gpu_machine_type}, GPU type: {self.gpu_type}")
    
    def deploy_nim_instance(self, node_type: str, instance_name: str = None,
                           scale_to_zero: bool = True, gpu_tier: str = None) -> Dict:
        """
        Deploy a NIM instance to GCP GKE
        
        Args:
            node_type: Type of NIM node (e.g., "FLUX Dev", "FLUX Canny")
            instance_name: Optional custom instance name
            scale_to_zero: If True, deployment starts with 0 replicas (stopped)
            gpu_tier: GPU tier (t4, a10g, a100) - used for naming, actual GPU depends on machine type
            
        Returns:
            Dictionary with deployment info including endpoint URL
        """
        if instance_name is None:
            gpu_suffix = f"-{gpu_tier}" if gpu_tier else ""
            instance_name = f"nim-{node_type.lower().replace(' ', '-')}{gpu_suffix}-{int(time.time())}"
        
        logger.info(f"Deploying {node_type} as {instance_name} to GCP GKE {self.region}")
        
        try:
            # Step 1: Get or create GKE cluster with GPU node pool
            cluster = self._get_or_create_gke_cluster()
            
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
                "provider": "gcp",
                "region": self.region,
                "zone": self.zone,
                "project_id": self.project_id,
                "cluster": self.cluster_name,
                "endpoint": endpoint_url,
                "deployed_at": datetime.utcnow().isoformat() + "Z",
                "status": "stopped" if scale_to_zero else "running",
                "gpu_machine_type": self.gpu_machine_type,
                "gpu_type": self.gpu_type,
                "gpu_tier": gpu_tier
            }
            
            logger.info(f"Successfully deployed {node_type} to GCP GKE. Endpoint: {endpoint_url}")
            return deployment_info
            
        except Exception as e:
            logger.error(f"Failed to deploy {node_type} to GCP GKE: {e}", exc_info=True)
            raise
    
    def _get_or_create_gke_cluster(self) -> Cluster:
        """Get existing GKE cluster or create new one with GPU node pool"""
        parent = f"projects/{self.project_id}/locations/{self.zone}"
        
        try:
            # Check if cluster exists
            try:
                cluster = self.container_client.get_cluster(
                    name=f"{parent}/clusters/{self.cluster_name}"
                )
                logger.info(f"Using existing GKE cluster: {self.cluster_name}")
                
                # Check if GPU node pool exists
                if not self._has_gpu_node_pool(cluster):
                    logger.info("GPU node pool not found, creating...")
                    self._create_gpu_node_pool(cluster)
                
                return cluster
            except gcp_exceptions.NotFound:
                pass  # Cluster doesn't exist, create it
        
        # Create new GKE cluster with GPU node pool
        logger.info(f"Creating new GKE cluster: {self.cluster_name} with GPU node pool")
        
        # Create cluster configuration
        cluster = Cluster(
            name=self.cluster_name,
            location=self.zone,
            initial_node_count=1,  # System node pool (CPU-only)
            node_config=NodeConfig(
                machine_type="e2-standard-2",  # 2 vCPU, 8 GB RAM (CPU-only system pool)
                disk_size_gb=50,
                oauth_scopes=[
                    "https://www.googleapis.com/auth/cloud-platform"
                ]
            ),
            master_auth=MasterAuth(
                username="admin",
                # Password will be auto-generated, or use client certificate
            ),
            network_config=NetworkConfig(
                enable_intranode_visibility=True
            ),
            addons_config=AddonsConfig(
                http_load_balancing=HttpLoadBalancing(disabled=False),
                network_policy_config=NetworkPolicyConfig(disabled=True)
            ),
            # Enable GCE persistent disk CSI driver for storage
            gce_persistent_disk_csi_driver_config=GcePersistentDiskCsiDriverConfig(enabled=True)
        )
        
        # Create cluster (this takes 10-15 minutes)
        logger.info(f"Creating GKE cluster (this may take 10-15 minutes)...")
        operation = self.container_client.create_cluster(
            parent=parent,
            cluster=cluster
        )
        
        # Wait for cluster creation to complete
        self._wait_for_operation(operation.name)
        
        # Get the created cluster
        cluster = self.container_client.get_cluster(
            name=f"{parent}/clusters/{self.cluster_name}"
        )
        
        logger.info(f"GKE cluster {self.cluster_name} created successfully")
        
        # Create GPU node pool
        self._create_gpu_node_pool(cluster)
        
        return cluster
    
    def _has_gpu_node_pool(self, cluster: Cluster) -> bool:
        """Check if cluster has a GPU node pool"""
        parent = f"projects/{self.project_id}/locations/{cluster.location}/clusters/{cluster.name}"
        
        try:
            node_pools = self.container_client.list_node_pools(parent=parent)
            for pool in node_pools.node_pools:
                if pool.config.accelerators:
                    return True
        except Exception as e:
            logger.warning(f"Error checking node pools: {e}")
        
        return False
    
    def _create_gpu_node_pool(self, cluster: Cluster):
        """Create GPU node pool in existing cluster"""
        logger.info(f"Creating GPU node pool in cluster: {self.cluster_name}")
        
        parent = f"projects/{self.project_id}/locations/{cluster.location}/clusters/{cluster.name}"
        
        node_pool = NodePool(
            name="gpu-node-pool",
            initial_node_count=0,  # Start with 0 nodes (scale-to-zero)
            autoscaling={
                "min_node_count": 0,  # Allow scale-to-zero
                "max_node_count": 10  # Max nodes for manual scaling
            },
            config=NodeConfig(
                machine_type=self.gpu_machine_type,
                disk_size_gb=100,
                disk_type="pd-standard",
                accelerators=[
                    AcceleratorConfig(
                        accelerator_count=1,
                        accelerator_type=self.gpu_type
                    )
                ],
                oauth_scopes=[
                    "https://www.googleapis.com/auth/cloud-platform"
                ],
                # Taint GPU nodes to require GPU workloads
                taints=[
                    {
                        "key": "nvidia.com/gpu",
                        "value": "true",
                        "effect": "NO_SCHEDULE"
                    }
                ],
                labels={
                    "accelerator": "nvidia-gpu"
                }
            ),
            management={
                "auto_repair": True,
                "auto_upgrade": True
            }
        )
        
        operation = self.container_client.create_node_pool(
            parent=parent,
            node_pool=node_pool
        )
        
        # Wait for node pool creation
        self._wait_for_operation(operation.name)
        logger.info("GPU node pool created")
    
    def _wait_for_operation(self, operation_name: str, timeout: int = 1800):
        """Wait for GKE operation to complete"""
        logger.info(f"Waiting for operation: {operation_name}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                operation = self.container_client.get_operation(name=operation_name)
                if operation.status == container_v1.Operation.Status.DONE:
                    if operation.error:
                        raise Exception(f"Operation failed: {operation.error}")
                    logger.info("Operation completed successfully")
                    return
                time.sleep(10)
            except Exception as e:
                logger.warning(f"Error checking operation status: {e}")
                time.sleep(10)
        
        raise TimeoutError(f"Operation {operation_name} did not complete within {timeout} seconds")
    
    def _initialize_k8s_client(self, cluster: Cluster):
        """Initialize Kubernetes client using GKE cluster credentials"""
        try:
            # Get GKE cluster credentials
            parent = f"projects/{self.project_id}/locations/{cluster.location}/clusters/{cluster.name}"
            creds = self.container_client.get_cluster(name=parent)
            
            # Extract kubeconfig from cluster endpoint
            # GKE provides cluster endpoint and CA certificate
            cluster_endpoint = creds.endpoint
            cluster_ca = creds.master_auth.cluster_ca_certificate
            
            # For GKE, we need to use the cluster's credentials
            # The simplest approach is to use the cluster's client certificate or token
            # For service account auth, we'll use the token from the credentials
            from google.auth import default
            from google.auth.transport.requests import Request
            
            # Get default credentials (service account or user credentials)
            # If credentials_path was provided, use service account from file
            if hasattr(self, '_credentials') and self._credentials:
                credentials = self._credentials
            else:
                credentials, _ = default()
            
            # Refresh credentials to get access token
            if not credentials.valid:
                credentials.refresh(Request())
            
            access_token = credentials.token
            
            # Create kubeconfig dict with token authentication
            kubeconfig_dict = {
                "apiVersion": "v1",
                "clusters": [{
                    "cluster": {
                        "certificate-authority-data": cluster_ca,
                        "server": f"https://{cluster_endpoint}"
                    },
                    "name": "gke-cluster"
                }],
                "contexts": [{
                    "context": {
                        "cluster": "gke-cluster",
                        "user": "gke-user"
                    },
                    "name": "gke-context"
                }],
                "current-context": "gke-context",
                "kind": "Config",
                "users": [{
                    "name": "gke-user",
                    "user": {
                        "token": access_token
                    }
                }]
            }
            
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
        return f"http://{instance_name}.{self.region}.cloudapp.gcp.com:8000"
    
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
                        'provider': 'gcp',
                        'region': self.region,
                        'zone': self.zone,
                        'project_id': self.project_id,
                        'cluster': self.cluster_name
                    })
        except Exception as e:
            logger.error(f"Error listing deployments: {e}", exc_info=True)
        
        return deployments
    
    def start_deployment(self, instance_name: str) -> bool:
        """Start a stopped deployment by scaling to 1 replica"""
        namespace = "default"
        try:
            # Scale to 1 replica
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

