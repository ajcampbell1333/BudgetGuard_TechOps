"""
Endpoints Tab for BudgetGuard TechOps GUI

Handles endpoint viewing, copying, and export functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import logging

logger = logging.getLogger(__name__)


def create_endpoints_tab(parent, config_manager):
    """
    Create the endpoint viewing/export tab
    
    Args:
        parent: Parent widget (ttk.Notebook)
        config_manager: ConfigManager instance for loading endpoints
        
    Returns:
        ttk.Frame: The endpoints tab frame
    """
    endpoints_frame = ttk.Frame(parent)
    parent.add(endpoints_frame, text="Endpoints")
    
    # Title
    title_label = ttk.Label(endpoints_frame, text="Deployed NIM Endpoints", 
                           font=("Arial", 16, "bold"))
    title_label.pack(pady=10)
    
    # Endpoint display area
    text_frame = ttk.Frame(endpoints_frame)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    endpoint_text = tk.Text(text_frame, wrap=tk.WORD, height=20, width=80)
    scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=endpoint_text.yview)
    endpoint_text.configure(yscrollcommand=scrollbar.set)
    
    # Enable touchpad/mouse wheel vertical scrolling on Text widget
    _enable_text_vertical_scroll(endpoint_text)
    
    endpoint_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Placeholder text
    endpoint_text.insert(tk.END, "No endpoints deployed yet.\n\n")
    endpoint_text.insert(tk.END, "Deploy NIM instances using the Deployment Selection tab,\n")
    endpoint_text.insert(tk.END, "then endpoint URLs will appear here.")
    endpoint_text.config(state=tk.DISABLED)
    
    # Buttons
    button_frame = ttk.Frame(endpoints_frame)
    button_frame.pack(pady=10)
    
    def copy_endpoints():
        """Copy endpoints to clipboard"""
        parent.winfo_toplevel().clipboard_clear()
        content = endpoint_text.get("1.0", tk.END)
        parent.winfo_toplevel().clipboard_append(content)
        messagebox.showinfo("Copied", "Endpoints copied to clipboard!")
    
    def export_endpoints():
        """Export endpoints to JSON file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                endpoints_dict = config_manager.load_endpoints()
                with open(filename, 'w') as f:
                    json.dump(endpoints_dict, f, indent=2)
                messagebox.showinfo("Export", f"Endpoints exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def refresh_endpoints():
        """Refresh endpoint display"""
        endpoint_text.config(state=tk.NORMAL)
        endpoint_text.delete("1.0", tk.END)
        
        endpoints = config_manager.load_endpoints()
        if not endpoints:
            endpoint_text.insert(tk.END, "No endpoints deployed yet.\n\n")
            endpoint_text.insert(tk.END, "Deploy NIM instances using the Deployment Selection tab,\n")
            endpoint_text.insert(tk.END, "then endpoint URLs will appear here.")
        else:
            # Ensure endpoints is a list
            if isinstance(endpoints, dict):
                endpoints_list = []
                for key, value in endpoints.items():
                    if isinstance(value, list):
                        endpoints_list.extend(value)
                    else:
                        endpoints_list.append(value)
            else:
                endpoints_list = endpoints if isinstance(endpoints, list) else []
            
            text = json.dumps(endpoints_list, indent=2)
            endpoint_text.insert(tk.END, text)
        
        endpoint_text.config(state=tk.DISABLED)
    
    ttk.Button(button_frame, text="Copy to Clipboard", 
              command=copy_endpoints).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Export to JSON", 
              command=export_endpoints).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Refresh", 
              command=refresh_endpoints).pack(side=tk.LEFT, padx=5)
    
    # Store refresh function for external access
    endpoints_frame.refresh = refresh_endpoints
    
    # Initial refresh
    refresh_endpoints()
    
    return endpoints_frame


def _enable_text_vertical_scroll(text_widget):
    """Enable two-finger/mouse wheel vertical scrolling on a Text widget.
    Works on Windows/macOS (<MouseWheel>) and Linux (<Button-4>/<Button-5>)."""
    def _on_mousewheel(event):
        try:
            if hasattr(event, 'delta') and event.delta != 0:
                step = -1 if event.delta > 0 else 1
                text_widget.yview_scroll(step, "units")
            else:
                if getattr(event, 'num', None) == 4:
                    text_widget.yview_scroll(-1, "units")
                elif getattr(event, 'num', None) == 5:
                    text_widget.yview_scroll(1, "units")
        except Exception:
            pass

    def _bind_all():
        text_widget.bind_all("<MouseWheel>", _on_mousewheel, add=True)
        text_widget.bind_all("<Button-4>", _on_mousewheel, add=True)
        text_widget.bind_all("<Button-5>", _on_mousewheel, add=True)

    def _unbind_all():
        try:
            text_widget.unbind_all("<MouseWheel>")
            text_widget.unbind_all("<Button-4>")
            text_widget.unbind_all("<Button-5>")
        except Exception:
            pass

    text_widget.bind("<Enter>", lambda e: _bind_all())
    text_widget.bind("<Leave>", lambda e: _unbind_all())

