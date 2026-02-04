# Configuration Directory (`config/`)

This directory is the central hub for system-wide configuration, enabling the VASP Platform to scale across different environments (local development, staging, production HPC).

## Purpose

To decouple "Code" from "Environment". The agent logic remains immutable, while this directory handles the variances in infrastructure.

## Scalability Roadmap

### 1. Cluster Profiles
Future integration will support `cluster_profiles.json` to define HPC specifications:

```json
{
  "perlmutter": {
    "hostname": "perlmutter.nersc.gov",
    "scheduler": "slurm",
    "commands": {
      "submit": "sbatch",
      "status": "squeue -u $USER"
    },
    "partitions": ["regular", "debug"]
  }
}
```

### 2. Multi-Environment Support
-   **Secrets Management**: Integration with `secrets.enc` for encrypted storage of API keys and SSH credentials.
-   **Feature Flags**: Toggle experimental features (e.g., `use_gpt4_physics_engine: true`) without code changes.

## Current Usage
-   Currently, basic configuration is handled via the root `.env` file which injects variables into `vasp_platform.src.core.state`.
