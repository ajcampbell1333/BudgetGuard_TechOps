# BudgetGuard Artists Config Format

This JSON file is produced by TechOps and consumed by the Artists app/backend to:
- Detect credentials presence (status-only in GUI)
- Route requests to deployed NIM endpoints (by node and provider)
- Optionally include GPU tier availability per node

File name recommendation:
- `budgetguard_artists_config.json`
- Location for handoff: place alongside Artists’ ComfyUI config (documented by TechOps)

## Top-level fields

```json
{
  "version": "1.0",
  "generated_at": "2025-11-06T21:00:00Z",
  "nim_endpoints": {
    "FLUX Dev": {
      "aws": [
        { "url": "https://...", "gpu_tier": "a10g" }
      ],
      "azure": [],
      "gcp": []
    }
  },
  "credentials_status": {
    "nvidia": true,
    "aws": true,
    "azure": false,
    "gcp": true
  }
}
```

- `version`: schema version for compatibility.
- `generated_at`: ISO timestamp (UTC).
- `nim_endpoints`: map of NIM node name → provider → list of endpoints with optional `gpu_tier`.
- `credentials_status`: booleans reflecting whether credentials were installed for each provider (Artists GUI uses to show ✓/⚠ only; no secrets included here).

## Notes
- No secrets are stored in this file; credentials are installed separately by TechOps tooling.
- Providers use lowercase keys: `aws`, `azure`, `gcp`, `nvidia-hosted`, `local` (if included).
- Artists GUI can hide GPU dropdown when only one tier is available for a node.

