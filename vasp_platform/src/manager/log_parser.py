
class LogParser:
    """
    Parses VASP output logs to detect convergence status and runtime errors.
    Acts as a 'Watchdog' for the Manager Agent.
    """
    
    ACTION_CONTINUE = "CONTINUE"
    ACTION_STOP_ERROR = "STOP_ERROR" 
    ACTION_MODIFY_INCAR_ALGO = "MODIFY_INCAR_ALGO"
    ACTION_SLOW_CONVERGENCE = "SLOW_CONVERGENCE"

    def __init__(self):
        pass

    def parse(self, log_content: str) -> dict:
        """
        Analyzes the log content and returns a status dictionary.
        """
        status = {
            "action": self.ACTION_CONTINUE,
            "error": None,
            "convergence_step": 0
        }

        if not log_content:
            return status

        # 1. Check for specific VASP Errors
        if "ZHEGV" in log_content:
            status["action"] = self.ACTION_MODIFY_INCAR_ALGO
            status["error"] = "ZHEGV: Diagonlization failed. Try ALGO=Normal."
            return status
            
        if "EDDDAV" in log_content: 
             status["action"] = self.ACTION_MODIFY_INCAR_ALGO # Often fixed similarly
             status["error"] = "EDDDAV: Subspace gradient error."
             return status

        # 2. Check for Slow Convergence
        # Logic: If we see many electronic steps (DAV: or RMM:) without reaching the limit
        lines = log_content.split('\n')
        scf_steps = [line for line in lines if "DAV:" in line or "RMM:" in line]
        
        status["convergence_step"] = len(scf_steps)
        
        # Heuristic: If > 60 steps in a single IONIC loop (implied by just counting total for now as a proxy, 
        # normally we track steps between ionic steps, but for 'run.log' it's a stream)
        # A better check is looking at the last few lines. 
        if len(scf_steps) > 60:
             # Check if dE is small. If dE is large, it's just diverging. If dE is small, it's stuck.
             last_step = scf_steps[-1]
             # Example line: DAV:  10    -0.12345E+01    0.123E-04   -0.567E-05 ...
             # We can do a rough check. for now, just flag it.
             status["action"] = self.ACTION_SLOW_CONVERGENCE
             status["error"] = "Slow convergence detected (>60 steps)."

        return status
