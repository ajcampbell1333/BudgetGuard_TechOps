"""
Deployment State Management for BudgetGuard TechOps GUI

Handles state persistence for deployment checkboxes across GPU tiers and modes.
"""

import logging

logger = logging.getLogger(__name__)


class DeploymentStateManager:
    """Manages state for deployment checkboxes across GPU tiers"""
    
    def __init__(self):
        """Initialize state manager"""
        # Persistent state: {gpu_tier: {node: {provider: bool}}}
        # When local-only mode, gpu_tier is None
        self.deployment_state = {}  # Persistent state per GPU tier
        self.local_only_state = {}  # Persistent state: {node: bool}
        self.current_gpu_tier = None
        self.is_switching_gpu_tier = False
    
    def set_current_gpu_tier(self, gpu_tier: str):
        """Set the current GPU tier"""
        self.current_gpu_tier = gpu_tier
    
    def save_state_for_gpu_tier(self, gpu_tier: str, deployment_checkboxes: dict):
        """Save checkbox state for a specific GPU tier"""
        try:
            if gpu_tier not in self.deployment_state:
                self.deployment_state[gpu_tier] = {}
            
            for node, node_data in deployment_checkboxes.items():
                if isinstance(node_data, dict) and 'vars' in node_data:
                    if node not in self.deployment_state[gpu_tier]:
                        self.deployment_state[gpu_tier][node] = {}
                    for provider, var in node_data['vars'].items():
                        if var is not None:
                            self.deployment_state[gpu_tier][node][provider] = var.get()
                            logger.debug(f"Saved state for {gpu_tier}/{node} -> {provider}: {var.get()}")
        except Exception as e:
            logger.error(f"Error saving checkbox state for GPU tier {gpu_tier}: {e}", exc_info=True)
    
    def save_local_only_state(self, local_only_checkboxes: dict):
        """Save local-only checkbox state"""
        try:
            for node, var in local_only_checkboxes.items():
                if var is not None:
                    self.local_only_state[node] = var.get()
                    logger.debug(f"Saved local state for {node}: {var.get()}")
        except Exception as e:
            logger.error(f"Error saving local-only state: {e}", exc_info=True)
    
    def restore_state_for_gpu_tier(self, gpu_tier: str, deployment_checkboxes: dict):
        """Restore checkbox state for a specific GPU tier"""
        try:
            logger.debug(f"Attempting to restore state for GPU tier: {gpu_tier}")
            
            if gpu_tier in self.deployment_state:
                gpu_state = self.deployment_state[gpu_tier]
                logger.debug(f"Found state for GPU tier {gpu_tier}: {gpu_state}")
                
                for node, node_data in deployment_checkboxes.items():
                    if isinstance(node_data, dict) and 'vars' in node_data:
                        if node in gpu_state:
                            for provider, var in node_data['vars'].items():
                                if provider in gpu_state[node] and var is not None:
                                    should_be_checked = gpu_state[node][provider]
                                    var.set(should_be_checked)
                                    logger.debug(f"Restored state for {gpu_tier}/{node} -> {provider}: {should_be_checked}")
                        else:
                            logger.debug(f"No saved state for node {node} in GPU tier {gpu_tier}")
            else:
                # No saved state for this GPU tier - start with empty checkboxes
                logger.debug(f"No saved state for GPU tier: {gpu_tier}. Starting with empty checkboxes.")
                # Explicitly uncheck all checkboxes for this new GPU tier
                for node, node_data in deployment_checkboxes.items():
                    if isinstance(node_data, dict) and 'vars' in node_data:
                        for provider, var in node_data['vars'].items():
                            if var is not None:
                                var.set(False)
                                logger.debug(f"Unchecked {gpu_tier}/{node} -> {provider} (no saved state)")
        except Exception as e:
            logger.error(f"Error restoring checkbox state for GPU tier {gpu_tier}: {e}", exc_info=True)
    
    def restore_local_only_state(self, local_only_checkboxes: dict):
        """Restore local-only checkbox state"""
        try:
            for node, var in local_only_checkboxes.items():
                if node in self.local_only_state and var is not None:
                    var.set(self.local_only_state[node])
                    logger.debug(f"Restored local state for {node}: {self.local_only_state[node]}")
        except Exception as e:
            logger.error(f"Error restoring local-only state: {e}", exc_info=True)
    
    def on_checkbox_change(self, node: str, provider: str, value: bool):
        """Handle checkbox change in normal mode"""
        try:
            current_gpu_tier = self.current_gpu_tier
            if current_gpu_tier not in self.deployment_state:
                self.deployment_state[current_gpu_tier] = {}
            if node not in self.deployment_state[current_gpu_tier]:
                self.deployment_state[current_gpu_tier][node] = {}
            self.deployment_state[current_gpu_tier][node][provider] = value
            logger.debug(f"State updated for {current_gpu_tier}/{node} -> {provider}: {value}")
        except Exception as e:
            logger.warning(f"Error updating state for {node} -> {provider}: {e}")
    
    def on_local_checkbox_change(self, node: str, value: bool):
        """Handle checkbox change in local-only mode"""
        try:
            self.local_only_state[node] = value
            logger.debug(f"Local state updated for {node}: {value}")
        except Exception as e:
            logger.warning(f"Error updating local state for {node}: {e}")
    
    def on_gpu_tier_changed(self, old_tier: str, new_tier: str, deployment_checkboxes: dict):
        """Handle GPU tier change - save old tier state, restore new tier state"""
        if old_tier != new_tier and deployment_checkboxes:
            # Save state for old tier
            self.save_state_for_gpu_tier(old_tier, deployment_checkboxes)
            logger.debug(f"Saved state for old GPU tier: {old_tier}, switching to: {new_tier}")
            
            # Update current tier
            self.current_gpu_tier = new_tier
    
    def get_selected_deployments(self, deployment_checkboxes: dict, local_only_checkboxes: dict, 
                                 is_local_only: bool) -> list:
        """
        Get list of selected deployments across all GPU tiers
        
        Returns:
            list: List of (node, provider, gpu_tier) tuples
        """
        deployment_tasks = []
        
        if is_local_only:
            # Local-only mode
            for node, var in local_only_checkboxes.items():
                if var and var.get():
                    deployment_tasks.append((node, "local", None))
        else:
            # Normal mode - collect deployments from ALL GPU tiers
            for gpu_tier, gpu_state in self.deployment_state.items():
                for node, node_providers in gpu_state.items():
                    for provider, is_checked in node_providers.items():
                        if is_checked:
                            deployment_tasks.append((node, provider, gpu_tier))
            
            # Also check currently visible checkboxes (in case user just checked but state not saved yet)
            current_gpu_tier = self.current_gpu_tier
            for node, node_data in deployment_checkboxes.items():
                if isinstance(node_data, dict) and 'vars' in node_data:
                    node_checkboxes = node_data['vars']
                    has_cloud_deployment = False
                    
                    for provider, var in node_checkboxes.items():
                        if var is not None and var.get():
                            # Check if this combination is already in deployment_tasks
                            task_key = (node, provider, current_gpu_tier)
                            if task_key not in deployment_tasks:
                                deployment_tasks.append(task_key)
                            if provider.lower() != "local":
                                has_cloud_deployment = True
                    
                    # Auto-deploy local if any cloud provider is selected for current tier
                    if has_cloud_deployment:
                        local_var = node_checkboxes.get("local")
                        if local_var and not local_var.get():
                            task_key = (node, "local", current_gpu_tier)
                            if task_key not in deployment_tasks:
                                deployment_tasks.append(task_key)
        
        return deployment_tasks
    
    def update_selected_count(self, deployment_checkboxes: dict, local_only_checkboxes: dict,
                             is_local_only: bool) -> int:
        """
        Calculate total selected node count across all GPU tiers
        
        Returns:
            int: Total count of selected deployments
        """
        try:
            total_count = 0
            all_checked = set()  # Use set to avoid double-counting
            
            if is_local_only:
                # Count local-only checkboxes
                for var in local_only_checkboxes.values():
                    if var is not None and var.get():
                        total_count += 1
            else:
                # Count all checked node+provider combinations across ALL GPU tiers
                for gpu_tier, gpu_state in self.deployment_state.items():
                    for node, node_providers in gpu_state.items():
                        for provider, is_checked in node_providers.items():
                            if is_checked:
                                # Count each unique node+provider+GPU tier combination
                                all_checked.add(f"{gpu_tier}:{node}:{provider}")
                
                # Also check currently visible checkboxes (in case user just checked but state not saved yet)
                current_gpu_tier = self.current_gpu_tier
                for node, node_data in deployment_checkboxes.items():
                    if isinstance(node_data, dict) and 'vars' in node_data:
                        for provider, var in node_data['vars'].items():
                            if var is not None and var.get():
                                all_checked.add(f"{current_gpu_tier}:{node}:{provider}")
                
                total_count = len(all_checked)
            
            return total_count
        except Exception as e:
            logger.warning(f"Error updating selected count: {e}")
            return 0

