# Local Deployment Architecture

## Problem Statement

The BudgetGuard TechOps GUI may run on a TechOps workstation, not directly on each artist workstation. However, "local" deployments need to create Docker containers on each artist's workstation (localhost).

## Current Approach vs. Proposed Solution

### Current Approach (Not Suitable for Remote Deployment)
- TechOps GUI calls `LocalDeployer.deploy_nim_instance()`
- This pulls Docker images and creates containers on the **same machine** where the GUI is running
- **Problem**: If GUI runs on TechOps machine, containers would be created there, not on artist workstations

### Proposed Solution: Install Package Approach

Instead of deploying locally from the TechOps GUI, we should:

1. **Create Local Deployment Package** on TechOps machine:
   - Export Docker images (using `docker save`)
   - Create Docker Compose configuration files
   - Package images + configs into a ZIP file
   - Include installation scripts

2. **Install Package Contents**:
   - Docker images (as tar files)
   - Docker Compose YAML files
   - Installation script (loads images, creates containers)
   - Credentials (already handled by install-credentials)
   - Endpoint URLs (already handled)

3. **Installation Workflow**:
   - TechOps runs: `python budgetguard_techops.py create-install-package --nodes "FLUX Dev,FLUX Canny" --output ./install-package.zip`
   - TechOps copies ZIP to each workstation
   - On workstation: `python budgetguard_techops.py install-package --package ./install-package.zip`
   - Script automatically:
     - Loads Docker images (`docker load`)
     - Creates Docker Compose configuration
     - Starts containers (or leaves them stopped, as configured)

## Implementation Plan

### Phase 1: Create Install Package Command
- Add `create-install-package` command to TechOps CLI
- Pull Docker images for selected NIM nodes
- Export images using `docker save` → tar files
- Create Docker Compose YAML for each node
- Create installation script
- Package everything into ZIP

### Phase 2: Install Package Command
- Add `install-package` command to TechOps CLI
- Extract ZIP on target workstation
- Load Docker images using `docker load`
- Create Docker Compose configuration
- Optionally start containers (or leave stopped)

### Phase 3: Update GUI
- Remove "Deploy Local Only" mode from GUI (or repurpose it)
- Add "Create Install Package" button/option
- Generate install package instead of deploying directly

## Benefits

- ✅ **No remote access required**: No need for SSH/RDP to artist workstations
- ✅ **Offline installation**: Package can be created once, installed on multiple workstations
- ✅ **Consistent deployment**: Same images/configs across all workstations
- ✅ **Simpler workflow**: TechOps creates package once, installs on each workstation
- ✅ **Works across networks**: No network dependencies during installation

## Local Deployment in GUI

The "Deploy Local Only" checkbox should be repurposed to:
- **"Create Local Install Package"**: Instead of deploying, generates install package
- Or kept as-is but only works when GUI is running directly on target workstation

## Docker Image Export/Import

### Export (on TechOps machine):
```bash
docker pull nvcr.io/nim/nim-flux-dev:latest
docker save nvcr.io/nim/nim-flux-dev:latest -o nim-flux-dev.tar
```

### Import (on artist workstation):
```bash
docker load -i nim-flux-dev.tar
docker-compose up -d  # or leave stopped
```

## Docker Compose Configuration

Each NIM node needs a `docker-compose.yml`:
```yaml
version: '3.8'
services:
  flux-dev:
    image: nvcr.io/nim/nim-flux-dev:latest
    ports:
      - "8001:8000"
    environment:
      - NIM_MODEL=FLUX Dev
    restart: unless-stopped
    # GPU support
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Installation Script

The install package would include a Python script that:
1. Extracts ZIP
2. Loads all Docker images
3. Creates Docker Compose configs
4. Optionally starts containers (or leaves stopped)
5. Reports success/failure

