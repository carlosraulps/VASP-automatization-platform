from enum import Enum
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class JobType(str, Enum):
    RELAXATION = "relaxation"
    STATIC = "static"
    BANDS = "bands"

class VaspJob(BaseModel):
    """
    Represents a VASP calculation job prepared by the Translator.
    This is the contract passed to the Manager Agent.
    """
    material_id: str = Field(..., description="The MP ID of the material (e.g., mp-149)")
    formula: str = Field(..., description="Chemical formula (e.g., Si)")
    directory_path: str = Field(..., description="Absolute path to the staged job directory")
    job_type: JobType = Field(..., description="Type of calculation")
    status: JobStatus = Field(default=JobStatus.CREATED)
    
    # Physics Parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Key VASP parameters (ENCUT, KPOINTS, etc.) for record keeping"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

class JobManifest(BaseModel):
    """
    Collection of jobs created in a session.
    """
    jobs: List[VaspJob] = Field(default_factory=list)
    project_root: str
