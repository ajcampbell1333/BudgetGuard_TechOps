"""
Deployment Actions for BudgetGuard TechOps GUI

Handles deployment execution, result handling, and UI updates.
"""

import threading
import logging
from tkinter import messagebox

from .deployment_handlers import deploy_to_aws, deploy_to_azure, deploy_to_gcp, deploy_to_local

logger = logging.getLogger(__name__)


def execute_deployments(deployment_tasks, config_manager, status_var, root, refresh_endpoints_callback):
    """
    Execute deployments in background thread
    
    Args:
        deployment_tasks: List of (node, provider, gpu_tier) tuples
        config_manager: ConfigManager instance for saving endpoints
        status_var: tk.StringVar for status updates
        root: tk.Tk root window for UI updates
        refresh_endpoints_callback: Function to refresh endpoints tab
    """
    results = []
    errors = []
    
    for deployment in deployment_tasks:
        # deployment is a tuple: (node, provider, gpu_tier)
        node, provider, gpu_tier = deployment
        try:
            gpu_display = f" ({gpu_tier.upper()})" if gpu_tier else ""
            root.after(0, lambda n=node, p=provider, g=gpu_display: status_var.set(f"Deploying {n} to {p}{g}..."))
            
            result = None
            if provider.lower() == "aws":
                result = deploy_to_aws(node, gpu_tier, config_manager)
            elif provider.lower() == "azure":
                result = deploy_to_azure(node, gpu_tier, config_manager)
            elif provider.lower() == "gcp":
                result = deploy_to_gcp(node, gpu_tier, config_manager)
            elif provider.lower() == "local":
                result = deploy_to_local(node, config_manager)
            elif provider.lower() == "nvidia-hosted":
                # Phase 5
                errors.append(f"{node} → {provider}: NVIDIA-hosted deployment will be implemented in Phase 5")
            else:
                errors.append(f"{node} → {provider}: Unknown provider")
            
            if result:
                results.append(result)
                # Save endpoint
                endpoints = config_manager.load_endpoints()
                if not isinstance(endpoints, list):
                    endpoints = []
                endpoints.append(result)
                config_manager.save_endpoints(endpoints)
            elif provider.lower() not in ["nvidia-hosted"]:
                errors.append(f"{node} → {provider}: Deployment failed")
                
        except Exception as e:
            error_msg = f"Failed to deploy {node} to {provider}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)
    
    # Update UI with results
    def update_ui():
        if results:
            msg = f"Successfully deployed {len(results)} instance(s):\n\n"
            msg += "\n".join([f"• {r['node_type']} → {r['provider']}: {r['endpoint']}" for r in results])
            messagebox.showinfo("Deployment Complete", msg)
            status_var.set(f"Deployed {len(results)} instance(s)")
            if refresh_endpoints_callback:
                refresh_endpoints_callback()
        else:
            status_var.set("No deployments completed")
        
        if errors:
            error_msg = "Errors occurred:\n\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors) - 5} more"
            messagebox.showerror("Deployment Errors", error_msg)
    
    root.after(0, update_ui)


def collect_selected_deployments(state_manager, deployment_checkboxes, local_only_checkboxes, 
                                 is_local_only: bool) -> list:
    """
    Collect selected deployments from state manager
    
    Args:
        state_manager: DeploymentStateManager instance
        deployment_checkboxes: Normal mode checkboxes dict
        local_only_checkboxes: Local-only mode checkboxes dict
        is_local_only: Whether in local-only mode
        
    Returns:
        list: List of (node, provider, gpu_tier) tuples
    """
    return state_manager.get_selected_deployments(
        deployment_checkboxes, local_only_checkboxes, is_local_only
    )

