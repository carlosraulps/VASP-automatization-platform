# Data Lake (`data/`)

This directory serves as the "Workbench" and "Long-Term Memory" for the VASP Platform. It is designed to act as a structured Data Lake for both active simulations and historical knowledge.

## Directory Structure (Planned)

### 1. `manifests/`
-   **Content**: JSON files (`JobManifest`) produced by the Translator.
-   **Role**: The persistent "Contract" between agents.
-   **Scalability**: Allows the Manager Agent to pick up jobs created days ago, or by a different Translator instance.

### 2. `simulations/`
-   **Content**: Raw VASP inputs and outputs (`POSCAR`, `OUTCAR`, `vasprun.xml`, `run.log`, `job.sh`).
-   **Role**: The physical working directory for jobs (mirrored from HPC scratch).
-   **Organization**: Hierarchical structure `Material_ID / Calculation_Type / Run_ID`.

### 3. `knowledge_base/`
-   **Content**: Processed documents for RAG (Retrieval-Augmented Generation).
-   **Role**: Stores VASP Wiki pages, physics textbooks, and "Lessons Learned" from previous runs.
-   **Integration**: The Physicist Agent queries this folder to explain *why* a calculation failed.

## Data Retention
-   Files in `simulations/` should be treated as ephemeral (scratch).
-   Files in `manifests/` are permanent records of scientific intent.
