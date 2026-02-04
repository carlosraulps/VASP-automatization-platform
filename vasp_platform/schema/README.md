# The Shared Data Contract (`schema/`)

This directory defines the **Protocol** by which all agents communicate. In a multi-agent system, the schema is the "Universal Language" that prevents miscommunication.

## The Job Manifest
The core concept is the `JobManifest`. It serves as a persistent, portable record of scientific intent.

### JSON Structure Example
A `VaspJob` serialized to JSON looks like this:

```json
{
  "material_id": "mp-149",
  "formula": "Si",
  "directory_path": "/simulations/Si/static-scf",
  "job_type": "STATIC",
  "status": "CREATED",
  "parameters": {
    "kpoints": "Monkhorst 12 12 12",
    "dft_u": false,
    "encut": 520
  },
  "metadata": {}
}
```

## The Lifecycle
1.  **CREATED**: The Translator has generated input files.
2.  **PENDING**: The Job is in the `JobManifest`, waiting for the Manager.
3.  **SUBMITTED**: The Manager has run `sbatch`.
4.  **RUNNING**: The job is active on the cluster.
5.  **COMPLETED**: The Calculator has finished.
6.  **ANALYZED**: The Physicist has verified the results.

## Extension
To add new capabilities (e.g., "Phonon Calculations"), simply extend the `JobType` enum in `manifest.py`. No other code needs to change to support the data structure.
