---
name: VASP Automation Skill
description: Modular AI platform for creating VASP DFT workflows (Relaxation, Static, Bands).
---

# VASP Automation Skill

This skill allows you to consult with an AI Physicist ("Translator Agent") to design and stage high-throughput VASP calculations. It outputs a structured `JobManifest` representing the work to be done.

## Prerequisites

1.  **Environment**: Python 3.9+ with `python-dotenv`, `google-genai`, `pymatgen`, `mp-api`.
2.  **Configuration**:
    -   Ensure a `.env` file exists in the root with:
        ```env
        GOOGLE_API_KEY=...
        MP_API_KEY=...
        PROJECT_ROOT=/path/to/simulations
        POTENTIALS_DIR=/path/to/potentials
        ```

## Usage

Run the platform entry point:

```bash
python3 main.py
```

## Workflow

1.  **Consultation**: Ask for a material (e.g., "Bands for Silicon").
2.  **Negotiation**: The agent will propose settings based on **Crystallography** and **Physics**.
    -   It uses a "Truth Layer" to avoid crystal system hallucinations.
    -   It enforces a text-based "Preview" before generating files.
3.  **Execution**:
    -   On approval, the agent generates:
        -   VASP Inputs (`POSCAR`, `INCAR`, `KPOINTS`, `POTCAR`, `job.sh`).
        -   Directory Structure: `formula/relaxation`, `formula/static-scf`, `formula/bands`.
    -   **Output**: A JSON `JobManifest` printed to stdout, ready for handoff to a Manager Agent.

## Architecture

-   **Entry**: `main.py`
-   **Core Logic**: `vasp_platform/`
-   **Schema**: `vasp_platform/schema/manifest.py` (Defines the `VaspJob` contract).
