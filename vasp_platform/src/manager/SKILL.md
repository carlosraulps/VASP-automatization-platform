---
name: VASP Manager Skill
description: Capabilities for HPC Cluster Management, Queue execution, and Job submission.
---

# VASP Manager Skill

This module defines the capabilities of the **Manager Agent**, the "Sysadmin" of the platform. Its primary role is to execute the jobs defined in the `JobManifest` on an HPC cluster (e.g., Slurm) and ensure they complete successfully.

## Capabilities

### 1. Connection Management (`connection.py`)
-   **SSH Gateway/Bastion Support**: Connects to the HPC cluster via a jump host using `fabric`.
-   **Persistence**: Maintains a reliable connection for command execution.
-   **File Transfer**: Handles uploading inputs and downloading logs.

### 2. Workflow Orchestration (`workflow.py`)
-   **State Machine**: Manages the lifecycle of a calculation:
    1.  `Relaxation` (Ionic optimization)
    2.  `Transition` (Copy CONTCAR -> POSCAR)
    3.  `Static-SCF` (Electronic optimization)
    4.  `Bands` (Band structure calculation)
-   **Self-Correction**: Automatically detects failures and attempts to fix them (e.g., switching algorithms on ZHEGV errors).

### 3. Monitoring & Intelligence (`log_parser.py` & `ai_debugger.py`)
-   **Convergence Watchdog**: Detects slow convergence (many SCF steps with small dE).
-   **Error Detection**: Identifies common VASP errors (`ZHEGV`, `EDDDAV`).
-   **AI Analysis**: The `AIDebugger` uses Google Gemini to read tail logs (`run.log`, `OUTCAR`) and intelligently propose `INCAR` modifications to fix crashes.

### 4. External Tools (`vaspkit_driver.py`)
-   **VASPkit Integration**: Wraps `vaspkit` commands on the remote cluster.
-   **K-Path Generation**: Automates the creation of `KPOINTS` for Band Structure (VASPkit Task 303/302).
-   **Band Extraction**: Extracts `BAND.dat` and `KLABELS` for plotting (VASPkit Task 211).

### 5. Service Daemon (`daemon.py`)
-   **Continuous Operation**: Runs as a persistent service on the cloud VM.
-   **Queue Sync**: Automatically syncs new job folders from the local queue to the remote cluster.
-   **Job Triggering**: Initiates the workflow for new jobs.

## Integration
-   **Input**: Directory structure created by the Translator.
-   **Output**: Completed VASP calculations on the HPC cluster (WAVECAR, CHGCAR, XML).
