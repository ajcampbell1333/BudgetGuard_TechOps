# GPU Selection UI Design for TechOps

## Overview

TechOps GUI needs to support deploying NIM nodes on multiple GPU tiers. The current checkbox grid (Nodes × Providers) needs a third dimension (GPU Tier).

## UI Structure

### Deployment Selection Tab

```
┌─────────────────────────────────────────────────────────┐
│ Deployment Selection                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ GPU Tier Selection (Radio Buttons):                     │
│  ○ T4 (Cost-Effective)   ○ A10G (Recommended) ⭐       │
│  ○ A100 (Fastest)                                        │
│                                                          │
│ [Deploy Local Only] ☐                                   │
│ (When disabled, each node chosen to deploy to a cloud   │
│ provider will automatically deploy local as well...)    │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Node          │ AWS  │ Azure │ GCP                │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ FLUX Dev      │ ☐   │ ☐    │ ☐                  │   │
│ │ FLUX Canny    │ ☐   │ ☐    │ ☐                  │   │
│ │ FLUX Depth    │ ☐   │ ☐    │ ☐                  │   │
│ │ FLUX Kontext  │ ☐   │ ☐    │ ☐                  │   │
│ │ SDXL          │ ☐   │ ☐    │ ☐                  │   │
│ │ ...           │ ... │ ...  │ ...                │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ [Select All] [Deselect All] [Deploy Selected]           │
│                                                          │
│ Info: Selected GPU tier will be used for all checked    │
│       deployments. Deploy each GPU tier separately.     │
└─────────────────────────────────────────────────────────┘
```

### When "Deploy Local Only" is Checked

```
┌─────────────────────────────────────────────────────────┐
│ Deployment Selection                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ [Deploy Local Only] ☑                                   │
│                                                          │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Node                                              │   │
│ ├──────────────────────────────────────────────────┤   │
│ │ FLUX Dev      │ ☐                               │   │
│ │ FLUX Canny    │ ☐                               │   │
│ │ FLUX Depth    │ ☐                               │   │
│ │ FLUX Kontext  │ ☐                               │   │
│ │ SDXL          │ ☐                               │   │
│ │ ...           │ ...                             │   │
│ └──────────────────────────────────────────────────┘   │
│                                                          │
│ [Select All] [Deselect All] [Deploy Selected]           │
│                                                          │
│ Note: GPU tier selector hidden (local deployment        │
│       doesn't have GPU options)                         │
└─────────────────────────────────────────────────────────┘
```

## User Workflow

### Deploying Multiple GPU Tiers

1. **Select GPU Tier**: Choose T4, A10G, or A100 (radio button)
2. **Select Nodes & Providers**: Check boxes for nodes/providers to deploy
3. **Click "Deploy"**: Deploys all checked nodes with selected GPU tier
4. **Repeat**: Select different GPU tier, select nodes/providers, deploy again

**Example**:
- Step 1: Select "A10G" → Check FLUX Dev (AWS, Azure) → Deploy
- Step 2: Select "T4" → Check FLUX Dev (GCP) → Deploy
- Step 3: Select "A100" → Check FLUX Dev (AWS) → Deploy

**Result**: FLUX Dev deployed on:
- AWS A10G: `flux-dev-a10g-aws.aws.com`
- AWS A100: `flux-dev-a100-aws.aws.com`
- Azure A10G: `flux-dev-a10g-azure.azure.com`
- GCP T4: `flux-dev-t4-gcp.gcp.com`

## Implementation Details

### GPU Tier Radio Buttons
- **Default**: A10G (Recommended)
- **Options**: T4, A10G, A100
- **Tooltips**:
  - T4: "$0.50/hr, 30-60s per image (FLUX)"
  - A10G: "$1.00/hr, 15-30s per image (FLUX) - Recommended"
  - A100: "$32.00/hr, 5-15s per image (FLUX) - Fastest"

### Checkbox Grid Behavior
- Grid shows nodes × providers (same as before)
- GPU tier selection applies to all checked boxes when "Deploy" is clicked
- Instance naming: `{node-type}-{gpu-tier}-{provider}`

### "Deploy Local Only" Behavior
- When checked:
  - Hide GPU tier radio buttons
  - Hide cloud provider columns
  - Show single column (local deployment only)
  - GPU tier not applicable (local uses host GPU)

### Deployment Instance Naming
- **Cloud**: `{node-type}-{gpu-tier}-{provider}-{timestamp}`
  - Example: `flux-dev-a10g-aws-1234567890`
- **Local**: `{node-type}-local-{timestamp}`
  - Example: `flux-dev-local-1234567890`

## Endpoint Export Format

```json
{
  "node_type": "FLUX Dev",
  "provider": "aws",
  "gpu_tier": "a10g",
  "endpoint": "https://nim-flux-dev-a10g-aws.aws.com",
  "cost_per_hour": 1.00,
  "estimated_time_per_image": "15-30s",
  "instance_name": "flux-dev-a10g-aws-1234567890"
}
```

## State Management

### Checkbox State
- Save checkbox state per GPU tier
- When switching GPU tiers, restore previous selections for that tier
- When "Deploy Local Only" is toggled, save/restore state appropriately

### Deployment History
- Track which GPU tiers have been deployed for each node/provider combination
- Show visual indicators (green checkmark) for already-deployed combinations
- Allow re-deployment with different GPU tier

## Visual Indicators

### Checkbox States
- ☐ **Unchecked**: Not selected
- ☑ **Checked**: Selected for deployment
- ✅ **Green checkmark**: Already deployed (with current GPU tier)
- ⚠️ **Yellow circle**: Deployed with different GPU tier
- ❌ **Red X**: Deployment failed

### GPU Tier Indicators
- Highlight selected GPU tier (radio button)
- Show cost/performance info in tooltip
- Gray out unavailable GPU tiers (if region doesn't support them)

