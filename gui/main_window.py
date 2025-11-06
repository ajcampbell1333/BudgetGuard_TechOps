"""
Main GUI Window for BudgetGuard TechOps

Provides graphical interface for:
- Credential management
- Node/provider deployment selection
- Deployment execution
- Endpoint viewing and export

Platform Support: Windows and Linux (tkinter is built into Python)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging

from .tabs import credentials_tab, deployment_tab, endpoints_tab
from .tabs.deployment_state import DeploymentStateManager
from .tabs import deployment_handlers, deployment_actions

logger = logging.getLogger(__name__)


class BudgetGuardTechOpsGUI:
    """Main GUI window for BudgetGuard TechOps"""
    
    def __init__(self, config_manager):
        """
        Initialize the GUI
        
        Args:
            config_manager: ConfigManager instance for handling configuration
        """
        self.config_manager = config_manager
        self.root = tk.Tk()
        self.root.title("BudgetGuard TechOps")
        self.root.geometry("1000x700")
        
        # Set window icon if available
        try:
            # TODO: Add icon file
            pass
        except:
            pass
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                               relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize deployment state manager
        self.state_manager = DeploymentStateManager()
        
        # Create tabs
        self.credential_frame = credentials_tab.create_credential_tab(
            self.notebook, self.config_manager, self.status_var
        )
        
        deployment_result = deployment_tab.create_deployment_tab(
            self.notebook, self.config_manager, self.status_var,
            self.state_manager, deployment_handlers, deployment_actions
        )
        self.deployment_frame = deployment_result['frame']
        
        # Create endpoints tab with refresh callback
        self.endpoints_frame = endpoints_tab.create_endpoints_tab(
            self.notebook, self.config_manager
        )
        
        # Store refresh callback for endpoints (used after deployments)
        self.refresh_endpoints = self.endpoints_frame.refresh
        
        # Create a wrapper for execute_deployments that includes the refresh callback
        original_execute = deployment_actions.execute_deployments
        
        def execute_with_refresh(deployment_tasks, config_manager, status_var, root, refresh_endpoints_callback=None):
            """Wrapper that adds refresh callback if not provided"""
            if refresh_endpoints_callback is None:
                refresh_endpoints_callback = self.refresh_endpoints
            return original_execute(deployment_tasks, config_manager, status_var, root, refresh_endpoints_callback)
        
        # Replace the function in the module
        deployment_actions.execute_deployments = execute_with_refresh
    
    def run(self):
        """Run the GUI application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            logger.info("GUI closed by user")
        except Exception as e:
            logger.error(f"GUI error: {e}", exc_info=True)
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
