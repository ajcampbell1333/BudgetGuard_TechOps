# BudgetGuard TechOps

Python application for automating NIM deployment across multiple cloud providers (AWS, Azure, GCP) for VFX studios. **Supports the BudgetGuard custom node in ComfyUI** by deploying and managing cloud infrastructure for multi-provider cost optimization.

## ⚠️ Pre-Alpha Disclaimer

**BudgetGuard TechOps is currently in PRE-ALPHA status and has NOT been tested in production environments.**

- This software is provided "as-is" for demonstration and development purposes
- Deployment functionality is implemented but **untested** with real cloud credentials
- Credential encryption uses placeholder/default keys (marked as TODO)
- Do NOT use in production or with real cloud accounts until further notice
- Many features are incomplete (see Development Status sections)
- Use at your own risk - no warranties or guarantees are provided

**For developers and early testers only. Do not deploy to production cloud environments.**

## Overview

BudgetGuard TechOps is a Python-based deployment automation tool that enables TechOps teams to automatically deploy NVIDIA NIM instances to AWS, Azure, and GCP. This provides the infrastructure foundation that **BudgetGuard Artists (ComfyUI custom node)** uses for cost-optimized multi-provider routing.

**Purpose**: This tool deploys and manages cloud infrastructure that the BudgetGuard node in ComfyUI connects to, enabling artists to seamlessly switch between cloud providers and optimize costs directly within their ComfyUI workflows.

**Related Project**: This is the backend deployment tool. For the ComfyUI custom node that artists use, see **[BudgetGuard Artists](https://github.com/ajcampbell1333/BudgetGuard_Artists)**.

**Platform Support**: Python runs on both Windows and Linux, so this application supports both platforms.

## Features

### ComfyUI Integration
- **Deploy infrastructure** that the BudgetGuard ComfyUI node connects to
- **Install credentials** directly into ComfyUI's backend configuration
- **Export endpoint URLs** for automatic discovery by BudgetGuard nodes
- **Studio-wide deployment** with per-workstation credential installation
- Seamless integration with ComfyUI workflows - artists never see deployment complexity

### Automated NIM Deployment
- Deploy NIM instances to AWS, Azure, and GCP with a single command
- Configure deployment settings per provider (region, instance type, GPU tier, etc.)
- Retrieve endpoint URLs for deployed instances
- Manage multiple NIM deployments across providers
- **All deployments are accessible to BudgetGuard nodes in ComfyUI**

### Multi-Provider Support
- AWS deployment via AWS SDK (boto3)
- Azure deployment via Azure SDK
- GCP deployment via Google Cloud SDK
- NVIDIA-hosted deployment support
- **Multi-provider deployments enable cost comparison in ComfyUI**

### Endpoint Management
- Track deployed NIM endpoints per provider
- Export endpoint configuration for [BudgetGuard Artists](https://github.com/ajcampbell1333/BudgetGuard_Artists) (ComfyUI)
- Validate endpoint connectivity
- Monitor deployment status
- **Automatic endpoint discovery by BudgetGuard ComfyUI nodes**

## Architecture

```
[TechOps User] → [BudgetGuard TechOps] → [Cloud Provider APIs]
                                      ↓
                    [AWS] [Azure] [GCP] [NVIDIA]
                                      ↓
                    [Deployed NIM Instances]
                                      ↓
                    [Endpoint URLs] → [ComfyUI Backend Config]
                                      ↓
                    [BudgetGuard ComfyUI Node] → [Artist Workflows]
```

**Integration Flow:**
1. **TechOps** uses BudgetGuard TechOps to deploy NIM instances to cloud providers
2. **Endpoints** are saved and exported to ComfyUI backend configuration
3. **Credentials** are installed into ComfyUI's backend config (encrypted)
4. **Artists** use BudgetGuard custom node in ComfyUI to access deployed instances
5. **BudgetGuard node** automatically discovers endpoints and routes requests to selected providers

## Technical Implementation

### Python Environment
- **Python 3.8+** required
- Cross-platform: Windows and Linux support
- Uses cloud provider SDKs for deployment automation

### Cloud Provider Integration

#### AWS Deployment
- Uses AWS SDK (boto3)
- **GPU Workloads**: Deploys NIM via AWS ECS on EC2 with GPU instances (p3, p4, g4dn, g5)
- **CPU Workloads**: Can use ECS Fargate or App Runner (no GPU support)
- Requires AWS credentials (Access Keys, IAM role, or credentials file)
- Configurable regions and instance types
- **Cost Tracking**: CloudWatch Metrics (real-time) + Cost Explorer API (billing)

#### Azure Deployment
- Uses Azure SDK for Python
- **GPU Workloads**: Deploys NIM via AKS (Azure Kubernetes Service) with GPU node pools (NC-series, ND-series)
- **CPU Workloads**: Can use Container Apps or Container Instances (no GPU support)
- Requires Azure credentials (Service Principal, Managed Identity, or Azure CLI)
- Configurable regions and instance types
- **Cost Tracking**: Azure Monitor Metrics (real-time) + Cost Management API (billing)

#### GCP Deployment
- Uses Google Cloud SDK
- **GPU Workloads**: Deploys NIM via GKE (Google Kubernetes Engine) with GPU node pools (T4, A100, etc.)
- **CPU Workloads**: Can use Cloud Run (no GPU support)
- Requires GCP credentials (Service Account JSON, Application Default Credentials)
- Configurable regions and instance types
- **Cost Tracking**: Cloud Monitoring API (real-time) + Cloud Billing API (billing)

### Deployment Workflow

**Important**: BudgetGuard TechOps is a **studio-wide deployment tool**, not a per-workstation tool. See [Architecture: Studio-Wide vs Per-Workstation](../Research/TechOps/ARCHITECTURE_STUDIO_VS_WORKSTATION.md) for details.

#### Initial Studio Setup (One-Time per Studio)

1. **Credential Creation**: TechOps creates credentials for cloud deployment:
   - NVIDIA NIM (NVIDIA API key / NGC API key) - for deploying NIM containers
   - AWS (Access Keys or IAM role) - for AWS deployment
   - Azure (Service Principal) - for Azure deployment
   - GCP (Service Account JSON) - for GCP deployment
   - These credentials are stored securely by TechOps (for deployment only)

2. **GUI Deployment Tool**: TechOps runs the BudgetGuard TechOps GUI application

3. **Node Selection**: GUI displays a checkbox table:
   - **Rows**: Available NIM nodes (FLUX Dev, FLUX Canny, FLUX Depth, FLUX Kontext, etc.)
   - **Columns**: Cloud providers (AWS, Azure, GCP)
   - **Options**:
     - "Deploy All to All" - Quick toggle to deploy every node to every provider
     - Individual checkboxes - Select specific nodes for specific providers
     - "Toggle All Off" then select specific deployments
     - Visual indicators show which deployments are already active

4. **Deployment Execution**: 
   - TechOps clicks "Deploy" button
   - Python code deploys one NIM image per selected node per selected provider
   - **Result**: Cloud containers are deployed **once** and **shared across all workstations**
   - Progress indicators show deployment status for each deployment
   - Deployment may take several minutes per instance

5. **Endpoint Output**: 
   - GUI displays endpoint URLs for all successfully deployed instances
   - Format: Organized by provider, then by node type
   - **These endpoint URLs are the same for all workstations**
   - Example output:
     ```
     AWS Deployments:
       FLUX Dev: https://nim-flux-dev-xyz.us-east-1.aws.nim.api.nvidia.com
       FLUX Canny: https://nim-flux-canny-abc.us-east-1.aws.nim.api.nvidia.com
     
     Azure Deployments:
       FLUX Dev: https://nim-flux-dev-xyz.eastus.azure.nim.api.nvidia.com
       ...
     ```

6. **Export for Artists**: 
   - TechOps can export endpoint configuration to a file
   - Endpoint URLs are **NOT encrypted** - they're public endpoints (like API URLs)
   - Endpoint URLs can be safely shared with all artists (same URLs for all workstations)
   - **Credentials are NOT exported** - those are installed separately per-workstation

#### Per-Workstation Credential Installation

**TechOps Installs Credentials (Repeated for Each Workstation)**

**Two Models Supported:**

1. **Studio-Wide Shared Credentials** (Recommended for Small Studios):
   - One set of credentials for all workstations
   - Same credentials installed to each workstation
   - Simpler management, but no per-workstation cost tracking
   - Use: `install-credentials --studio-wide`

2. **Per-Workstation Credentials** (Recommended for Large Studios):
   - Separate credentials for each workstation
   - Each workstation has its own IAM user/Service Principal
   - Enables per-workstation cost tracking
   - Use: `install-credentials --workstation <workstation-id>`

**Installation Process:**
- TechOps runs `install-credentials` command on each workstation
- Provides credentials (studio-wide OR per-workstation)
- Provides endpoint URLs (from studio deployment - **same for all workstations**)
- Credentials + endpoints written to ComfyUI backend config file
- BudgetGuard Artists (JavaScript) reads from config and stores in localStorage on startup
- Credentials are encrypted in both config file and localStorage
- Artists never see credential input fields - they only see a status message

**What Artists See:**
- **Green status**: "✓ Server Credentials Found" - Everything is configured, ready to use in ComfyUI
- **Yellow status**: "⚠ Server Credentials Not Found - call your TechOps technician" - Needs TechOps setup

**No Manual Credential Entry**: Artists never enter credentials manually in ComfyUI. All credential management is handled by TechOps via the `install-credentials` command, which writes directly to ComfyUI's backend configuration.

**Security**: 
- Credentials are encrypted in ComfyUI backend config file
- Credentials are encrypted in localStorage after being read from config
- Artists have no access to raw credentials
- All credential management is centralized through TechOps

**Key Point**: Cloud containers are deployed **once** (studio-wide), but credentials are installed **per-workstation** (either shared or separate credentials, depending on studio needs).

### Deployment GUI

The BudgetGuard TechOps GUI provides:

**Credential Management Tab**:
- Input fields for NVIDIA, AWS, Azure, GCP credentials
- Credential validation before deployment
- Secure credential storage (encrypted local storage)

**Deployment Selection Tab**:
- Checkbox table showing:
  - **Rows**: Available NIM nodes (FLUX Dev, FLUX Canny, FLUX Depth, FLUX Kontext, SDXL, Llama 3, etc.)
  - **Columns**: Cloud providers (AWS, Azure, GCP, NVIDIA-hosted)
- Quick action buttons:
  - "Select All" - Check all nodes for all providers
  - "Deselect All" - Uncheck everything
  - "Select All for [Provider]" - Select all nodes for a specific provider
  - "Select [Node] for All" - Select a specific node for all providers
- Visual indicators:
  - Green checkmark = Already deployed
  - Yellow circle = Pending deployment
  - Red X = Deployment failed
  - Gray = Not selected

**Deployment Tab**:
- "Deploy Selected" button - Starts deployment process
- Progress indicators for each deployment
- Real-time status updates
- Deployment logs

**Endpoint Output Tab**:
- Displays all endpoint URLs after successful deployment
- Copy-to-clipboard functionality
- Export to JSON file option
- Format suitable for sharing with artists

### Endpoint Export Format

TechOps exports endpoint configuration in a format that BudgetGuard Artists can import:

```json
{
  "aws": {
    "endpoint": "https://nim-xyz.us-east-1.aws.nim.api.nvidia.com",
    "region": "us-east-1",
    "deployed_at": "2024-01-01T00:00:00Z"
  },
  "azure": {
    "endpoint": "https://nim-xyz.eastus.azure.nim.api.nvidia.com",
    "region": "eastus",
    "deployed_at": "2024-01-01T00:00:00Z"
  },
  "gcp": {
    "endpoint": "https://nim-xyz.us-central1.gcp.nim.api.nvidia.com",
    "region": "us-central1",
    "deployed_at": "2024-01-01T00:00:00Z"
  },
  "nvidia": {
    "endpoint": "https://nim-xyz.ngc.nvidia.com",
    "deployed_at": "2024-01-01T00:00:00Z"
  }
}
```

## Technical Implementation Details

### ComfyUI Integration (BudgetGuard Node)

**BudgetGuard ComfyUI Node Architecture:**

**Python Backend (Node Logic):**
- BudgetGuard is a ComfyUI custom node (Python class inheriting from ComfyUI's base node classes)
- Node execution logic runs in Python within ComfyUI's execution engine
- Graph traversal and node operations use ComfyUI's Python APIs
- Cost calculation and API integrations are implemented in Python
- **Reads credentials from ComfyUI backend config file** (`ComfyUI/budgetguard/budgetguard_backend_config.json`)
- **Routes requests to endpoints deployed by BudgetGuard TechOps**

**JavaScript Frontend (UI):**
- ComfyUI runs as a web application with a JavaScript frontend
- BudgetGuard GUI is a JavaScript extension that integrates with ComfyUI's UI
- Custom draggable control panel appears when BudgetGuard nodes are in the graph
- Node inputs/outputs are rendered automatically by ComfyUI based on Python node definitions
- Provider and GPU tier dropdowns are created automatically from Python enum inputs

**Integration Points:**
- **TechOps → ComfyUI**: Credentials and endpoints written to ComfyUI backend config
- **ComfyUI → BudgetGuard Node**: Node reads config on startup
- **BudgetGuard Node → Cloud**: Routes requests to deployed endpoints based on provider selection
- **Communication**: WebSocket or ComfyUI's built-in message passing between frontend and backend

**Artists GUI (BudgetGuard Control Panel):**
- **Expanded GUI Contents**:
  - Title: "BudgetGuard Settings"
  - Two-pole radio button toggle:
    - Left option: **MANUAL** - Each node's provider dropdown is user-controlled
    - Right option: **LOWEST PRICE** - All nodes automatically switch to lowest-cost provider
  - **Credential Status Display** (no input fields):
    - **Green status**: "✓ Server Credentials Found" - Credentials installed, ready to use
    - **Yellow status**: "⚠ Server Credentials Not Found - call your TechOps technician" - Needs setup
    - Status is automatically detected from localStorage
    - No credential input fields - all handled by TechOps
- **GUI Disabled State**: 
  - If credentials not found: Mode toggle and controls disabled
  - Nodes still function as passthrough
  - Clear messaging about contacting TechOps

### State Management & Persistence

**Client-Side State (Artists):**
- All state stored client-side using browser localStorage API
- localStorage availability: ComfyUI runs as a web application, so JavaScript has full access to `window.localStorage`
- Manual selections: Per-node provider choices saved to localStorage
- Global mode: Current mode (MANUAL/LOWEST PRICE) saved to localStorage
- Critical save point: When switching MANUAL → LOWEST PRICE, manual selections are immediately saved to localStorage before applying lowest-cost providers

**State Restoration on Graph Load:**
- When a ComfyUI workflow/graph is loaded:
  1. Detect all BudgetGuard nodes in the loaded graph
  2. Restore global mode (MANUAL/LOWEST PRICE) from localStorage (default to MANUAL if not found)
  3. Restore saved manual selections from localStorage for each node
  4. Apply state based on restored mode
  5. Update GUI radio button to reflect restored mode
  6. Handle missing state: New nodes default to MANUAL mode with a default provider selection

### Authentication & Credential Management

**Credential Storage:**
- Credentials are installed by TechOps via `install-credentials` command
- TechOps writes credentials to ComfyUI backend config file (encrypted)
- BudgetGuard Artists reads from config and stores in localStorage on startup (encrypted)
- Artists never see credential input fields
- Artists only see status message: "✓ Server Credentials Found" or "⚠ Server Credentials Not Found"
- Status is detected by checking localStorage for credential presence
- **Security Best Practices**: Never store credentials in workflow JSON files, encrypt at rest, use least-privilege IAM roles

**Authentication Per Provider:**
- **AWS**: Access Key ID, Secret Access Key, or IAM role
- **Azure**: Service Principal (Application ID, Tenant ID, Client Secret) or Managed Identity
- **GCP**: Service Account JSON key file or Application Default Credentials (ADC)
- **NVIDIA NIM**: NVIDIA API Key (NGC API key)

### Cost Calculation Logic

1. **Node Analysis**: Inspect the downstream NIM node configuration
   - Model type (FLUX Dev, FLUX Canny, FLUX Depth, FLUX Kontext, SDXL, Llama 3, etc.)
   - Input parameters (image dimensions, text length, steps, CFG scale, etc.)
   - Expected compute requirements (based on model type and parameters)

2. **API Queries**: Query pricing APIs from each provider
   - AWS: AWS Pricing API / Cost Explorer API
   - Azure: Azure Pricing Calculator API / Consumption API
   - GCP: Cloud Billing API / Pricing API
   - NVIDIA NIM: NIM API pricing endpoints

3. **Cost Estimation**: Calculate estimated cost based on:
   - Compute time (GPU hours)
   - Token usage (for LLM nodes)
   - API call overhead
   - Data transfer costs

## Development Plan

### Phase 1: Core Infrastructure & GUI ✅ COMPLETED
- [x] Create Python application structure
- [x] Implement GUI framework (tkinter - Windows/Linux compatible)
- [x] Create credential management tab in GUI
- [x] Implement configuration management
- [x] Add credential management (AWS, Azure, GCP, NVIDIA)
- [x] Support Windows and Linux platforms
- [x] Add logging and error handling
- [x] Implement secure credential storage (encrypted)
- [x] Create deployment selection tab with checkbox table
- [x] Create endpoints viewing/export tab

**Status**: Phase 1 is complete and ready for testing. Run `python budgetguard_techops.py gui` to launch the application.

### Phase 2: AWS Deployment ✅ COMPLETED
- [x] Integrate AWS SDK (boto3)
- [x] Implement AWS NIM deployment automation
- [x] Add endpoint retrieval for AWS deployments
- [x] Add deployment status monitoring
- [x] Integrate AWS deployer into GUI
- [x] Add background deployment execution
- [x] Add deployment status checking UI

**Status**: Phase 2 is complete. AWS deployment is fully functional. The application can deploy NIM instances to AWS ECS, retrieve endpoints, and monitor deployment status.

**⚠️ GPU Migration Required**: Current implementation uses basic ECS (may not support GPUs). **GPU workloads require ECS on EC2 with GPU instances**. See [Phase 2.5 GPU Migration Plan](../Research/TechOps/PHASE_2_3_GPU_MIGRATION.md).

**Next**: Phase 2.5 - Migrate AWS deployment to ECS on EC2 with GPU instances.

### Phase 3: Azure Deployment ✅ COMPLETED
- [x] Integrate Azure SDK
- [x] Implement Azure NIM deployment automation
- [x] Add endpoint retrieval for Azure deployments
- [x] Add deployment status monitoring
- [x] Integrate Azure deployer into GUI
- [x] Add Azure credential management (Subscription ID, Tenant ID, Client ID/Secret, Resource Group, Region)

**Status**: Phase 3 is complete. Azure deployment is fully functional. The application can deploy NIM instances to Azure Container Instances, retrieve endpoints, and monitor deployment status.

**⚠️ GPU Migration Required**: Current implementation uses Azure Container Instances (ACI), which **does NOT support GPUs**. **GPU workloads require AKS (Azure Kubernetes Service) with GPU node pools**. See [Phase 3.5 GPU Migration Plan](../Research/TechOps/PHASE_2_3_GPU_MIGRATION.md).

**Next**: Phase 3.5 - Migrate Azure deployment to AKS with GPU node pools.

### Phase 2.5: AWS GPU Migration ✅ COMPLETED
- [x] Migrate AWS deployment from generic ECS to ECS on EC2 with GPU instances
- [x] Create EC2 Auto Scaling Group with GPU instances (g4dn.xlarge default)
- [x] Configure ECS cluster with EC2 launch type and GPU support
- [x] Add GPU resource requirements to ECS task definitions
- [x] Configure ECS-optimized AMI with GPU support
- [x] Add EC2 instance management (start/stop for scale-to-zero)
- [x] Update endpoint retrieval for EC2-based deployments
- [ ] Test GPU-enabled NIM container deployment (requires AWS credentials)

**Status**: ✅ **Code Complete** - AWS deployment now uses ECS on EC2 with GPU instances (g4dn.xlarge). Ready for testing with AWS credentials.

**Key Changes**:
- Switched from Fargate to EC2 launch type
- Added Auto Scaling Group with GPU instances (g4dn.xlarge)
- Configured task definitions with GPU resource requirements
- Updated endpoint retrieval for EC2 instances
- Added IAM role creation for ECS instances

### Phase 3.5: Azure GPU Migration ✅ COMPLETED
- [x] Migrate Azure deployment from Container Instances to AKS with GPU node pools
- [x] Create AKS cluster with GPU node pool (NC-series, ND-series)
- [x] Configure Kubernetes deployment for NIM containers with GPU resources
- [ ] Install NVIDIA device plugin on AKS cluster (requires cluster access - manual step)
- [x] Update endpoint retrieval for AKS services (LoadBalancer)
- [x] Add node pool scaling for manual scale-to-zero
- [ ] Test GPU-enabled NIM container deployment (requires Azure credentials)
- [x] See [Phase 3.5 GPU Migration Plan](../Research/TechOps/PHASE_2_3_GPU_MIGRATION.md) for details

**Status**: ✅ **Code Complete** - Azure deployment now uses AKS with GPU node pools (NC6s_v3 default). Ready for testing with Azure credentials.

**Key Changes**:
- Switched from Container Instances to AKS (Kubernetes)
- Added GPU node pool with configurable VM sizes (NC6s_v3, NC24s_v3, ND96asr_v4)
- Configured Kubernetes deployments with GPU resource requirements (`nvidia.com/gpu`)
- Updated endpoint retrieval for LoadBalancer services
- Implemented start/stop via deployment replica scaling
- Added GPU tier mapping (T4 -> NC6s_v3, A10G -> NC24s_v3, A100 -> ND96asr_v4)

**Note**: NVIDIA device plugin installation is typically handled automatically by AKS for GPU node pools, but may require manual verification. See [NVIDIA Device Plugin Verification Guide](../Research/TechOps/NVIDIA_DEVICE_PLUGIN_VERIFICATION.md) for details on what this means for TechOps devs and artists.

### Phase 4: GCP Deployment ✅ COMPLETED
- [x] Integrate Google Cloud SDK
- [x] Implement GCP NIM deployment automation using **GKE with GPU node pools** (from the start)
- [x] Add endpoint retrieval for GCP deployments
- [x] Add deployment status monitoring
- [x] Configure GPU node pools (T4, A10G, A100) for NIM containers
- [ ] Test GPU-enabled NIM container deployment (requires GCP credentials)

**Status**: ✅ **Code Complete** - GCP deployment now uses GKE with GPU node pools (n1-standard-4 + nvidia-tesla-t4 default). Ready for testing with GCP credentials.

**Key Changes**:
- Implemented GKE cluster creation with GPU node pools from the start
- Added GPU node pool with configurable machine types (n1-standard-4, a2-highgpu-1g, a2-highgpu-4g)
- Configured Kubernetes deployments with GPU resource requirements (`nvidia.com/gpu`)
- Updated endpoint retrieval for LoadBalancer services
- Implemented start/stop via deployment replica scaling
- Added GPU tier mapping (T4 -> n1-standard-4 + nvidia-tesla-t4, A10G -> a2-highgpu-1g + nvidia-a10, A100 -> a2-highgpu-4g + nvidia-a100)

**Note**: GKE automatically handles NVIDIA device plugin installation for GPU node pools, so no manual verification is needed (unlike Azure AKS).

### Phase 5: Endpoint Management & Artist Handoff (In Progress)
- [x] Implement endpoint export functionality (`export.py` - supports `--config` and `--credentials`)
- [x] Add endpoint validation (`validate_endpoints.py`)
- [x] Create configuration file format for BudgetGuard Artists (`ARTISTS_CONFIG_FORMAT.md`)
- [ ] Add endpoint monitoring and health checks (enhanced validation with health checks)
- [x] Implement ComfyUI credential installation tool (`install-credentials` command) ✅ COMPLETE
  - [x] Inject endpoint URLs for all deployed instances
  - [x] Validate credentials before installation
  - [x] Support workstation-specific installation (`--workstation` flag)
  - [x] Support studio-wide installation (`--studio-wide` flag)
  - [x] Support file-based input (`--endpoints` and `--credentials` files)
  - [x] Support ConfigManager input (`--from-config-manager` for TechOps machine)
  - [x] Non-interactive mode for automation (`--non-interactive`)
  - [x] **✅ COMPLETE**: Implement proper credential encryption using Fernet (studio-wide key)
    - Uses PBKDF2 key derivation with fixed salt for studio-wide compatibility
    - Supports custom studio key via `--studio-key` argument
    - All workstations use same key to decrypt (default key for development, custom for production)
  - **Note**: Credentials are written to ComfyUI backend config file (not localStorage - that's Artists' responsibility)
- [x] Implement local install package creation (`create-install-package` command) ✅ COMPLETE
  - [x] Pull Docker images for selected NIM nodes
  - [x] Export images using `docker save` → tar files
  - [x] Create Docker Compose YAML files for each node
  - [x] Create installation script (`install.py`) for loading images and starting containers
  - [x] Package everything into ZIP file (images, compose files, install script, manifest, README)
  - **Usage**: `python budgetguard_techops.py create-install-package --nodes "FLUX Dev,FLUX Canny" --output ./install-package.zip`
- [x] Implement local install package installation (`install-package` command) ✅ COMPLETE
  - [x] Extract ZIP on target workstation
  - [x] Load Docker images using `docker load` (via install.py script)
  - [x] Create Docker Compose configuration in `~/.budgetguard_local/`
  - [x] Containers always left stopped (artists control via GUI)
  - [x] Report success/failure
  - **Usage**: `python budgetguard_techops.py install-package --package ./install-package.zip`
- [x] Update GUI "Create Local Install Package Only" mode to generate install packages instead of deploying directly ✅ COMPLETE
  - [x] GUI now calls `create-install-package` command when "Create Local Install Package Only" is checked
  - [x] Prompts user for output ZIP file location
  - [x] Creates install package in background thread
  - [x] Shows success message with installation instructions
- [x] Add endpoint URL sharing/export features ✅ COMPLETE
  - [x] Enhanced endpoint display with formatted grouping by node type
  - [x] "Share Endpoints" button - copies formatted endpoints to clipboard
  - [x] "Export Artists Config" button - exports in BudgetGuard Artists config format
  - [x] Improved endpoint display showing provider, GPU tier, and URLs
  - [x] Raw JSON display for technical users
- [ ] **TechOps Tool**: Add workstation credential audit tool (`check-credentials` or `audit-workstations` command)
  - Check which workstations have credentials installed (ping remote workstations)
  - Verify credential validity on remote workstations
  - **Check what local NIM nodes are currently installed** on each workstation (from local install packages)
  - Report installation status across all workstations (credentials + local nodes)
  - Generate audit report showing:
    - Workstation ID
    - Credential installation status (installed/not installed)
    - Local node installations (which NIM nodes are installed locally)
    - Local container status (running/stopped) if applicable
  - Useful for TechOps to track deployment progress and troubleshoot issues

### Phase 6: Multi-Provider Deployment
- [ ] Implement batch deployment across all providers
- [ ] Add parallel deployment support
- [ ] Add deployment failure handling and retry logic
- [ ] Create deployment dashboard/reporting

## API Integration Requirements

### AWS
- AWS SDK for Python (boto3)
- **ECS on EC2 APIs** for GPU container deployment (p3, p4, g4dn, g5 instances)
- AWS EC2 APIs for GPU instance management
- **CloudWatch Metrics API** for real-time usage tracking
- **Cost Explorer API** for cost data (~24hr delay)
- AWS Pricing API for cost estimation

### Azure
- Azure SDK for Python
- **AKS (Azure Kubernetes Service) API** for GPU container deployment (NC-series, ND-series)
- Azure Monitor Metrics API for real-time usage tracking
- **Cost Management API** for cost data (~24hr delay)
- Azure Pricing Calculator API

### GCP
- Google Cloud SDK
- **GKE (Google Kubernetes Engine) API** for GPU container deployment (T4, A100, etc.)
- Cloud Monitoring API for real-time usage tracking
- **Cloud Billing API** for cost data (~24hr delay)
- Cloud Billing Export for detailed usage data

### NVIDIA
- NVIDIA NGC API for NIM deployment
- NVIDIA Cloud deployment tools integration
- NIM API for instance management

## Installation

### Prerequisites
- Python 3.8 or higher
- Cloud provider accounts (AWS, Azure, GCP) with appropriate permissions
- NVIDIA account with NIM deployment access
- **For Azure**: Azure CLI installed (`az`) for AKS cluster access (needed for GPU verification)
- **For Azure**: kubectl installed for Kubernetes cluster management

### Setup

**Windows:**
```powershell
cd BudgetGuard_TechOps
python -m pip install -r requirements.txt
```

**Linux:**
```bash
cd BudgetGuard_TechOps
pip install -r requirements.txt
```

**Or install as package:**
```bash
cd BudgetGuard_TechOps
pip install -e .
```

### Running the Application

**Launch GUI:**
```bash
python budgetguard_techops.py gui
```

Or simply:
```bash
python budgetguard_techops.py
```

The GUI will open with three tabs:
- **Credentials**: Manage authentication credentials for all providers
- **Deployment Selection**: Select nodes and providers for deployment (checkbox table)
- **Endpoints**: View and export deployed endpoint URLs

### First Time Setup

1. Run the application: `python budgetguard_techops.py gui`
2. Go to **Credentials** tab
3. Enter credentials for:
   - NVIDIA NIM (required)
   - At least one cloud provider: AWS, Azure, or GCP (required)
4. Click "Validate Credentials" to test
5. Click "Save Credentials" to store (encrypted)
6. **For Azure deployments**: Verify NVIDIA device plugin after first AKS cluster creation (see [Azure AKS GPU Setup](#azure-aks-gpu-setup) below)
7. Go to **Deployment Selection** tab to deploy NIM instances

## Azure AKS GPU Setup

**Important for Azure deployments**: After creating your first AKS cluster with GPU node pools, you need to verify that the NVIDIA device plugin is working. This is a **one-time check per cluster**.

### Quick Verification (5 minutes)

After deploying your first NIM node to Azure through the GUI:

1. **Connect to your AKS cluster**:
   ```bash
   az aks get-credentials --resource-group budgetguard-nim-rg --name budgetguard-nim-aks
   ```

2. **Check if device plugin is running**:
   ```bash
   kubectl get daemonset -n kube-system | grep nvidia
   ```
   
   Should show: `nvidia-device-plugin` with `READY: 1/1`

3. **Verify GPUs are visible**:
   ```bash
   kubectl get nodes -o json | jq '.items[] | {name: .metadata.name, gpus: .status.capacity."nvidia.com/gpu"}'
   ```
   
   GPU nodes should show `"gpus": "1"` or higher.

### If Verification Fails

If the device plugin isn't running, install it manually:

```bash
helm repo add nvdp https://nvidia.github.io/k8s-device-plugin
helm repo update
helm install nvidia-device-plugin nvdp/nvidia-device-plugin --namespace kube-system
```

### Full Documentation

For detailed verification steps, troubleshooting, and what this means for artists, see:
- **[NVIDIA Device Plugin Verification Guide](../Research/TechOps/NVIDIA_DEVICE_PLUGIN_VERIFICATION.md)** - Complete guide with all verification methods

**Note**: This is only needed for Azure AKS deployments. AWS ECS on EC2 and GCP GKE handle GPU access automatically.

## Usage

### GUI Mode (Recommended)
```bash
python budgetguard_techops.py gui
```
Opens the graphical interface for:
- Credential management
- Node/provider selection via checkbox table
- Deployment execution
- Endpoint viewing and export

### Command Line Mode

#### Create Credentials Programmatically (RECOMMENDED for Multiple Workstations)
```bash
# Create credentials for multiple workstations
python budgetguard_techops.py create-credentials \
  --workstations "ws-01,ws-02,ws-03,ws-04,ws-05" \
  --providers aws,azure,gcp \
  --output-dir ./credentials

# Create studio-wide shared credentials
python budgetguard_techops.py create-credentials \
  --studio-wide \
  --providers aws,azure,gcp \
  --output-dir ./credentials
```

**What It Does:**
- Creates IAM users/Service Principals/Service Accounts for each workstation
- Generates access keys/secrets automatically
- Attaches cost tracking permissions
- Saves encrypted credential files (one per workstation per provider)

**Time**: ~30 seconds per workstation (vs 5-10 minutes manually)

See [Automated Credential Creation](../Research/TechOps/CREDENTIAL_CREATION.md) for details.

#### Deploy Selected Nodes
```bash
python budgetguard_techops.py deploy --nodes "FLUX Dev,FLUX Canny" --providers aws,azure --region us-east-1
```

#### Deploy All Nodes to All Providers
```bash
python budgetguard_techops.py deploy --all --all-providers
```

#### Export Endpoints and Credentials

Export files for workstation installation (see [Install Credentials](#install-credentials-to-comfyui-per-workstation---required-for-budgetguard-node) for deployment scenarios):

```bash
# Export both endpoints and credentials (for all deployment scenarios)
python tools/export.py --config --credentials --out-dir ./exports

# Export only endpoints + credential status (safe to share, no secrets)
python tools/export.py --config --out endpoints.json

# Export only credentials (contains secrets, TechOps use only)
python tools/export.py --credentials --out credentials.json
```

**Output Files:**
- `budgetguard_artists_config.json`: Endpoints + credential status (no secrets, safe to share)
- `budgetguard_credentials.json`: Actual credentials (contains secrets, keep secure)

**Use Cases:**
- **Small studios**: Export to network drive, artists copy and install
- **Mid-sized studios**: Export to local directory, TechOps copies via RDP/SSH
- **Large studios**: Export to automation tool's file server, distributed automatically

#### Create Local Install Package
```bash
# Create install package for selected nodes
python budgetguard_techops.py create-install-package \
  --nodes "FLUX Dev,FLUX Canny,FLUX Depth" \
  --output ./budgetguard-local-package.zip
```

**What It Does:**
- Pulls Docker images for selected NIM nodes
- Exports images using `docker save` → tar files
- Creates Docker Compose YAML files for each node
- Creates installation script
- Packages everything into ZIP file

**Output:**
- ZIP file containing:
  - Docker image tar files (one per node)
  - Docker Compose configuration files
  - Installation script (`install.py`)
  - README with instructions

#### Install Local Package on Workstation
```bash
# On each artist workstation
python budgetguard_techops.py install-package \
  --package ./budgetguard-local-package.zip
```

**What It Does:**
- Extracts ZIP file to temporary directory
- Runs installation script (`install.py`) from package
- Loads Docker images using `docker load`
- Creates Docker Compose configuration in `~/.budgetguard_local/`
- **Containers are always left stopped** (artists control via BudgetGuard GUI)
- Reports success/failure

**Note:** Local install packages are created once on TechOps machine, then distributed to each workstation. No remote access required.

#### Install Credentials to ComfyUI (Per-Workstation) - Required for BudgetGuard Node

BudgetGuard supports three deployment scenarios to accommodate studios of all sizes:

##### Scenario 1: Small Studios (File Share / Network Drive)

**Best for:** Studios with 1-10 workstations, simple network setup

**Workflow:**
1. **TechOps exports files** (on TechOps machine):
   ```bash
   python tools/export.py --config --credentials --out-dir ./network-share/budgetguard
   ```
   This creates:
   - `budgetguard_artists_config.json` (endpoints + credential status, safe to share)
   - `budgetguard_credentials.json` (actual credentials, keep secure)

2. **TechOps copies files to network drive** (accessible by all workstations)

3. **On each workstation** (artist or TechOps can do this):
   ```bash
   # Copy files from network drive to workstation
   # Then run installation:
   python tools/install_credentials.py \
     --comfyui-path "C:\ComfyUI" \
     --endpoints "\\network-share\budgetguard\budgetguard_artists_config.json" \
     --credentials "\\network-share\budgetguard\budgetguard_credentials.json" \
     --studio-wide
   ```

**Advantages:**
- Simple setup, no remote access needed
- Artists can install themselves if TechOps provides instructions
- Works with basic network file sharing

---

##### Scenario 2: Mid-Sized Studios (RDP/SSH Remote Access)

**Best for:** Studios with 10-50 workstations, TechOps team with remote access

**Workflow:**
1. **TechOps exports files** (on TechOps machine):
   ```bash
   python tools/export.py --config --credentials --out-dir ./exports
   ```

2. **TechOps RDPs/SSHs to each workstation**:
   - Copy exported files to workstation (via RDP file transfer, SCP, or network share)
   - Run installation command on workstation

3. **On each workstation** (via RDP/SSH):
   ```bash
   # Studio-wide shared credentials:
   python tools/install_credentials.py \
     --comfyui-path "C:\ComfyUI" \
     --endpoints exports/budgetguard_artists_config.json \
     --credentials exports/budgetguard_credentials.json \
     --studio-wide

   # OR per-workstation credentials (for cost tracking):
   python tools/install_credentials.py \
     --comfyui-path "C:\ComfyUI" \
     --endpoints exports/budgetguard_artists_config.json \
     --credentials exports/workstation-01-credentials.json \
     --workstation "workstation-01"
   ```

**Advantages:**
- Centralized control by TechOps
- Supports per-workstation credentials for cost tracking
- Standard VFX studio workflow (like MPC/Technicolor)

---

##### Scenario 3: Large Studios (Automation / Batch Deployment)

**Best for:** Studios with 50+ workstations, any automation infrastructure (custom scripts, Ansible, Puppet, Group Policy, etc.)

**How It Works:**
BudgetGuard's `install_credentials.py` is designed to be **scriptable and non-interactive**, so it works with whatever automation your studio already uses. You don't need specific tools - any system that can:
- Copy files to workstations
- Run a Python command on each workstation
- Handle batch execution

**Common Approaches in VFX Studios:**

**A. Custom Python/Bash Scripts** (Most Common)
- TechOps writes a simple script that loops through workstations
- Uses SSH (Linux) or RDP/PSExec (Windows) to run commands
- No special tools required - just Python and network access

**B. Windows Group Policy** (Windows Studios with Active Directory)
- Group Policy is a Windows Active Directory feature (not related to Microsoft Dynamics)
- Deploy batch script via Group Policy startup/login script
- Files stored on network share
- Runs automatically when workstations boot/login
- Requires Windows Server with Active Directory domain

**C. Ansible/Puppet** (If Already in Use)
- If your studio already uses these tools, BudgetGuard integrates easily
- If not, you don't need to install them - simpler scripts work fine

**D. Custom Studio Tools** (Like MPC/Technicolor)
- Many large studios have custom-built deployment systems
- BudgetGuard's command-line interface works with any system

**Workflow (Generic - Works with Any Tool):**
1. **TechOps exports files** (on TechOps machine):
   ```bash
   python tools/export.py --config --credentials --out-dir ./exports --non-interactive
   ```
   This creates:
   - `budgetguard_artists_config.json` (endpoints + credential status)
   - `budgetguard_credentials.json` (actual credentials)

2. **TechOps places files on network share** (accessible by all workstations):
   - Network file server, shared drive, or automation tool's file server

3. **TechOps creates deployment script** (using whatever tool your studio uses):
   - Script loops through list of workstations
   - For each workstation: copies files, runs `install_credentials.py`
   - Can run sequentially or in parallel (depends on your tool)

4. **TechOps runs deployment script**:
   - Executes installation on all specified workstations
   - Tool handles execution, error reporting, logging

**Example 1: Simple Python Script (Most Common)**
```python
#!/usr/bin/env python3
"""
Deploy BudgetGuard credentials to all workstations.
Works with any studio infrastructure - just needs SSH (Linux) or RDP/PSExec (Windows).
"""
import subprocess
import sys

# List of workstations (from your studio's inventory system)
WORKSTATIONS = [
    'workstation-01',
    'workstation-02',
    'workstation-03',
    # ... etc
]

NETWORK_SHARE = '\\\\fileserver\\budgetguard'
COMFYUI_PATH = 'C:\\ComfyUI'

for ws in WORKSTATIONS:
    print(f"Installing on {ws}...")
    
    # Run installation via SSH (Linux) or PSExec (Windows)
    # Adjust command based on your studio's remote execution method
    cmd = [
        'python', 'tools/install_credentials.py',
        '--comfyui-path', COMFYUI_PATH,
        '--endpoints', f'{NETWORK_SHARE}/budgetguard_artists_config.json',
        '--credentials', f'{NETWORK_SHARE}/budgetguard_credentials.json',
        '--workstation', ws,
        '--non-interactive'
    ]
    
    # Example: Using SSH (Linux workstations)
    # result = subprocess.run(['ssh', f'techops@{ws}'] + cmd, capture_output=True)
    
    # Example: Using PSExec (Windows workstations)
    # result = subprocess.run(['psexec', f'\\\\{ws}'] + cmd, capture_output=True)
    
    # Example: If workstations can access network share directly
    # result = subprocess.run(cmd, capture_output=True)
    
    print(f"  {ws}: {result.returncode == 0 and 'Success' or 'Failed'}")

print("Deployment complete!")
```

**Example 2: Windows Batch Script (Group Policy)**
```batch
@echo off
REM Deploy BudgetGuard credentials via Windows Group Policy
REM Place this script on file server, deploy via Group Policy startup/login script

set COMFYUI_PATH=C:\ComfyUI
set NETWORK_SHARE=\\fileserver\budgetguard
set ENDPOINTS=%NETWORK_SHARE%\budgetguard_artists_config.json
set CREDENTIALS=%NETWORK_SHARE%\budgetguard_credentials.json

python tools\install_credentials.py ^
  --comfyui-path "%COMFYUI_PATH%" ^
  --endpoints "%ENDPOINTS%" ^
  --credentials "%CREDENTIALS%" ^
  --workstation "%COMPUTERNAME%" ^
  --non-interactive

if %ERRORLEVEL% EQU 0 (
    echo BudgetGuard credentials installed successfully
) else (
    echo BudgetGuard installation failed
)
```

**Example 3: Bash Script (Linux Studios)**
```bash
#!/bin/bash
# Deploy BudgetGuard credentials to all Linux workstations
# Uses SSH to connect to each workstation

WORKSTATIONS=("ws-01" "ws-02" "ws-03")  # Your workstation list
NETWORK_SHARE="/mnt/fileserver/budgetguard"
COMFYUI_PATH="/opt/ComfyUI"

for ws in "${WORKSTATIONS[@]}"; do
    echo "Installing on $ws..."
    ssh "techops@$ws" python tools/install_credentials.py \
        --comfyui-path "$COMFYUI_PATH" \
        --endpoints "$NETWORK_SHARE/budgetguard_artists_config.json" \
        --credentials "$NETWORK_SHARE/budgetguard_credentials.json" \
        --workstation "$ws" \
        --non-interactive
    echo "  $ws: $([ $? -eq 0 ] && echo 'Success' || echo 'Failed')"
done
```

**Example 4: Ansible (If Your Studio Uses It)**
```yaml
# budgetguard_install.yml
- name: Install BudgetGuard credentials
  hosts: artist_workstations
  tasks:
    - name: Install credentials
      command: >
        python tools/install_credentials.py
        --comfyui-path "{{ comfyui_path }}"
        --endpoints "{{ network_share }}/budgetguard_artists_config.json"
        --credentials "{{ network_share }}/budgetguard_credentials.json"
        --workstation "{{ inventory_hostname }}"
        --non-interactive
```

**Note:** These are examples. Use whatever method your studio already uses for deploying software to workstations. BudgetGuard just needs to be able to run a Python command with file paths - it works with any deployment system.

**Advantages:**
- **Batch installation**: Install on all workstations at once (or in batches)
- **Centralized control**: One script/command deploys to hundreds of workstations
- **Consistent deployment**: Same process for all workstations
- **Scales efficiently**: No manual per-workstation work required
- **Works with existing tools**: No need to install new automation software

**Key Point:**
BudgetGuard doesn't require any specific automation tool. It's designed to work with:
- Custom Python/Bash scripts (most common in VFX)
- Windows Group Policy (Windows studios)
- Ansible/Puppet (if already in use)
- Custom studio deployment systems (like MPC/Technicolor's)
- Any system that can copy files and run Python commands

The `--non-interactive` flag ensures it works in automated environments without user prompts.

---

##### Quick Reference: Installation Command Options

**Using exported files (recommended for all scenarios):**
```bash
python tools/install_credentials.py \
  --comfyui-path "C:\ComfyUI" \
  --endpoints endpoints.json \
  --credentials credentials.json \
  --studio-wide  # OR --workstation "workstation-id"
```

**Using ConfigManager (TechOps machine only):**
```bash
python tools/install_credentials.py \
  --comfyui-path "C:\ComfyUI" \
  --from-config-manager \
  --studio-wide  # OR --workstation "workstation-id"
```

This command:
- **Writes credentials (NVIDIA NIM, AWS, Azure, GCP) to ComfyUI backend config file** (`ComfyUI/budgetguard/budgetguard_backend_config.json`)
  - **Studio-wide**: Same credentials for all workstations
  - **Per-workstation**: Separate credentials per workstation (for cost tracking)
- **Writes endpoint URLs for all deployed NIM instances to config**
  - **Same endpoint URLs for all workstations** (from studio-wide deployment)
  - **BudgetGuard ComfyUI node automatically discovers these endpoints**
- Encrypts credentials before writing to config
- **BudgetGuard ComfyUI node (Python) reads config on startup**
- BudgetGuard GUI (JavaScript) reads from config and stores in localStorage on first load
- Artists see "✓ Server Credentials Found" status in BudgetGuard GUI after ComfyUI restarts
- **No manual setup required in ComfyUI** - artists just use BudgetGuard nodes

**Important Notes:**
- **Cloud containers**: Deployed once (studio-wide), shared across all workstations
- **Endpoint URLs**: Same for all workstations (from studio deployment)
- **Credentials**: Installed per-workstation (either shared or separate, depending on studio needs)
- **Repeat**: Run `install-credentials` on each workstation separately

**Technical Implementation (ComfyUI Integration):**
- **TechOps Python tool writes to ComfyUI backend config** (`ComfyUI/budgetguard/budgetguard_backend_config.json`) - server-side
- **BudgetGuard ComfyUI node (Python) reads config on startup** - server-side (within ComfyUI)
- **BudgetGuard GUI (JavaScript) reads from localStorage** - client-side (populated from backend config)
- Credentials are encrypted in both config file and localStorage
- **Seamless integration** - BudgetGuard node automatically discovers endpoints and credentials without artist intervention

**For Small Studios Without TechOps:**
- Artists can run this command themselves
- They need to set up credentials and deploy NIM instances first
- Same tool, same workflow - just used by artists instead of TechOps team

#### List Deployments
```bash
python budgetguard_techops.py list
```

## License

(To be determined)

## Contributing

(To be added)

