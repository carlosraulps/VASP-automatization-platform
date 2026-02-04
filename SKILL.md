---
name: VASP Agent Skill
description: Interactive conversational agent for VASP workflow automation.
---

# VASP Agent Skill

This skill provides a conversational AI agent (`vasp_agent.py`) that acts as a physicist and automation engineer to help you set up VASP calculations.

## Prerequisites

1.  **Python Environment**: Python 3.9+.
2.  **Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **API Keys**:
    - **Materials Project**: Ensure your key is in `config.json` or exported as `MP_API_KEY`.
    - **Google GenAI**: Export your Google API key:
        ```bash
        export GOOGLE_API_KEY="your_google_api_key"
        ```

## Usage

Start the agent session:

```bash
python3 vasp_agent.py
```

### Conversation Flow

1.  **Consultant Phase**:
    - You: "I want to run bands for GaAs"
    - Agent: Queries Materials Project, analyzes options, and presents a table with AI advice.
    - You: Select an option (e.g., "1").

2.  **Engineer Phase**:
    - The agent automatically:
        - Downloads `POSCAR`.
        - Constructs `POTCAR` (Local library).
        - Generates "Wise" `KPOINTS` based on band gap (Metal vs Semiconductor).
        - Stages `static-scf` and `bands` directories with `INCAR` and `job.sh`.

## Configuration

- `config.json`: Project root and potentials path.
- `templates.py`: VASP input templates.
