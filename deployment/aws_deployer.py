"""
AWS Deployment Module for BudgetGuard TechOps

Handles deployment of NVIDIA NIM instances to AWS ECS on EC2 (GPU support required).

Note: GPU workloads require ECS on EC2 with GPU instances (p3, p4, g4dn, g5).
ECS Fargate and App Runner do not support GPUs.

See PLATFORM_SELECTION_GPU_REQUIREMENTS.md for details.
"""

import boto3
import logging
import time
import base64
import json
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class AWSDeployer:
    """Deploys NIM instances to AWS"""
    
    def __init__(self, access_key_id: str, secret_access_key: str, region: str = 'us-east-1',
                 gpu_instance_type: str = None):
        """
        Initialize AWS Deployer
        
        Args:
            access_key_id: AWS Access Key ID
            secret_access_key: AWS Secret Access Key
            region: AWS region (default: us-east-1)
            gpu_instance_type: GPU instance type (default: g4dn.xlarge for T4, 
                             or g5.xlarge for A10G - recommended for SD/FLUX models)
        """
        self.region = region
        self.session = boto3.Session(
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        
        # Initialize AWS clients
        self.ecs_client = self.session.client('ecs')
        self.ec2_client = self.session.client('ec2')
        self.ecr_client = self.session.client('ecr')
        self.logs_client = self.session.client('logs')
        self.autoscaling_client = self.session.client('autoscaling')
        self.iam_client = self.session.client('iam')
        
        # Default GPU instance type (can be overridden)
        # T4 (g4dn) is cost-effective but slower for SD/FLUX models
        # A10G (g5) is recommended for production SD/FLUX workloads (~2x faster)
        if gpu_instance_type:
            self.gpu_instance_type = gpu_instance_type
        else:
            # Default to g4dn.xlarge (T4) for cost-effectiveness
            # For production SD/FLUX, consider g5.xlarge (A10G)
            self.gpu_instance_type = 'g4dn.xlarge'  # 1 NVIDIA T4 GPU, 4 vCPU, 16 GB RAM
        # Alternative options:
        # - g5.xlarge: 1x A10G (24GB VRAM, ~2x faster than T4 for SD models) - RECOMMENDED for production
        # - g5.2xlarge: 1x A10G (24GB VRAM, more CPU/memory)
        # - p3.2xlarge: 1x V100 (16GB VRAM, older but still capable)
        # - p4d.24xlarge: 8x A100 (40GB VRAM each, best for production)
        
        logger.info(f"AWS Deployer initialized for region: {region} with GPU instance type: {self.gpu_instance_type}")
    
    def deploy_nim_instance(self, node_type: str, instance_name: str = None, 
                           scale_to_zero: bool = True) -> Dict:
        """
        Deploy a NIM instance to AWS
        
        Args:
            node_type: Type of NIM node (e.g., "FLUX Dev", "FLUX Canny")
            instance_name: Optional custom instance name
            
        Returns:
            Dictionary with deployment info including endpoint URL
        """
        if instance_name is None:
            instance_name = f"nim-{node_type.lower().replace(' ', '-')}-{int(time.time())}"
        
        logger.info(f"Deploying {node_type} as {instance_name} to AWS {self.region}")
        
        try:
            # For Phase 2, we'll use ECS (Elastic Container Service) as it's simpler than EKS
            # This will deploy NIM as a containerized service
            
            # Step 1: Get or create ECS cluster with EC2 capacity
            cluster_name = "budgetguard-nim-cluster"
            cluster_arn = self._get_or_create_cluster(cluster_name)
            
            # Step 2: Ensure EC2 instances are available in cluster (GPU instances)
            self._ensure_ec2_capacity(cluster_name)
            
            # Step 3: Get or create ECR repository for NIM images
            # Note: In production, we'd pull from NVIDIA's container registry
            # For now, we'll assume NVIDIA provides public ECR images or we use their registry
            repo_name = self._get_nim_repository_name(node_type)
            
            # Step 4: Create task definition for NIM with GPU support
            task_def = self._create_task_definition(node_type, instance_name)
            
            # Step 5: Create ECS service with EC2 launch type
            service = self._create_ecs_service(cluster_arn, task_def, instance_name, scale_to_zero)
            
            # Step 6: Get endpoint URL
            endpoint_url = self._get_endpoint_url(service, instance_name)
            
            deployment_info = {
                "node_type": node_type,
                "instance_name": instance_name,
                "provider": "aws",
                "region": self.region,
                "endpoint": endpoint_url,
                "cluster": cluster_name,
                "service": service['serviceName'],
                "deployed_at": datetime.utcnow().isoformat() + "Z",
                "status": "running"
            }
            
            logger.info(f"Successfully deployed {node_type} to AWS. Endpoint: {endpoint_url}")
            return deployment_info
            
        except Exception as e:
            logger.error(f"Failed to deploy {node_type} to AWS: {e}", exc_info=True)
            raise
    
    def _get_or_create_cluster(self, cluster_name: str) -> str:
        """Get existing ECS cluster or create new one"""
        try:
            response = self.ecs_client.describe_clusters(clusters=[cluster_name])
            if response['clusters'] and response['clusters'][0]['status'] == 'ACTIVE':
                logger.info(f"Using existing cluster: {cluster_name}")
                return response['clusters'][0]['clusterArn']
        except Exception:
            pass
        
        # Create new cluster (for EC2 launch type)
        logger.info(f"Creating new ECS cluster: {cluster_name}")
        response = self.ecs_client.create_cluster(
            clusterName=cluster_name,
            capacityProviders=['EC2'],  # Use EC2 capacity provider
            defaultCapacityProviderStrategy=[
                {
                    'capacityProvider': 'EC2',
                    'weight': 1,
                    'base': 0
                }
            ]
        )
        return response['cluster']['clusterArn']
    
    def _ensure_ec2_capacity(self, cluster_name: str):
        """Ensure EC2 instances with GPU support are available in the cluster"""
        try:
            # Check if Auto Scaling Group already exists
            asg_name = f"budgetguard-nim-asg-{cluster_name.replace('_', '-')}"
            
            try:
                self.autoscaling_client.describe_auto_scaling_groups(
                    AutoScalingGroupNames=[asg_name]
                )
                logger.info(f"Auto Scaling Group already exists: {asg_name}")
                return
            except:
                pass  # ASG doesn't exist, create it
            
            logger.info(f"Setting up EC2 capacity with GPU instances for cluster: {cluster_name}")
            
            # Get VPC and subnets
            vpc_id, subnet_ids, security_group_id = self._get_or_create_network_resources()
            
            # Create IAM role for ECS instances
            instance_role_arn = self._get_or_create_ecs_instance_role()
            
            # Create Launch Template with GPU instance
            launch_template_name = f"budgetguard-nim-launch-template-{int(time.time())}"
            launch_template_id = self._create_launch_template(
                launch_template_name, instance_role_arn, security_group_id
            )
            
            # Create Auto Scaling Group
            self._create_auto_scaling_group(
                asg_name, cluster_name, launch_template_id, subnet_ids
            )
            
            logger.info(f"EC2 capacity setup complete. Auto Scaling Group: {asg_name}")
            
        except Exception as e:
            logger.error(f"Error setting up EC2 capacity: {e}", exc_info=True)
            raise
    
    def _get_nim_repository_name(self, node_type: str) -> str:
        """Get ECR repository name for NIM node type"""
        # Map node types to NVIDIA NIM container images
        # These would be from NVIDIA's registry or ECR
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
    
    def _create_task_definition(self, node_type: str, instance_name: str) -> str:
        """Create ECS task definition for NIM instance"""
        image_uri = self._get_nim_repository_name(node_type)
        
        task_def_name = f"budgetguard-nim-{node_type.lower().replace(' ', '-')}"
        
        # Check if task definition already exists
        try:
            response = self.ecs_client.describe_task_definition(taskDefinition=task_def_name)
            logger.info(f"Using existing task definition: {task_def_name}")
            return response['taskDefinition']['taskDefinitionArn']
        except Exception:
            pass
        
        # Create new task definition
        logger.info(f"Creating task definition: {task_def_name}")
        
        # NIM containers require GPU access - use EC2 launch type
        # For g4dn.xlarge: 4 vCPU, 16 GB RAM, 1 NVIDIA T4 GPU
        task_def = {
            'family': task_def_name,
            'networkMode': 'bridge',  # EC2 launch type can use bridge mode
            'requiresCompatibilities': ['EC2'],  # GPU requires EC2 launch type
            'cpu': '4096',  # 4 vCPU
            'memory': '8192',  # 8 GB RAM (16 GB available, but limit to 8 GB for task)
            'containerDefinitions': [
                {
                    'name': instance_name,
                    'image': image_uri,
                    'essential': True,
                    'portMappings': [
                        {
                            'containerPort': 8000,  # Typical NIM API port
                            'hostPort': 8000,  # Map to host port
                            'protocol': 'tcp'
                        }
                    ],
                    'environment': [
                        {'name': 'NIM_MODEL', 'value': node_type},
                    ],
                    'resourceRequirements': [
                        {'type': 'GPU', 'value': '1'}  # Request 1 GPU
                    ],
                    'logConfiguration': {
                        'logDriver': 'awslogs',
                        'options': {
                            'awslogs-group': f'/ecs/{task_def_name}',
                            'awslogs-region': self.region,
                            'awslogs-stream-prefix': 'ecs'
                        }
                    }
                }
            ]
        }
        
        response = self.ecs_client.register_task_definition(**task_def)
        
        # Create CloudWatch log group
        try:
            self.logs_client.create_log_group(logGroupName=f'/ecs/{task_def_name}')
        except:
            pass  # Log group may already exist
        
        return response['taskDefinition']['taskDefinitionArn']
    
    def _create_ecs_service(self, cluster_arn: str, task_def_arn: str, service_name: str, scale_to_zero: bool = True) -> Dict:
        """Create ECS service with EC2 launch type"""
        logger.info(f"Creating ECS service: {service_name} with EC2 launch type")
        
        # Set desired count based on scale_to_zero setting
        # For EC2, we can set to 0 and start manually via start_deployment
        desired_count = 0 if scale_to_zero else 1
        
        service_config = {
            'cluster': cluster_arn.split('/')[-1],
            'serviceName': service_name,
            'taskDefinition': task_def_arn.split('/')[-1],
            'desiredCount': desired_count,
            'launchType': 'EC2',  # Use EC2 for GPU support
            'placementConstraints': [
                {
                    'type': 'memberOf',
                    'expression': 'attribute:ecs.instance-type =~ g4dn.*'  # Prefer GPU instances
                }
            ],
            'placementStrategy': [
                {
                    'type': 'spread',
                    'field': 'instanceId'  # Spread tasks across instances
                }
            ]
        }
        
        try:
            response = self.ecs_client.create_service(**service_config)
            logger.info(f"ECS service created: {service_name}")
            return response['service']
        except Exception as e:
            if 'already exists' in str(e).lower():
                # Service already exists, get it
                response = self.ecs_client.describe_services(
                    cluster=cluster_arn.split('/')[-1],
                    services=[service_name]
                )
                return response['services'][0]
            raise
    
    def _get_or_create_network_resources(self) -> tuple:
        """Get or create VPC, subnets, and security group"""
        # Get default VPC
        vpcs = self.ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
        
        if vpcs['Vpcs']:
            vpc_id = vpcs['Vpcs'][0]['VpcId']
        else:
            # Create VPC if needed (simplified)
            logger.warning("No default VPC found. Using first available VPC.")
            all_vpcs = self.ec2_client.describe_vpcs()
            if all_vpcs['Vpcs']:
                vpc_id = all_vpcs['Vpcs'][0]['VpcId']
            else:
                raise Exception("No VPC available. Please create a VPC first.")
        
        # Get subnets
        subnets = self.ec2_client.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        subnet_ids = [s['SubnetId'] for s in subnets['Subnets'][:2]]  # Use first 2 subnets
        
        # Create security group for NIM
        sg_name = "budgetguard-nim-sg"
        try:
            sgs = self.ec2_client.describe_security_groups(
                Filters=[{'Name': 'group-name', 'Values': [sg_name]}]
            )
            if sgs['SecurityGroups']:
                sg_id = sgs['SecurityGroups'][0]['GroupId']
            else:
                raise Exception("Security group not found")
        except:
            # Create security group
            sg = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description='Security group for BudgetGuard NIM instances',
                VpcId=vpc_id
            )
            sg_id = sg['GroupId']
            
            # Allow inbound traffic on port 8000 (NIM API)
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 8000,
                        'ToPort': 8000,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # Allow from anywhere (restrict in production)
                    }
                ]
            )
        
        return vpc_id, subnet_ids, sg_id
    
    def _get_or_create_ecs_instance_role(self) -> str:
        """Get or create IAM role for ECS EC2 instances"""
        role_name = "budgetguard-ecs-instance-role"
        
        try:
            # Check if role exists
            response = self.iam_client.get_role(RoleName=role_name)
            logger.info(f"Using existing IAM role: {role_name}")
            return response['Role']['Arn']
        except:
            pass
        
        # Create role
        logger.info(f"Creating IAM role: {role_name}")
        
        # Trust policy for EC2 instances
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        # Create role
        role = self.iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="IAM role for BudgetGuard ECS EC2 instances"
        )
        
        # Attach AWS managed policy for ECS instances
        self.iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
        )
        
        # Create instance profile
        try:
            profile_name = role_name
            self.iam_client.create_instance_profile(InstanceProfileName=profile_name)
            self.iam_client.add_role_to_instance_profile(
                InstanceProfileName=profile_name,
                RoleName=role_name
            )
        except:
            pass  # Profile may already exist
        
        logger.info(f"IAM role created: {role_name}")
        return role['Role']['Arn']
    
    def _create_launch_template(self, template_name: str, instance_role_arn: str, security_group_id: str) -> str:
        """Create EC2 Launch Template with GPU instance configuration"""
        logger.info(f"Creating Launch Template: {template_name} with GPU instance type: {self.gpu_instance_type}")
        
        # Get instance profile name from role ARN
        instance_profile_name = instance_role_arn.split('/')[-1]
        
        # User data script to configure ECS cluster registration
        # ECS-optimized AMIs already have ECS agent installed
        cluster_name = "budgetguard-nim-cluster"
        user_data = f"""#!/bin/bash
# Configure ECS cluster
echo ECS_CLUSTER={cluster_name} >> /etc/ecs/ecs.config

# For GPU instances, ensure NVIDIA drivers and nvidia-docker are available
# ECS GPU-optimized AMI should have these pre-installed
"""
        
        # Get ECS-optimized AMI with GPU support
        # For g4dn instances, use ECS-optimized AMI with GPU support
        try:
            ssm_client = self.session.client('ssm')
            ami_param = '/aws/service/ecs/optimized-ami/amazon-linux-2/gpu/recommended'
            ami_info = ssm_client.get_parameter(Name=ami_param)
            # SSM parameter returns JSON with image_id field
            ami_data = json.loads(ami_info['Parameter']['Value'])
            ami_id = ami_data.get('image_id')
            if not ami_id:
                # Try alternative format
                ami_id = ami_info['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Could not get ECS GPU AMI from SSM: {e}. You may need to specify AMI manually.")
            # Fallback: Use a known GPU AMI or let user specify
            ami_id = None  # Will need to be specified or use default ECS-optimized AMI
        
        launch_template_data = {
            'InstanceType': self.gpu_instance_type,
            'IamInstanceProfile': {
                'Name': instance_profile_name
            },
            'SecurityGroupIds': [security_group_id],
            'UserData': base64.b64encode(user_data.encode('utf-8')).decode('utf-8') if user_data else None,
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': 'BudgetGuard-ECS-GPU'},
                        {'Key': 'BudgetGuard', 'Value': 'true'},
                        {'Key': 'Cluster', 'Value': 'budgetguard-nim-cluster'}
                    ]
                }
            ]
        }
        
        # Add AMI ID if available
        if ami_id:
            launch_template_data['ImageId'] = ami_id
        
        try:
            response = self.ec2_client.create_launch_template(
                LaunchTemplateName=template_name,
                LaunchTemplateData=launch_template_data
            )
            logger.info(f"Launch Template created: {template_name}")
            return response['LaunchTemplate']['LaunchTemplateId']
        except Exception as e:
            # Template may already exist
            if 'already exists' in str(e).lower():
                response = self.ec2_client.describe_launch_templates(
                    LaunchTemplateNames=[template_name]
                )
                return response['LaunchTemplates'][0]['LaunchTemplateId']
            raise
    
    def _create_auto_scaling_group(self, asg_name: str, cluster_name: str, launch_template_id: str, subnet_ids: List[str]):
        """Create Auto Scaling Group for ECS cluster with GPU instances"""
        logger.info(f"Creating Auto Scaling Group: {asg_name}")
        
        # Create ASG with minimum 0 (scale-to-zero), desired 1, max 10
        # This allows manual control via start/stop
        asg_config = {
            'AutoScalingGroupName': asg_name,
            'LaunchTemplate': {
                'LaunchTemplateId': launch_template_id,
                'Version': '$Latest'
            },
            'MinSize': 0,  # Can scale to zero
            'MaxSize': 10,  # Max 10 GPU instances
            'DesiredCapacity': 1,  # Start with 1 instance
            'VPCZoneIdentifier': ','.join(subnet_ids),
            'HealthCheckType': 'EC2',
            'HealthCheckGracePeriod': 300,
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'BudgetGuard-ECS-ASG',
                    'PropagateAtLaunch': True
                },
                {
                    'Key': 'BudgetGuard',
                    'Value': 'true',
                    'PropagateAtLaunch': True
                },
                {
                    'Key': 'Cluster',
                    'Value': cluster_name,
                    'PropagateAtLaunch': True
                }
            ]
        }
        
        try:
            self.autoscaling_client.create_auto_scaling_group(**asg_config)
            logger.info(f"Auto Scaling Group created: {asg_name}")
        except Exception as e:
            if 'already exists' in str(e).lower():
                logger.info(f"Auto Scaling Group already exists: {asg_name}")
            else:
                raise
        
        # Wait for instances to register with ECS cluster
        logger.info("Waiting for EC2 instances to register with ECS cluster...")
        time.sleep(30)  # Give instances time to start and register
    
    def _get_endpoint_url(self, service: Dict, instance_name: str) -> str:
        """Get endpoint URL for deployed NIM instance (EC2 launch type)"""
        # Get task details
        cluster_name = service['clusterArn'].split('/')[-1]
        service_name = service['serviceName']
        
        # Get running tasks
        tasks = self.ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
        
        if not tasks['taskArns']:
            # Wait a bit for task to start
            time.sleep(10)
            tasks = self.ecs_client.list_tasks(cluster=cluster_name, serviceName=service_name)
        
        if tasks['taskArns']:
            task_details = self.ecs_client.describe_tasks(
                cluster=cluster_name,
                tasks=tasks['taskArns']
            )
            
            if task_details['tasks']:
                task = task_details['tasks'][0]
                
                # For EC2 launch type with bridge network mode
                # Get the EC2 instance ID from the task
                container_instance_arn = task.get('containerInstanceArn')
                if container_instance_arn:
                    # Get container instance details
                    container_instances = self.ecs_client.describe_container_instances(
                        cluster=cluster_name,
                        containerInstances=[container_instance_arn]
                    )
                    if container_instances['containerInstances']:
                        ec2_instance_id = container_instances['containerInstances'][0]['ec2InstanceId']
                        
                        # Get EC2 instance public IP
                        instances = self.ec2_client.describe_instances(InstanceIds=[ec2_instance_id])
                        if instances['Reservations'] and instances['Reservations'][0]['Instances']:
                            instance = instances['Reservations'][0]['Instances'][0]
                            public_ip = instance.get('PublicIpAddress')
                            if public_ip:
                                return f"http://{public_ip}:8000"
        
        # Fallback: Return a placeholder endpoint
        # In production, this would use Application Load Balancer or similar
        return f"https://nim-{instance_name}.{self.region}.aws.nim.api.nvidia.com"
    
    def get_deployment_status(self, instance_name: str) -> Dict:
        """Get status of a deployed instance"""
        try:
            # Find service by instance name
            clusters = self.ecs_client.list_clusters()
            for cluster_arn in clusters['clusterArns']:
                cluster_name = cluster_arn.split('/')[-1]
                services = self.ecs_client.list_services(cluster=cluster_name)
                for service_arn in services['serviceArns']:
                    service_name = service_arn.split('/')[-1]
                    if instance_name in service_name:
                        service_details = self.ecs_client.describe_services(
                            cluster=cluster_name,
                            services=[service_name]
                        )
                        if service_details['services']:
                            service = service_details['services'][0]
                            return {
                                'status': service['status'],
                                'runningCount': service['runningCount'],
                                'desiredCount': service['desiredCount'],
                                'endpoint': self._get_endpoint_url(service, instance_name)
                            }
        except Exception as e:
            logger.error(f"Error getting deployment status: {e}", exc_info=True)
        
        return {'status': 'unknown', 'runningCount': 0, 'desiredCount': 0}
    
    def list_deployments(self) -> List[Dict]:
        """List all deployed NIM instances"""
        deployments = []
        
        try:
            clusters = self.ecs_client.list_clusters()
            for cluster_arn in clusters['clusterArns']:
                cluster_name = cluster_arn.split('/')[-1]
                services = self.ecs_client.list_services(cluster=cluster_name)
                
                for service_arn in services['serviceArns']:
                    service_name = service_arn.split('/')[-1]
                    if 'budgetguard' in service_name.lower() or 'nim' in service_name.lower():
                        service_details = self.ecs_client.describe_services(
                            cluster=cluster_name,
                            services=[service_name]
                        )
                        if service_details['services']:
                            service = service_details['services'][0]
                            endpoint = self._get_endpoint_url(service, service_name)
                            deployments.append({
                                'instance_name': service_name,
                                'cluster': cluster_name,
                                'status': service['status'],
                                'runningCount': service['runningCount'],
                                'endpoint': endpoint,
                                'provider': 'aws',
                                'region': self.region
                            })
        except Exception as e:
            logger.error(f"Error listing deployments: {e}", exc_info=True)
        
        return deployments
    
    def start_deployment(self, instance_name: str) -> bool:
        """Start a stopped deployment (scale from 0 to 1)"""
        try:
            clusters = self.ecs_client.list_clusters()
            for cluster_arn in clusters['clusterArns']:
                cluster_name = cluster_arn.split('/')[-1]
                services = self.ecs_client.list_services(cluster=cluster_name)
                for service_arn in services['serviceArns']:
                    service_name = service_arn.split('/')[-1]
                    if instance_name in service_name:
                        self.ecs_client.update_service(
                            cluster=cluster_name,
                            service=service_name,
                            desiredCount=1
                        )
                        logger.info(f"Started deployment: {instance_name}")
                        return True
        except Exception as e:
            logger.error(f"Error starting deployment: {e}", exc_info=True)
        
        return False
    
    def stop_deployment(self, instance_name: str) -> bool:
        """Stop a deployed NIM instance"""
        try:
            clusters = self.ecs_client.list_clusters()
            for cluster_arn in clusters['clusterArns']:
                cluster_name = cluster_arn.split('/')[-1]
                services = self.ecs_client.list_services(cluster=cluster_name)
                for service_arn in services['serviceArns']:
                    service_name = service_arn.split('/')[-1]
                    if instance_name in service_name:
                        self.ecs_client.update_service(
                            cluster=cluster_name,
                            service=service_name,
                            desiredCount=0
                        )
                        logger.info(f"Stopped deployment: {instance_name}")
                        return True
        except Exception as e:
            logger.error(f"Error stopping deployment: {e}", exc_info=True)
        
        return False

