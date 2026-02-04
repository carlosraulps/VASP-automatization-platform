---
name: VASP Translator Skill
description: Capabilities for Consultative VASP Workflow Design.
---

# VASP Translator Skill

The **Translator Agent** acts as the "Architect" of the platform. It bridges the gap between a human request ("Calculate bands for Si") and the rigid requirements of VASP inputs.

## The Interactive Loop

The agent follows a strict 3-phase consulting process:

### 1. Consultant Phase
-   **Goal**: Identify the material.
-   **Action**: Queries Materials Project via `MPRester` to find candidates.
-   **Output**: Presents a list of options (e.g., Stable vs Unstable ID).

### 2. Negotiation Phase
-   **Goal**: Define physics parameters.
-   **Features**:
    -   **Truth Layer**: Runs `analyze_crystallography` to mathematically classify the lattice (e.g., Rhombohedral vs Hexagonal).
    -   **Preview Mode**: Users can type "Preview" to see the generated `INCAR` files instantly without committing.
    -   **Physics Rules**: Automatically detects Transition Metals and suggests `DFT+U`.

### 3. Engineering Phase
-   **Goal**: Stage the files.
-   **Action**: Generates the directory structure (`formula/relaxation`, `formula/static`, `formula/bands`).
-   **Output**: A `JobManifest` (Status=CREATED) ready for the Manager Agent.

## Capabilities
-   **Magmom RLE**: Compresses magnetic moments for large systems to avoid VASP read errors.
-   **K-Point Logic**: Automatically switches between `Gamma`, `Monkhorst`, and `Line_Mode` based on calculation type.
