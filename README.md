# VASP Automation Platform (v2.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Status**: Service-Oriented Architecture (Ready for Multi-Agent Scale)

An AI-driven platform for high-throughput Density Functional Theory (DFT) calculations using VASP. This project transitions from linear scripting to a modular, event-driven architecture designed for multi-agent collaboration between an **Architect** (Translator), a **Sysadmin** (Manager), and an **Expert** (Physicist).

---

## 🏗️ Architecture

The platform operates on a "Manifest-Driven" workflow. Agents do not call each other directly; they communicate by reading and updating a shared **Data Contract** (`JobManifest`).

```mermaid
graph TD
    User([User]) -->|Consultation| Translator[Translator Agent]
    Translator -->|Creates| Manifest(JobManifest JSON)
    Manifest -->|Read by| Manager[Manager Agent]
    Manager -->|Submits to| HPC[HPC Cluster / Slurm]
    HPC -->|Outputs| RawFiles(OUTCAR / XML)
    RawFiles -->|Analyzed by| Physicist[Physicist Agent]
    Physicist -->|Updates| Manifest
```

---

## 🚀 Quick Start

### 1. Prerequisites
-   Python 3.9+
-   `.env` file with `GOOGLE_API_KEY`, `MP_API_KEY`, `PROJECT_ROOT`.

### 2. Execution
Run the orchestrator:
```bash
python3 main.py
```

### 3. The Workflow
1.  **Consult**: "I need a band structure for GaN."
2.  **Negotiate**: The Agent looks up the structure, checks the Band Gap, and proposes a customized `INCAR` strategy.
3.  **Approve**: You type "Run", and the Agent generates the full job directory structure.

---

## 📂 Deep Analysis of Modules

The source code (`vasp_platform/src`) is divided into four distinct domains:

### 1. Core Layer (`src/core`)
-   **Role**: The "Brain Stem".
-   **Key Components**:
    -   `llm.py`: A robust adapter for Google GenAI, handling API quotas and retries.
    -   `state.py`: Manages the short-term memory of the active agent session.
-   **Philosophy**: Agents should never talk to raw APIs directly; they must go through the Core.

### 2. Translator Module (`src/translator`)
-   **Role**: The "Architect".
-   **Documentation**: [Translator Skill](vasp_platform/src/translator/SKILL.md)
-   **Key Innovation**: **The Truth Layer**.
    -   Instead of letting the LLM "guess" the crystal structure, `tools.py` uses Pymatgen to rigorously compare lattice angles and classify the system (e.g., distinguishing Rhombohedral from Cubic).
    -   **IncarBuilder**: A logic-heavy class that generates `INCAR` files. It uses **Run-Length Encoding (RLE)** for `MAGMOM` tags.

### 3. Manager Module (`src/manager`) [Planned]
-   **Role**: The "Sysadmin".
-   **Documentation**: [Manager Skill](vasp_platform/src/manager/SKILL.md)
-   **Scalability**: Designed to handle `squeue` polling and SSH persistence.

### 4. Physicist Module (`src/physicist`) [Planned]
-   **Role**: The "Scientist".
-   **Documentation**: [Physicist Skill](vasp_platform/src/physicist/SKILL.md)
-   **Intelligence**: Checks `EDIFF` (Electronic) and `EDIFFG` (Ionic) limits to certify if a run is scientifically valid.

---

## 📂 Infrastructure & Scalability

### ⚙️ Configuration (`vasp_platform/config/`)
-   **[Read More](vasp_platform/config/README.md)**
-   Decouples the codebase from the environment.
-   Supports **Cluster Profiles** for multi-HPC deployments.

### 💾 Data Lake (`vasp_platform/data/`)
-   **[Read More](vasp_platform/data/README.md)**
-   **Manifests**: The persistent record of intent.
-   **Simulations**: The ephemeral working directory (mirrors scratch).
-   **Knowledge Base**: Future home for RAG documents.

---
*Developed by the VASP Automation Team.*
