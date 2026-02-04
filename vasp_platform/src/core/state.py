from typing import List, Optional, Any
from vasp_platform.schema.manifest import VaspJob

class AgentState:
    def __init__(self):
        self.memory: List[str] = []
        self.current_jobs: List[VaspJob] = []
        self.context: dict = {}

    def add_job(self, job: VaspJob):
        self.current_jobs.append(job)

    def log_interaction(self, role: str, content: str):
        self.memory.append(f"{role}: {content}")

    def get_last_message(self) -> str:
        if self.memory:
            return self.memory[-1]
        return ""
