"""
Cost Estimation Module for BudgetGuard TechOps

Estimates deployment and running costs for NIM instances across cloud providers
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CostEstimator:
    """Estimates costs for NIM deployments"""
    
    # Pricing data (as of 2024, approximate - update with actual API calls)
    # All prices in USD
    
    # AWS ECS Fargate pricing (per hour)
    AWS_FARGATE_CPU_PRICE = 0.00001156  # per vCPU-second
    AWS_FARGATE_MEMORY_PRICE = 0.00000127  # per GB-second
    
    # Typical NIM node resource requirements
    NIM_RESOURCE_REQUIREMENTS = {
        "FLUX Dev": {"cpu": 4, "memory": 16, "gpu": True},  # 4 vCPU, 16GB RAM
        "FLUX Canny": {"cpu": 4, "memory": 16, "gpu": True},
        "FLUX Depth": {"cpu": 4, "memory": 16, "gpu": True},
        "FLUX Kontext": {"cpu": 4, "memory": 16, "gpu": True},
        "SDXL": {"cpu": 2, "memory": 8, "gpu": True},
        "Llama 3": {"cpu": 4, "memory": 16, "gpu": False},
        "Mixtral": {"cpu": 4, "memory": 16, "gpu": False},
        "Phi-3": {"cpu": 2, "memory": 8, "gpu": False}
    }
    
    # AWS Fargate GPU pricing (if available)
    AWS_FARGATE_GPU_PRICE = 0.000528  # per GPU-second (approximate)
    
    # Azure Container Instances pricing (per hour)
    AZURE_ACI_CPU_PRICE = 0.000012  # per vCPU-second
    AZURE_ACI_MEMORY_PRICE = 0.0000015  # per GB-second
    AZURE_ACI_GPU_PRICE = 0.0005  # per GPU-second (approximate)
    
    # GCP Cloud Run pricing
    GCP_CLOUD_RUN_CPU_PRICE = 0.00002400  # per vCPU-second
    GCP_CLOUD_RUN_MEMORY_PRICE = 0.00000250  # per GB-second
    GCP_CLOUD_RUN_REQUEST_PRICE = 0.00000040  # per request
    GCP_CLOUD_RUN_MIN_INSTANCES = 0  # can scale to zero
    
    # GCP Cloud Run on GKE (for GPU support)
    GCP_GKE_GPU_PRICE = 0.00035  # per GPU-second (approximate, varies by GPU type)
    
    def __init__(self):
        """Initialize cost estimator"""
        pass
    
    def estimate_deployment_cost(self, node_type: str, provider: str, 
                                duration_hours: Optional[float] = None) -> Dict:
        """
        Estimate cost for deploying and running a NIM node
        
        Args:
            node_type: Type of NIM node
            provider: Cloud provider (aws, azure, gcp)
            duration_hours: How long to run (None = per hour estimate)
            
        Returns:
            Dictionary with cost breakdown
        """
        if node_type not in self.NIM_RESOURCE_REQUIREMENTS:
            logger.warning(f"Unknown node type: {node_type}, using defaults")
            resources = {"cpu": 4, "memory": 8, "gpu": False}
        else:
            resources = self.NIM_RESOURCE_REQUIREMENTS[node_type]
        
        cpu = resources["cpu"]
        memory = resources["memory"]
        has_gpu = resources.get("gpu", False)
        
        if duration_hours is None:
            duration_hours = 1.0  # Default to 1 hour estimate
        
        provider_lower = provider.lower()
        
        if provider_lower == "aws":
            return self._estimate_aws_cost(cpu, memory, has_gpu, duration_hours)
        elif provider_lower == "azure":
            return self._estimate_azure_cost(cpu, memory, has_gpu, duration_hours)
        elif provider_lower == "gcp":
            return self._estimate_gcp_cost(cpu, memory, has_gpu, duration_hours)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _estimate_aws_cost(self, cpu: int, memory: int, has_gpu: bool, 
                           duration_hours: float) -> Dict:
        """Estimate AWS ECS Fargate costs"""
        duration_seconds = duration_hours * 3600
        
        # CPU cost
        cpu_cost = cpu * self.AWS_FARGATE_CPU_PRICE * duration_seconds
        
        # Memory cost
        memory_cost = memory * self.AWS_FARGATE_MEMORY_PRICE * duration_seconds
        
        # GPU cost (if applicable)
        gpu_cost = 0.0
        if has_gpu:
            # AWS Fargate GPU support requires specific instance types
            # This is approximate - actual GPU pricing varies
            gpu_cost = self.AWS_FARGATE_GPU_PRICE * duration_seconds
        
        total_cost = cpu_cost + memory_cost + gpu_cost
        
        # Deployment cost (API calls are free, but there's a small overhead)
        deployment_cost = 0.0  # Free
        
        return {
            "provider": "AWS",
            "deployment_cost": deployment_cost,
            "hourly_cost": total_cost / duration_hours if duration_hours > 0 else total_cost,
            "estimated_cost": total_cost,
            "duration_hours": duration_hours,
            "breakdown": {
                "cpu_cost": cpu_cost,
                "memory_cost": memory_cost,
                "gpu_cost": gpu_cost if has_gpu else None,
                "deployment_cost": deployment_cost
            },
            "resources": {
                "cpu": cpu,
                "memory_gb": memory,
                "gpu": has_gpu
            },
            "note": "Deployment itself is free. Costs shown are for running the container. "
                    "Container runs 24/7 unless set to scale-to-zero (on-demand)."
        }
    
    def _estimate_azure_cost(self, cpu: int, memory: int, has_gpu: bool,
                            duration_hours: float) -> Dict:
        """Estimate Azure Container Instances costs"""
        duration_seconds = duration_hours * 3600
        
        # CPU cost
        cpu_cost = cpu * self.AZURE_ACI_CPU_PRICE * duration_seconds
        
        # Memory cost
        memory_cost = memory * self.AZURE_ACI_MEMORY_PRICE * duration_seconds
        
        # GPU cost (if applicable)
        gpu_cost = 0.0
        if has_gpu:
            gpu_cost = self.AZURE_ACI_GPU_PRICE * duration_seconds
        
        total_cost = cpu_cost + memory_cost + gpu_cost
        
        # Deployment cost
        deployment_cost = 0.0  # Free
        
        return {
            "provider": "Azure",
            "deployment_cost": deployment_cost,
            "hourly_cost": total_cost / duration_hours if duration_hours > 0 else total_cost,
            "estimated_cost": total_cost,
            "duration_hours": duration_hours,
            "breakdown": {
                "cpu_cost": cpu_cost,
                "memory_cost": memory_cost,
                "gpu_cost": gpu_cost if has_gpu else None,
                "deployment_cost": deployment_cost
            },
            "resources": {
                "cpu": cpu,
                "memory_gb": memory,
                "gpu": has_gpu
            },
            "note": "Deployment itself is free. Costs shown are for running the container. "
                    "Container runs 24/7 unless set to scale-to-zero (on-demand)."
        }
    
    def _estimate_gcp_cost(self, cpu: int, memory: int, has_gpu: bool,
                           duration_hours: float) -> Dict:
        """Estimate GCP Cloud Run costs"""
        duration_seconds = duration_hours * 3600
        
        # Cloud Run pricing (pay per request + CPU/memory time)
        # For estimation, assume minimal requests
        estimated_requests = max(1, int(duration_hours * 10))  # ~10 requests per hour
        request_cost = estimated_requests * self.GCP_CLOUD_RUN_REQUEST_PRICE
        
        # CPU cost (only charged while handling requests)
        # For estimation, assume 50% utilization
        cpu_cost = cpu * self.GCP_CLOUD_RUN_CPU_PRICE * duration_seconds * 0.5
        
        # Memory cost
        memory_cost = memory * self.GCP_CLOUD_RUN_MEMORY_PRICE * duration_seconds * 0.5
        
        # GPU cost (if applicable, requires GKE)
        gpu_cost = 0.0
        if has_gpu:
            # GCP Cloud Run doesn't support GPU directly
            # Would need GKE, which has different pricing
            gpu_cost = self.GCP_GKE_GPU_PRICE * duration_seconds
        
        total_cost = request_cost + cpu_cost + memory_cost + gpu_cost
        
        # Deployment cost
        deployment_cost = 0.0  # Free
        
        return {
            "provider": "GCP",
            "deployment_cost": deployment_cost,
            "hourly_cost": total_cost / duration_hours if duration_hours > 0 else total_cost,
            "estimated_cost": total_cost,
            "duration_hours": duration_hours,
            "breakdown": {
                "request_cost": request_cost,
                "cpu_cost": cpu_cost,
                "memory_cost": memory_cost,
                "gpu_cost": gpu_cost if has_gpu else None,
                "deployment_cost": deployment_cost
            },
            "resources": {
                "cpu": cpu,
                "memory_gb": memory,
                "gpu": has_gpu
            },
            "note": "Deployment itself is free. Cloud Run automatically scales to zero when idle - "
                    "you only pay when handling requests. This makes it ideal for low-traffic workloads."
        }
    
    def compare_providers(self, node_type: str, duration_hours: float = 1.0) -> Dict:
        """
        Compare costs across all providers for a given node type
        
        Args:
            node_type: Type of NIM node
            duration_hours: Duration to estimate
            
        Returns:
            Dictionary with comparison
        """
        estimates = {}
        for provider in ["aws", "azure", "gcp"]:
            try:
                estimates[provider] = self.estimate_deployment_cost(
                    node_type, provider, duration_hours
                )
            except Exception as e:
                logger.error(f"Failed to estimate {provider} costs: {e}")
                estimates[provider] = {"error": str(e)}
        
        # Find cheapest
        costs = {}
        for provider, est in estimates.items():
            if "error" not in est and "estimated_cost" in est:
                costs[provider] = est["estimated_cost"]
        
        cheapest = min(costs.items(), key=lambda x: x[1]) if costs else None
        
        return {
            "node_type": node_type,
            "duration_hours": duration_hours,
            "estimates": estimates,
            "cheapest_provider": cheapest[0] if cheapest else None,
            "cheapest_cost": cheapest[1] if cheapest else None,
            "savings": {
                provider: costs[cheapest[0]] - cost 
                for provider, cost in costs.items() 
                if provider != cheapest[0] and cheapest
            } if cheapest else {}
        }

