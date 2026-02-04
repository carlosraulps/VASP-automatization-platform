---
name: VASP Manager Skill
description: Capabilities for HPC Cluster Management, Queue execution, and Job submission.
---

# VASP Manager Skill

This module defines the capabilities of the **Manager Agent**, the "Sysadmin" of the platform. Its primary role is to execute the jobs defined in the `JobManifest` on an HPC cluster (e.g., Slurm).

## Capabilities

### 1. Queue Management
-   **Check Status**: Query the scheduling system (e.g., `squeue`, `qstat`) to track job IDs.
-   **Health Check**: Monitor node availability and user quotas.
-   **Manifest Update**: Update the status of a `VaspJob` in the manifest from `PENDING` to `RUNNING` or `COMPLETED`.

### 2. Job Submission
-   **SSH Connection**: Connect to remote clusters via `paramiko` or similar (defined in `core/`).
-   **Batch Execution**: Run `sbatch job.sh` inside the directory specified by `directory_path` in the Manifest.
-   **Error Handling**: Detect immediate submission failures (e.g., "Script not found", "Invalid Account").

### 3. File Transport (Future)
-   **Sync**: If separating Local/Remote, handle `rsync` of the staged directories to the scratch space.

## Integration
-   **Input**: `JobManifest` (from Translator).
-   **Output**: Updated `JobManifest` (Status=RUNNING).
