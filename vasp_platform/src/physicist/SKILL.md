---
name: VASP Physicist Skill
description: Capabilities for Post-Processing, Analysis, and Scientific Reporting.
---

# VASP Physicist Skill

This module defines the capabilities of the **Physicist Agent**, the "Expert" of the platform. Its primary role is to analyze the raw outputs of VASP calculations (`OUTCAR`, `vasprun.xml`) and provide scientific insights.

## Capabilities

### 1. File Parsing
-   **VASP Outputs**: Parse `vasprun.xml` using `pymatgen` to extract energies, forces, and eigenvalues.
-   **Log Analysis**: Scan `OUTCAR` or `run.log` for warnings (e.g., "ZBRENT: fatal error", "eddav").

### 2. Physical Validation
-   **Electronic Convergence**: Check if `dE < EDIFF` in the final electronic steps.
-   **Ionic Convergence**: Check if forces `< EDIFFG` (for Relaxations).
-   **Magnetic Moments**: Verification of `MAGMOM` (High Spin vs Low Spin).
-   **Band Gap**: Accurate extraction of CBM/VBM.

### 3. Reporting
-   **Manifest Update**: detailed `metadata` update in the `VaspJob` (e.g., `{"final_energy": -12.4, "converged": true}`).
-   **Advisory**: Recommend next steps to the Translator (e.g., "Relaxation converged, proceed to Static").

## Integration
-   **Input**: `JobManifest` (Status=COMPLETED).
-   **Output**: Scientist Report / Manifest Update.
