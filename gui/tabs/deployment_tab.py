"""
Deployment Tab for BudgetGuard TechOps GUI

Handles deployment selection UI (table, GPU tier selector, local-only mode).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading

from .deployment_state import DeploymentStateManager

logger = logging.getLogger(__name__)


def create_deployment_tab(parent, config_manager, status_var, state_manager, 
                         deployment_handlers, deployment_actions):
    """
    Create the deployment selection tab
    
    Args:
        parent: Parent widget (ttk.Notebook)
        config_manager: ConfigManager instance
        status_var: tk.StringVar for status updates
        state_manager: DeploymentStateManager instance
        deployment_handlers: Module with deployment handler functions
        deployment_actions: Module with deployment action functions
        
    Returns:
        dict: Contains frame and callback functions
    """
    deployment_frame = ttk.Frame(parent)
    parent.add(deployment_frame, text="Deployment Selection")
    
    # Title
    title_label = ttk.Label(deployment_frame, text="Select Nodes and Providers for Deployment", 
                           font=("Arial", 16, "bold"))
    title_label.pack(pady=10)
    
    # Deployment mode toggle
    mode_frame = ttk.Frame(deployment_frame)
    mode_frame.pack(fill=tk.X, padx=20, pady=10)
    
    deploy_local_only = tk.BooleanVar(value=False)
    
    # Info label
    info_label = ttk.Label(
        mode_frame, 
        text="(When disabled, each node chosen to deploy to a cloud provider\nwill automatically create a local install package as well.\nLocal packages are installed on artist workstations via install-package command.)",
        font=("Arial", 9),
        foreground="gray"
    )
    info_label.pack(side=tk.LEFT, padx=10)
    
    # GPU Tier Selection (hidden when Deploy Local Only is checked)
    gpu_tier_frame = ttk.LabelFrame(deployment_frame, text="GPU Tier Selection")
    gpu_tier_frame.pack(fill=tk.X, padx=20, pady=10)
    
    gpu_tier_var = tk.StringVar(value="a10g")  # Default to A10G (recommended)
    
    ttk.Radiobutton(
        gpu_tier_frame,
        text="T4 (Cost-Effective)\n$0.50/hr, 30-60s/image",
        variable=gpu_tier_var,
        value="t4"
    ).pack(side=tk.LEFT, padx=10)
    
    ttk.Radiobutton(
        gpu_tier_frame,
        text="A10G (Recommended) ⭐\n$1.00/hr, 15-30s/image",
        variable=gpu_tier_var,
        value="a10g"
    ).pack(side=tk.LEFT, padx=10)
    
    ttk.Radiobutton(
        gpu_tier_frame,
        text="A100 (Fastest)\n$32.00/hr, 5-15s/image",
        variable=gpu_tier_var,
        value="a100"
    ).pack(side=tk.LEFT, padx=10)
    
    # Info label for GPU selection
    gpu_info_label = ttk.Label(
        gpu_tier_frame,
        text="\nGPU tier selector is for viewing only.\nAll checked nodes across all tiers will deploy together.",
        font=("Arial", 8),
        foreground="gray"
    )
    gpu_info_label.pack(side=tk.LEFT, padx=10)
    
    # Quick action buttons
    quick_frame = ttk.Frame(deployment_frame)
    quick_frame.pack(fill=tk.X, padx=20, pady=10)
    
    # Available NIM nodes
    nim_nodes = [
        "FLUX Dev",
        "FLUX Canny",
        "FLUX Depth",
        "FLUX Kontext",
        "SDXL",
        "Llama 3",
        "Mixtral",
        "Phi-3"
    ]
    
    providers = ["AWS", "Azure", "GCP", "NVIDIA-hosted"]  # Local is auto-deployed, not manually selectable
    
    # Create checkbox table frame with scrollbars
    table_frame = ttk.Frame(deployment_frame)
    table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    # Scrollable canvas for table
    canvas = tk.Canvas(table_frame)
    scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
    scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=canvas.xview)
    scrollable_table = ttk.Frame(canvas)
    
    scrollable_table.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_table, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
    
    # Enable touchpad/mouse wheel scrolling (vertical + Shift+wheel horizontal)
    _enable_canvas_scroll(canvas)
    
    # Store checkboxes and their state
    deployment_checkboxes = {}  # Normal mode checkboxes
    local_only_checkboxes = {}  # Local-only mode checkboxes
    
    # Initialize state manager and track which tier the current checkboxes represent
    state_manager.set_current_gpu_tier(gpu_tier_var.get())
    visible_gpu_tier = gpu_tier_var.get()
    
    def on_gpu_tier_changed(*args):
        """Callback when GPU tier radio button changes"""
        nonlocal visible_gpu_tier
        new_gpu_tier = gpu_tier_var.get()
        old_gpu_tier = visible_gpu_tier
        
        if old_gpu_tier != new_gpu_tier and deployment_checkboxes:
            # Update current/visible tier (but pass the old tier to the table to save under old)
            visible_gpu_tier = new_gpu_tier
            state_manager.set_current_gpu_tier(new_gpu_tier)
            # Recreate table for the new tier
            create_deployment_table(save_under_gpu_tier=old_gpu_tier)
    
    gpu_tier_var.trace_add('write', on_gpu_tier_changed)
    
    def create_deployment_table(save_under_gpu_tier: str = None):
        """Create the deployment table (normal or local-only mode)
        save_under_gpu_tier: if provided, save current checkboxes under this tier before clearing
        """
        # Save current state before clearing under the correct tier
        is_local_only = deploy_local_only.get()
        if deployment_checkboxes or local_only_checkboxes:
            if is_local_only:
                state_manager.save_local_only_state(local_only_checkboxes)
            else:
                tier_to_save = save_under_gpu_tier if save_under_gpu_tier else visible_gpu_tier
                state_manager.save_state_for_gpu_tier(tier_to_save, deployment_checkboxes)
        
        # Clear existing table
        for widget in scrollable_table.winfo_children():
            widget.destroy()
        
        # Clear checkbox references
        deployment_checkboxes.clear()
        local_only_checkboxes.clear()
        
        logger.debug(f"Creating deployment table - local_only mode: {is_local_only}")
        
        if is_local_only:
            create_local_only_table()
        else:
            create_normal_table()
        
        # Restore state
        if is_local_only:
            state_manager.restore_local_only_state(local_only_checkboxes)
        else:
            state_manager.restore_state_for_gpu_tier(visible_gpu_tier, deployment_checkboxes)
        
        # Update selected count
        update_selected_count()
        
        # Update scroll region
        scrollable_table.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    def create_normal_table():
        """Create normal deployment table with all providers"""
        # Create header row
        header_frame = ttk.Frame(scrollable_table)
        header_frame.pack(fill=tk.X)
        
        ttk.Label(header_frame, text="Node", width=20, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        for provider in providers:
            ttk.Label(header_frame, text=provider, width=15, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        
        # Create rows for each node
        for node in nim_nodes:
            row_frame = ttk.Frame(scrollable_table)
            row_frame.pack(fill=tk.X)
            
            ttk.Label(row_frame, text=node, width=20, anchor=tk.W).pack(side=tk.LEFT, padx=2)
            
            node_checkboxes = {}
            for provider in providers:
                var = tk.BooleanVar()
                # Add callback to save state when checkbox changes
                var.trace_add('write', lambda *args, n=node, p=provider.lower(), v=var: 
                             state_manager.on_checkbox_change(n, p, v.get()))
                # Add callback to update count when checkbox changes
                var.trace_add('write', lambda *args: update_selected_count())
                cb = ttk.Checkbutton(row_frame, variable=var)
                cb.pack(side=tk.LEFT, padx=2)
                node_checkboxes[provider.lower()] = var
            
            # Store as dict with vars key for consistency with state functions
            deployment_checkboxes[node] = {'vars': node_checkboxes}
    
    def create_local_only_table():
        """Create local-only deployment table (single column)"""
        # Create header
        header_frame = ttk.Frame(scrollable_table)
        header_frame.pack(fill=tk.X)
        
        ttk.Label(header_frame, text="Node", width=30, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        ttk.Label(header_frame, text="Local", width=20, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=2)
        
        # Create rows for each node
        for node in nim_nodes:
            row_frame = ttk.Frame(scrollable_table)
            row_frame.pack(fill=tk.X)
            
            ttk.Label(row_frame, text=node, width=30, anchor=tk.W).pack(side=tk.LEFT, padx=2)
            
            var = tk.BooleanVar()
            # Add callback to save state when checkbox changes
            var.trace_add('write', lambda *args, n=node, v=var: 
                         state_manager.on_local_checkbox_change(n, v.get()))
            # Add callback to update count when checkbox changes
            var.trace_add('write', lambda *args: update_selected_count())
            cb = ttk.Checkbutton(row_frame, variable=var)
            cb.pack(side=tk.LEFT, padx=2)
            
            local_only_checkboxes[node] = var
    
    def toggle_local_only_mode():
        """Toggle between normal and local-only deployment modes"""
        # Show/hide GPU tier selector based on local-only mode
        if deploy_local_only.get():
            gpu_tier_frame.pack_forget()
        else:
            try:
                gpu_tier_frame.pack_info()
                gpu_tier_frame.pack_configure(fill=tk.X, padx=20, pady=10, before=quick_frame)
            except:
                gpu_tier_frame.pack(fill=tk.X, padx=20, pady=10, before=quick_frame)
        
        # Recreate table to show appropriate view
        create_deployment_table()
    
    local_only_cb = ttk.Checkbutton(
        mode_frame, 
        text="Create Local Install Package Only", 
        variable=deploy_local_only,
        command=toggle_local_only_mode
    )
    local_only_cb.pack(side=tk.LEFT, padx=5)
    
    def select_all_deployments():
        """Select all checkboxes"""
        if deploy_local_only.get():
            for var in local_only_checkboxes.values():
                var.set(True)
        else:
            for node_data in deployment_checkboxes.values():
                for var in node_data['vars'].values():
                    var.set(True)
        update_selected_count()
    
    def deselect_all_deployments():
        """Deselect all checkboxes"""
        if deploy_local_only.get():
            for var in local_only_checkboxes.values():
                var.set(False)
        else:
            for node_data in deployment_checkboxes.values():
                for var in node_data['vars'].values():
                    var.set(False)
        update_selected_count()
    
    ttk.Button(quick_frame, text="Select All", 
              command=select_all_deployments).pack(side=tk.LEFT, padx=5)
    ttk.Button(quick_frame, text="Deselect All", 
              command=deselect_all_deployments).pack(side=tk.LEFT, padx=5)
    
    # Pack scrollbars and canvas
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
    scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Selected count display
    selected_count_label = ttk.Label(
        deployment_frame,
        text="0 nodes selected",
        font=("Arial", 10),
        foreground="gray"
    )
    selected_count_label.pack(pady=(10, 5))
    
    def update_selected_count():
        """Update the selected node count display"""
        count = state_manager.update_selected_count(
            deployment_checkboxes, local_only_checkboxes, deploy_local_only.get()
        )
        if count == 1:
            selected_count_label.config(text="1 node selected")
        else:
            selected_count_label.config(text=f"{count} nodes selected")
    
    def deploy_selected():
        """Deploy selected nodes to selected providers across ALL GPU tiers"""
        if deploy_local_only.get():
            # Local-only mode
            selected = []
            for node, var in local_only_checkboxes.items():
                if var.get():
                    selected.append(f"{node} → Local")
            
            if not selected:
                messagebox.showwarning("No Selection", "Please select at least one node for local deployment")
                return
            
            msg = f"Create local install package for the following nodes?\n\n" + "\n".join(selected) + "\n\nThis will export Docker images and create an install package.\nInstall the package on each workstation using install-package command."
            if not messagebox.askyesno("Confirm Local Install Package Creation", msg):
                return
            
            status_var.set("Deploying...")
            parent.winfo_toplevel().update()
            
            deployment_tasks = []
            for node, var in local_only_checkboxes.items():
                if var.get():
                    deployment_tasks.append((node, "local", None))  # No GPU tier for local
        else:
            # Normal mode - collect deployments from ALL GPU tiers
            deployment_tasks = deployment_actions.collect_selected_deployments(
                state_manager, deployment_checkboxes, local_only_checkboxes, False
            )
            
            if not deployment_tasks:
                messagebox.showwarning("No Selection", "Please select at least one node/provider combination")
                return
            
            # Format selected list for confirmation
            selected = []
            for node, provider, gpu_tier in deployment_tasks:
                gpu_display = f" ({gpu_tier.upper()})" if gpu_tier else ""
                selected.append(f"{node} → {provider}{gpu_display}")
            
            # Confirm deployment
            msg = f"Deploy the following?\n\n" + "\n".join(selected)
            if not messagebox.askyesno("Confirm Deployment", msg):
                return
            
            status_var.set("Deploying...")
            parent.winfo_toplevel().update()
        
        # Execute deployments in background thread
        # Note: refresh callback will be set by main_window
        thread = threading.Thread(
            target=deployment_actions.execute_deployments,
            args=(deployment_tasks, config_manager, status_var, parent.winfo_toplevel(), None)
        )
        thread.daemon = True
        thread.start()
    
    # Deploy button
    deploy_btn = ttk.Button(deployment_frame, text="Deploy Selected", 
                           command=deploy_selected, style="Accent.TButton")
    deploy_btn.pack(pady=(0, 20))
    
    # Create initial table
    create_deployment_table()
    
    # Update count display initially
    update_selected_count()
    
    # Return frame and callbacks
    return {
        'frame': deployment_frame,
        'refresh': update_selected_count  # For external refresh if needed
    }

def _enable_canvas_scroll(canvas):
    """Enable two-finger/mouse wheel scrolling on a Canvas.
    Vertical by default, horizontal with Shift pressed.
    Supports Windows/macOS (<MouseWheel>) and Linux (<Button-4>/<Button-5>)."""
    def _on_mousewheel(event):
        try:
            shift = (getattr(event, 'state', 0) & 0x0001) != 0  # Shift key mask
            # Windows/macOS path
            if hasattr(event, 'delta') and event.delta != 0:
                step = -1 if event.delta > 0 else 1
                if shift:
                    canvas.xview_scroll(step, "units")
                else:
                    canvas.yview_scroll(step, "units")
                return
            # Linux buttons
            if getattr(event, 'num', None) == 4:  # up
                if shift:
                    canvas.xview_scroll(-1, "units")
                else:
                    canvas.yview_scroll(-1, "units")
            elif getattr(event, 'num', None) == 5:  # down
                if shift:
                    canvas.xview_scroll(1, "units")
                else:
                    canvas.yview_scroll(1, "units")
        except Exception:
            pass

    def _bind_all():
        canvas.bind_all("<MouseWheel>", _on_mousewheel, add=True)
        canvas.bind_all("<Shift-MouseWheel>", _on_mousewheel, add=True)
        canvas.bind_all("<Button-4>", _on_mousewheel, add=True)
        canvas.bind_all("<Button-5>", _on_mousewheel, add=True)

    def _unbind_all():
        try:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Shift-MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        except Exception:
            pass

    canvas.bind("<Enter>", lambda e: _bind_all())
    canvas.bind("<Leave>", lambda e: _unbind_all())

