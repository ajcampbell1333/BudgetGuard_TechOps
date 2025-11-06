"""
Credentials Tab for BudgetGuard TechOps GUI

Handles credential management UI and operations.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging

logger = logging.getLogger(__name__)


def create_credential_tab(parent, config_manager, status_var):
    """
    Create the credential management tab
    
    Args:
        parent: Parent widget (ttk.Notebook)
        config_manager: ConfigManager instance for saving/loading credentials
        status_var: tk.StringVar for status updates
        
    Returns:
        ttk.Frame: The credentials tab frame with credential_entries attribute
    """
    credential_frame = ttk.Frame(parent)
    parent.add(credential_frame, text="Credentials")
    
    # Create scrollable frame
    canvas = tk.Canvas(credential_frame)
    scrollbar = ttk.Scrollbar(credential_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Enable touchpad/mouse wheel scrolling (cross-platform)
    _enable_vertical_scroll(canvas)
    
    # Title
    title_label = ttk.Label(scrollable_frame, text="Credential Management", 
                           font=("Arial", 16, "bold"))
    title_label.pack(pady=10)
    
    # NVIDIA NIM Credentials
    nim_frame = _create_provider_section(scrollable_frame, "NVIDIA NIM", 
                                        ["NVIDIA API Key / NGC API Key"])
    nim_frame.pack(fill=tk.X, padx=20, pady=10)
    
    # AWS Credentials
    aws_frame = _create_provider_section(scrollable_frame, "AWS", 
                                        ["Access Key ID", "Secret Access Key"])
    aws_frame.pack(fill=tk.X, padx=20, pady=10)
    
    # Azure Credentials
    azure_frame = _create_provider_section(scrollable_frame, "Azure", 
                                          ["Subscription ID", "Tenant ID", "Client ID (Application ID)", 
                                           "Client Secret", "Resource Group", "Region"])
    azure_frame.pack(fill=tk.X, padx=20, pady=10)
    
    # GCP Credentials
    gcp_frame = _create_provider_section(scrollable_frame, "GCP", 
                                        ["Project ID", "Service Account JSON File Path", "Region", "Zone"])
    gcp_frame.pack(fill=tk.X, padx=20, pady=10)
    
    # Buttons
    button_frame = ttk.Frame(scrollable_frame)
    button_frame.pack(fill=tk.X, padx=20, pady=20)
    
    # Store credential entries for later access
    credential_entries = {}
    
    def validate_credentials():
        """Validate all entered credentials"""
        status_var.set("Validating credentials...")
        parent.winfo_toplevel().update()
        
        # TODO: Implement actual credential validation
        # For now, just check if fields are filled
        validated = []
        failed = []
        
        for provider, entries in credential_entries.items():
            all_filled = all(entry.get().strip() for entry in entries.values())
            if all_filled:
                validated.append(provider.upper())
            else:
                failed.append(provider.upper())
        
        if validated:
            message = f"Validated: {', '.join(validated)}\n"
        else:
            message = ""
        
        if failed:
            message += f"Missing or incomplete: {', '.join(failed)}"
        
        if validated:
            messagebox.showinfo("Validation Results", 
                               f"Credentials validated:\n{message}" if failed 
                               else f"All credentials validated:\n{', '.join(validated)}")
        else:
            messagebox.showwarning("Validation Results", 
                                  f"Please fill in all required fields:\n{message}")
        
        status_var.set("Validation complete")
    
    def save_credentials():
        """Save credentials to encrypted storage"""
        status_var.set("Saving credentials...")
        parent.winfo_toplevel().update()
        
        try:
            credentials = {}
            for provider, entries in credential_entries.items():
                provider_creds = {}
                for field_name, entry in entries.items():
                    provider_creds[field_name] = entry.get().strip()
                credentials[provider] = provider_creds
            
            # Save via config manager (handles encryption)
            config_manager.save_credentials(credentials)
            
            messagebox.showinfo("Success", "Credentials saved successfully!")
            status_var.set("Credentials saved")
            logger.info("Credentials saved successfully")
        except Exception as e:
            error_msg = f"Failed to save credentials: {str(e)}"
            messagebox.showerror("Error", error_msg)
            status_var.set("Error saving credentials")
            logger.error(error_msg, exc_info=True)
    
    def load_credentials():
        """Load credentials from storage"""
        status_var.set("Loading credentials...")
        parent.winfo_toplevel().update()
        
        try:
            credentials = config_manager.load_credentials()
            
            # Populate entry fields
            for provider, entries in credential_entries.items():
                if provider in credentials:
                    provider_creds = credentials[provider]
                    for field_name, entry in entries.items():
                        if field_name in provider_creds:
                            entry.delete(0, tk.END)
                            entry.insert(0, provider_creds[field_name])
            
            messagebox.showinfo("Success", "Credentials loaded successfully!")
            status_var.set("Credentials loaded")
            logger.info("Credentials loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load credentials: {str(e)}"
            messagebox.showerror("Error", error_msg)
            status_var.set("Error loading credentials")
            logger.error(error_msg, exc_info=True)
    
    def browse_file(entry_widget):
        """Browse for a file and update the entry widget"""
        filename = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)
    
    validate_btn = ttk.Button(button_frame, text="Validate Credentials", 
                              command=validate_credentials)
    validate_btn.pack(side=tk.LEFT, padx=5)
    
    save_btn = ttk.Button(button_frame, text="Save Credentials", 
                         command=save_credentials)
    save_btn.pack(side=tk.LEFT, padx=5)
    
    load_btn = ttk.Button(button_frame, text="Load Credentials", 
                         command=load_credentials)
    load_btn.pack(side=tk.LEFT, padx=5)
    
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Initialize credential entries
    _initialize_credential_entries(nim_frame, "nvidia", credential_entries, browse_file)
    _initialize_credential_entries(aws_frame, "aws", credential_entries, browse_file)
    _initialize_credential_entries(azure_frame, "azure", credential_entries, browse_file)
    _initialize_credential_entries(gcp_frame, "gcp", credential_entries, browse_file)
    
    # Store credential_entries for external access
    credential_frame.credential_entries = credential_entries
    
    return credential_frame


def _create_provider_section(parent, provider_name, field_names):
    """Create a credential section for a provider"""
    frame = ttk.LabelFrame(parent, text=provider_name, padding=10)
    
    entries = {}
    for field_name in field_names:
        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=5)
        
        label = ttk.Label(row, text=f"{field_name}:", width=25, anchor=tk.W)
        label.pack(side=tk.LEFT, padx=5)
        
        if "Secret" in field_name or "Key" in field_name:
            entry = ttk.Entry(row, show="*", width=40)
        else:
            entry = ttk.Entry(row, width=40)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        entries[field_name] = entry
        
        # For GCP JSON file path, add browse button
        if "JSON File" in field_name:
            browse_btn = ttk.Button(row, text="Browse...", 
                                   command=lambda e=entry: _browse_file(e))
            browse_btn.pack(side=tk.LEFT, padx=5)
    
    # Store entries in frame for later access
    frame.entries = entries
    return frame


def _initialize_credential_entries(frame, provider_key, credential_entries, browse_file_func):
    """Initialize credential entries dictionary"""
    if not hasattr(frame, 'entries'):
        return
    credential_entries[provider_key] = frame.entries


def _browse_file(entry_widget):
    """Browse for a file and update the entry widget"""
    filename = filedialog.askopenfilename(
        title="Select File",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filename)


def _enable_vertical_scroll(canvas):
    """Enable two-finger/mouse wheel vertical scrolling on the given Canvas.
    Works on Windows/macOS (<MouseWheel>) and Linux (<Button-4>/<Button-5>)."""
    def _on_mousewheel(event):
        try:
            if hasattr(event, 'delta') and event.delta != 0:
                # Windows/macOS: event.delta is typically +/-120 multiples
                step = -1 if event.delta > 0 else 1
                canvas.yview_scroll(step, "units")
            else:
                # Linux: use Button-4 (up) / Button-5 (down)
                if getattr(event, 'num', None) == 4:
                    canvas.yview_scroll(-1, "units")
                elif getattr(event, 'num', None) == 5:
                    canvas.yview_scroll(1, "units")
        except Exception:
            pass

    def _bind_all():
        canvas.bind_all("<MouseWheel>", _on_mousewheel, add=True)
        canvas.bind_all("<Button-4>", _on_mousewheel, add=True)
        canvas.bind_all("<Button-5>", _on_mousewheel, add=True)

    def _unbind_all():
        try:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        except Exception:
            pass

    # Bind only while pointer is over the canvas to avoid global hijack
    canvas.bind("<Enter>", lambda e: _bind_all())
    canvas.bind("<Leave>", lambda e: _unbind_all())

