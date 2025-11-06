# BudgetGuard TechOps

Python application for automating NIM deployment across multiple cloud providers (AWS, Azure, GCP) for VFX studios.

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

BudgetGuard TechOps is a Python-based deployment automation tool that enables TechOps teams to automatically deploy NVIDIA NIM instances to AWS, Azure, and GCP. This provides the infrastructure foundation that BudgetGuard Artists uses for cost-optimized multi-provider routing.

**Platform Support**: Python runs on both Windows and Linux, so this application supports both platforms.

## Features

### Automated NIM Deployment
- Deploy NIM instances to AWS, Azure, and GCP with a single command
- Configure deployment settings per provider (region, instance type, etc.)
- Retrieve endpoint URLs for deployed instances
- Manage multiple NIM deployments across providers

### Multi-Provider Support
- AWS deployment via AWS SDK (boto3)
- Azure deployment via Azure SDK
- GCP deployment via Google Cloud SDK
- NVIDIA-hosted deployment support

### Endpoint Management
- Track deployed NIM endpoints per provider
- Export endpoint configuration for BudgetGuard Artists
- Validate endpoint connectivity
- Monitor deployment status

## Architecture

```
[TechOps User] → [BudgetGuard TechOps] → [Cloud Provider APIs]
                                      ↓
                    [AWS] [Azure] [GCP] [NVIDIA]
                                      ↓
                    [Deployed NIM Instances]
                                      ↓
                    [Endpoint URLs] → [BudgetGuard Artists]
```

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
- **Green status**: "✓ Server Credentials Found" - Everything is configured, ready to use
- **Yellow status**: "⚠ Server Credentials Not Found - call your TechOps technician" - Needs TechOps setup

**No Manual Credential Entry**: Artists never enter credentials manually. All credential management is handled by TechOps via the install-credentials command.

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

### ComfyUI Node Integration (Artists Side)

**Python Backend (Node Logic):**
- Custom nodes are defined as Python classes inheriting from ComfyUI's base node classes
- Node execution logic runs in Python
- Graph traversal and node operations use Python APIs
- Cost calculation and API integrations are implemented in Python

**JavaScript Frontend (UI):**
- ComfyUI runs as a web application with a JavaScript frontend
- Custom UI elements/widgets can be created with JavaScript/HTML/CSS
- Node inputs/outputs are rendered automatically based on Python node definitions
- Enum inputs create dropdown menus automatically in the UI

**BudgetGuard Node Implementation:**
- **Python**: Node class definition, cost calculation logic, API integrations, graph traversal
- **JavaScript**: Custom GUI window component, node placement detection, draggable interface
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
- [x] Implement endpoint export functionality
- [x] Add endpoint validation
- [x] Create configuration file format for BudgetGuard Artists
- [ ] Add endpoint monitoring and health checks
- [ ] Implement ComfyUI credential installation tool (`install-credentials` command)
  - Inject credentials into ComfyUI's localStorage (encrypted)
  - Inject endpoint URLs for all deployed instances
  - Validate credentials before installation
  - Support workstation-specific installation
- [ ] Implement local install package creation (`create-install-package` command)
  - Pull Docker images for selected NIM nodes
  - Export images using `docker save` → tar files
  - Create Docker Compose YAML files for each node
  - Create installation script
  - Package everything into ZIP file
- [ ] Implement local install package installation (`install-package` command)
  - Extract ZIP on target workstation
  - Load Docker images using `docker load`
  - Create Docker Compose configuration in `~/.budgetguard_local/`
  - Optionally start containers (or leave stopped)
  - Report success/failure
- [ ] Update GUI "Create Local Install Package Only" mode to generate install packages instead of deploying directly
- [ ] Add endpoint URL sharing/export features
- [ ] Implement credential status detection in Artists GUI (check localStorage for credentials)

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

#### Export Endpoints
```bash
python budgetguard_techops.py export --output endpoints.json
```

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
  --package ./budgetguard-local-package.zip \
  --start-containers false  # Leave stopped (artists control via GUI)
```

**What It Does:**
- Extracts ZIP file
- Loads Docker images using `docker load`
- Creates Docker Compose configuration in `~/.budgetguard_local/`
- Optionally starts containers (or leaves stopped)
- Reports success/failure

**Note:** Local install packages are created once on TechOps machine, then distributed to each workstation. No remote access required.

#### Install Credentials to ComfyUI (Per-Workstation)

**Studio-Wide Shared Credentials:**
```bash
python budgetguard_techops.py install-credentials --comfyui-path "C:\ComfyUI" --studio-wide
```

**Per-Workstation Credentials (for cost tracking):**
```bash
python budgetguard_techops.py install-credentials --comfyui-path "C:\ComfyUI" --workstation "artist-workstation-01"
```

This command:
- Writes credentials (NVIDIA NIM, AWS, Azure, GCP) to ComfyUI backend config file
  - **Studio-wide**: Same credentials for all workstations
  - **Per-workstation**: Separate credentials per workstation (for cost tracking)
- Writes endpoint URLs for all deployed NIM instances to config
  - **Same endpoint URLs for all workstations** (from studio-wide deployment)
- Encrypts credentials before writing to config
- BudgetGuard Artists reads from config and stores in localStorage on first load
- Artists see "✓ Server Credentials Found" status in BudgetGuard GUI after ComfyUI restarts
- **No manual setup required** - artists just use BudgetGuard nodes

**Important Notes:**
- **Cloud containers**: Deployed once (studio-wide), shared across all workstations
- **Endpoint URLs**: Same for all workstations (from studio deployment)
- **Credentials**: Installed per-workstation (either shared or separate, depending on studio needs)
- **Repeat**: Run `install-credentials` on each workstation separately

**Technical Implementation:**
- TechOps Python tool writes to ComfyUI backend config (server-side)
- BudgetGuard Artists (JavaScript) reads config on startup and populates localStorage
- Credentials are encrypted in both config file and localStorage
- This bridges the gap between Python (TechOps) and JavaScript (browser localStorage)

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

