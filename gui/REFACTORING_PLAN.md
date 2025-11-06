# GUI Refactoring Plan

## Current State
- **File**: `gui/main_window.py`
- **Size**: ~1,204 lines
- **Structure**: Single class `BudgetGuardTechOpsGUI` with 34 methods

## Proposed Structure

### 1. `gui/main_window.py` (~150 lines)
**Purpose**: Main entry point and window management

**Responsibilities**:
- Window initialization
- Tab notebook creation
- Status bar
- Main event loop
- Coordinate between tab components

**Methods**:
- `__init__()`
- `run()`
- Status bar management

---

### 2. `gui/tabs/credentials_tab.py` (~250 lines)
**Purpose**: Credential management UI and logic

**Responsibilities**:
- Create credential input forms for all providers
- Handle credential validation
- Save/load credentials via config_manager
- File browsing for GCP JSON

**Methods**:
- `create_credential_tab(parent, config_manager, status_var)`
- `_create_provider_section()`
- `_initialize_credential_entries()`
- `_browse_file()`
- `_validate_credentials()`
- `_save_credentials()`
- `_load_credentials()`

**Dependencies**:
- `config_manager` (passed in)
- `status_var` (for status updates)

---

### 3. `gui/tabs/deployment_tab.py` (~400 lines)
**Purpose**: Deployment selection UI (table creation, GPU tier selection)

**Responsibilities**:
- Create deployment checkbox table
- GPU tier radio button UI
- Local-only mode toggle UI
- Table rendering (normal vs local-only)

**Methods**:
- `create_deployment_tab(parent, config_manager, status_var, deployment_state)`
- `_create_deployment_table()`
- `_create_normal_table()`
- `_create_local_only_table()`
- `_toggle_local_only_mode()`
- `_setup_gpu_tier_selector()`

**Returns**:
- References to checkbox widgets
- Deployment state object (shared with state manager)

---

### 4. `gui/tabs/deployment_state.py` (~200 lines)
**Purpose**: State management for deployment checkboxes

**Responsibilities**:
- Save/restore checkbox state per GPU tier
- Handle GPU tier changes
- Track checkbox changes
- Update selected count

**Methods**:
- `DeploymentStateManager` class
  - `save_state_for_gpu_tier(gpu_tier)`
  - `restore_state_for_gpu_tier(gpu_tier)`
  - `on_checkbox_change(node, provider, value)`
  - `on_local_checkbox_change(node, value)`
  - `on_gpu_tier_changed(old_tier, new_tier)`
  - `update_selected_count()`
  - `get_selected_deployments()` (returns list of (node, provider, gpu_tier) tuples)

**Dependencies**:
- Checkbox widgets (from deployment_tab)
- Deployment state dict (shared)

---

### 5. `gui/tabs/deployment_actions.py` (~150 lines)
**Purpose**: Deployment execution logic

**Responsibilities**:
- Collect selected deployments
- Execute deployments in background thread
- Handle deployment results/errors
- Update UI with results

**Methods**:
- `execute_deployments(deployment_tasks, config_manager, status_var, root)`
- `_collect_selected_deployments(state_manager, deployment_checkboxes)`
- `_show_deployment_results(results, errors, root)`

**Dependencies**:
- Deployment state manager
- Deployment methods (from deployment_handlers)

---

### 6. `gui/tabs/deployment_handlers.py` (~250 lines)
**Purpose**: Provider-specific deployment methods

**Responsibilities**:
- AWS deployment with GPU tier mapping
- Azure deployment with GPU tier mapping
- GCP deployment with GPU tier mapping
- Local deployment

**Methods**:
- `deploy_to_aws(node_type, gpu_tier, config_manager)`
- `deploy_to_azure(node_type, gpu_tier, config_manager)`
- `deploy_to_gcp(node_type, gpu_tier, config_manager)`
- `deploy_to_local(node_type, config_manager)`
- `_map_gpu_tier_to_aws_instance(gpu_tier)`
- `_map_gpu_tier_to_azure_vm_size(gpu_tier)`
- `_map_gpu_tier_to_gcp_config(gpu_tier)`

**Dependencies**:
- `config_manager` (for credentials)
- Deployment modules (`aws_deployer`, `azure_deployer`, `gcp_deployer`, `local_deployer`)

---

### 7. `gui/tabs/endpoints_tab.py` (~150 lines)
**Purpose**: Endpoint viewing and export

**Responsibilities**:
- Display deployed endpoints
- Copy to clipboard
- Export to JSON
- Refresh endpoint list

**Methods**:
- `create_endpoints_tab(parent, config_manager)`
- `_refresh_endpoints()`
- `_copy_endpoints()`
- `_export_endpoints()`

**Dependencies**:
- `config_manager` (for loading endpoints)

---

## File Structure

```
gui/
├── __init__.py
├── main_window.py          (~150 lines) - Main window coordinator
└── tabs/
    ├── __init__.py
    ├── credentials_tab.py  (~250 lines) - Credential management
    ├── deployment_tab.py   (~400 lines) - Deployment UI (table, GPU selector)
    ├── deployment_state.py (~200 lines) - State management
    ├── deployment_actions.py (~150 lines) - Deployment execution
    ├── deployment_handlers.py (~250 lines) - Provider-specific deployment
    └── endpoints_tab.py     (~150 lines) - Endpoint viewing
```

**Total**: ~1,550 lines (slightly more due to imports/boilerplate, but much more organized)

---

## Benefits

1. **Separation of Concerns**: Each file has a single, clear responsibility
2. **Easier Testing**: Can test state management, deployment logic, UI separately
3. **Easier Maintenance**: Changes to credential UI don't affect deployment logic
4. **Better Readability**: Smaller files are easier to understand
5. **Reusability**: Deployment handlers could be reused in CLI mode
6. **Parallel Development**: Multiple developers can work on different tabs

---

## Migration Strategy

### Phase 1: Extract Tab Modules (Non-Breaking)
1. Create `gui/tabs/` directory
2. Extract `endpoints_tab.py` first (simplest, least dependencies)
3. Extract `credentials_tab.py` (self-contained)
4. Update `main_window.py` to import and use tab modules
5. Test that everything still works

### Phase 2: Extract Deployment Components
1. Extract `deployment_handlers.py` (pure functions, easy to test)
2. Extract `deployment_state.py` (state management logic)
3. Extract `deployment_actions.py` (execution logic)
4. Extract `deployment_tab.py` (UI only)
5. Wire everything together in `main_window.py`

### Phase 3: Cleanup
1. Remove old code from `main_window.py`
2. Add docstrings and type hints
3. Update imports throughout codebase
4. Test thoroughly

---

## Implementation Notes

### Shared State
- `deployment_state` dict: Shared between `deployment_tab.py` and `deployment_state.py`
- `status_var`: Passed to all tabs for status updates
- `config_manager`: Passed to all tabs that need it

### Callbacks
- Tab modules return callback functions that main_window can call
- Or use event-based approach with tkinter variables

### Example Integration Pattern

```python
# main_window.py
from gui.tabs import credentials_tab, deployment_tab, endpoints_tab

class BudgetGuardTechOpsGUI:
    def __init__(self, config_manager):
        # ... window setup ...
        
        # Create tabs
        credentials_frame = credentials_tab.create_credential_tab(
            self.notebook, config_manager, self.status_var
        )
        
        deployment_frame, deployment_callbacks = deployment_tab.create_deployment_tab(
            self.notebook, config_manager, self.status_var
        )
        
        endpoints_frame = endpoints_tab.create_endpoints_tab(
            self.notebook, config_manager
        )
```

---

## Estimated Effort

- **Phase 1**: 2-3 hours (extract simple tabs)
- **Phase 2**: 4-6 hours (extract deployment components, careful state management)
- **Phase 3**: 1-2 hours (cleanup, testing)
- **Total**: ~8-11 hours

---

## Risk Assessment

**Low Risk**:
- Extracting endpoints_tab (simple, isolated)
- Extracting credentials_tab (self-contained)

**Medium Risk**:
- Extracting deployment_handlers (need to ensure credential access works)
- Extracting deployment_state (complex state management)

**Higher Risk**:
- Extracting deployment_tab (many interdependencies)
- Wiring everything together (need to ensure callbacks work correctly)

**Mitigation**:
- Test after each extraction
- Keep old code commented out until verified
- Use git branches for each phase

