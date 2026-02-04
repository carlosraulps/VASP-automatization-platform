# Source Code (`src/`)

This directory houses the logic for the platform's independent modules. The architecture follows a **Domain-Driven Design** approach, separating responsibilities into distinct "Skills."

## Module Map

### 1. `core/` (The Foundation)
-   **Role**: Shared utilities (LLM, State) used by all agents.
-   **[Read More](core/README.md)**

### 2. `translator/` (The Architect)
-   **Role**: Consults with the user and generates VASP input files.
-   **Capabilities**: Crystal analysis, Parameter negotiation, Input generation.
-   **Documentation**: [Translator Skill](translator/SKILL.md)

### 3. `manager/` (The Sysadmin) [Planned]
-   **Role**: Manages HPC interactions (jobs, queues, SSH).
-   **Capabilities**: `sbatch`, `squeue`, Fault tolerance.
-   **Documentation**: [Manager Skill](manager/SKILL.md)

### 4. `physicist/` (The Expert) [Planned]
-   **Role**: Analyzes scientific results.
-   **Capabilities**: Convergence checks (`EDIFF`), Band gap extraction, Reporting.
-   **Documentation**: [Physicist Skill](physicist/SKILL.md)

## Data Flow
```text
[Core] provides Tools -> [Translator] creates Manifest -> [Manager] executes Jobs -> [Physicist] verifies Results
```
