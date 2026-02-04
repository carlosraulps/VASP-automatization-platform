# VASP Automation Platform

An AI-driven platform for high-throughput Density Functional Theory (DFT) calculations using VASP. This project transitions from linear scripting to a modular, event-driven architecture designed for multi-agent collaboration.

## 🏗️ Architecture: Service-Oriented Design

The project is structured as a scalable platform (`vasp_platform/`) where functionality is isolated into specialized modules.

### Current State: The Translator Agent
The core of the current system is the **Translator Agent**, which acts as the "Architect." It handles:
- **Consultation**: Interaction with the user to define materials and goals.
- **Engineering**: Mathematical analysis of crystallography and physics parameters.
- **Job Staging**: Creation of VASP-ready input files (`POSCAR`, `POTCAR`, `INCAR`, `KPOINTS`, `job.sh`).
- **Data Contract**: Generating a `JobManifest` (Pydantic model) that serves as the digital blueprint for execution.

### Project Structure
```text
vasp_automation_platform/
├── main.py                 # The Orchestrator (Session start)
├── .env                    # Secrets & Config (API Keys, Paths)
├── vasp_platform/
│   ├── schema/
│   │   └── manifest.py     # Shared Data Contract (VaspJob, JobManifest)
│   ├── src/
│   │   ├── core/           # LLM Adapters and State Management
│   │   └── translator/     # Translator Agent Logic, Tools, and Builders
│   └── data/               # Workbench for simulation files
└── legacy/                 # Original scripts (vasp_agent.py, vasp_translator.py)
```

## 🚀 Future Roadmap

The platform is designed to integrate two additional agents:

### 1. The Manager Agent (Sysadmin)
- **Target**: High-Performance Computing (HPC) clusters.
- **Role**: Read the `JobManifest` created by the Translator, submit jobs via Slurm, and monitor run status.
- **Intelligence**: Handle queue priorities and basic node failure recovery.

### 2. The Physicist Agent (Expert)
- **Target**: Analysis & Reporting.
- **Role**: Post-process VASP outputs (OUTCAR, XML).
- **Intelligence**: Check for convergence, detect electronic/magnetic properties, and advise the Translator on subsequent steps (e.g., "Increase K-points for convergence").

## 🛠️ Setup & Usage

### 1. Configuration
Create a `.env` file in the root directory:
```env
GOOGLE_API_KEY=your_gemini_key
MP_API_KEY=your_materials_project_key
PROJECT_ROOT=/path/to/your/simulation/folders
POTENTIALS_DIR=/path/to/your/vasp/potentials
```

### 2. Execution
Run the orchestrator:
```bash
python3 main.py
```

## 📜 Key Features
- **Crystallography Truth Layer**: Hard-coded analysis to prevent LLM hallucinations.
- **Run-Length Encoding (RLE)**: Automatic `MAGMOM` formatting for large systems.
- **Physics Rationale Protocol**: Forced explainability for every parameter modification.
- **Pydantic Schemas**: Strict validation of job data for seamless handovers.

---
*Developed by the VASP Automation Team.*
