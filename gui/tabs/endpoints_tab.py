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
    
    def export_artists_config():
        """Export endpoints in Artists config format (for BudgetGuard Artists node)"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Artists Config",
            initialfile="budgetguard_artists_config.json"
        )
        if filename:
            try:
                from tools.export import build_artist_config
                from pathlib import Path
                
                # Build artist config
                artist_config = build_artist_config(config_manager)
                
                # Write to file
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(artist_config, f, indent=2)
                
                messagebox.showinfo(
                    "Export Complete",
                    f"Artists config exported to:\n{filename}\n\n"
                    "This file contains endpoints and credential status (no secrets).\n"
                    "Use with install-credentials command to install on workstations."
                )
            except Exception as e:
                logger.error(f"Failed to export artists config: {e}", exc_info=True)
                messagebox.showerror("Export Error", f"Failed to export artists config:\n{str(e)}")
    
    def share_endpoints():
        """Share endpoints via clipboard in a formatted way"""
        endpoints = config_manager.load_endpoints()
        if not endpoints:
            messagebox.showwarning("No Endpoints", "No endpoints to share")
            return
        
        # Format endpoints for sharing
        share_text = "BudgetGuard NIM Endpoints\n"
        share_text += "=" * 50 + "\n\n"
        
        # Normalize endpoints
        if isinstance(endpoints, dict):
            endpoint_list = []
            for key, value in endpoints.items():
                if isinstance(value, list):
                    endpoint_list.extend(value)
                else:
                    endpoint_list.append(value)
        else:
            endpoint_list = endpoints if isinstance(endpoints, list) else []
        
        # Group by node type
        by_node = {}
        for ep in endpoint_list:
            node = ep.get('node_type') or ep.get('node') or 'Unknown'
            provider = ep.get('provider') or 'Unknown'
            url = ep.get('endpoint') or ep.get('url') or 'N/A'
            gpu_tier = ep.get('gpu_tier', '')
            
            if node not in by_node:
                by_node[node] = []
            by_node[node].append({
                'provider': provider,
                'url': url,
                'gpu_tier': gpu_tier
            })
        
        # Format output
        for node, providers in sorted(by_node.items()):
            share_text += f"{node}:\n"
            for p in providers:
                gpu_str = f" ({p['gpu_tier'].upper()})" if p['gpu_tier'] else ""
                share_text += f"  • {p['provider']}{gpu_str}: {p['url']}\n"
            share_text += "\n"
        
        # Copy to clipboard
        parent.winfo_toplevel().clipboard_clear()
        parent.winfo_toplevel().clipboard_append(share_text)
        messagebox.showinfo("Shared", "Endpoints copied to clipboard in formatted text!")
    
    def refresh_endpoints():
        """Refresh endpoint display with formatted output"""
        endpoint_text.config(state=tk.NORMAL)
        endpoint_text.delete("1.0", tk.END)
        
        endpoints = config_manager.load_endpoints()
        if not endpoints:
            endpoint_text.insert(tk.END, "No endpoints deployed yet.\n\n")
            endpoint_text.insert(tk.END, "Deploy NIM instances using the Deployment Selection tab,\n")
            endpoint_text.insert(tk.END, "then endpoint URLs will appear here.")
        else:
            # Normalize endpoints
            if isinstance(endpoints, dict):
                endpoints_list = []
                for key, value in endpoints.items():
                    if isinstance(value, list):
                        endpoints_list.extend(value)
                    else:
                        endpoints_list.append(value)
            else:
                endpoints_list = endpoints if isinstance(endpoints, list) else []
            
            # Format for display (grouped by node type)
            by_node = {}
            for ep in endpoints_list:
                node = ep.get('node_type') or ep.get('node') or 'Unknown'
                provider = ep.get('provider') or 'Unknown'
                url = ep.get('endpoint') or ep.get('url') or 'N/A'
                gpu_tier = ep.get('gpu_tier', '')
                
                if node not in by_node:
                    by_node[node] = []
                by_node[node].append({
                    'provider': provider,
                    'url': url,
                    'gpu_tier': gpu_tier
                })
            
            # Display formatted
            display_text = "Deployed NIM Endpoints\n"
            display_text += "=" * 60 + "\n\n"
            
            for node, providers in sorted(by_node.items()):
                display_text += f"📦 {node}\n"
                display_text += "-" * 60 + "\n"
                for p in providers:
                    gpu_str = f" [{p['gpu_tier'].upper()}]" if p['gpu_tier'] else ""
                    display_text += f"  {p['provider'].upper()}{gpu_str}:\n"
                    display_text += f"    {p['url']}\n"
                display_text += "\n"
            
            # Also show raw JSON in a collapsible section
            display_text += "\n" + "=" * 60 + "\n"
            display_text += "Raw JSON (for export/copy):\n"
            display_text += "=" * 60 + "\n\n"
            display_text += json.dumps(endpoints_list, indent=2)
            
            endpoint_text.insert(tk.END, display_text)
        
        endpoint_text.config(state=tk.DISABLED)
    
    ttk.Button(button_frame, text="Copy to Clipboard", 
              command=copy_endpoints).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Share Endpoints", 
              command=share_endpoints).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Export to JSON", 
              command=export_endpoints).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text="Export Artists Config", 
              command=export_artists_config).pack(side=tk.LEFT, padx=5)
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

