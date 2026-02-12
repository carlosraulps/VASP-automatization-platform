
import time
import os
import json
from .connection import ClusterConnection
from .log_parser import LogParser
from .ai_debugger import AIDebugger
from .vaspkit_driver import VaspkitDriver

class VaspWorkflow:
    """
    Manages the lifecycle of a VASP calculation on the remote cluster.
    Implements the State Machine: Relaxation -> Static-SCF -> Bands.
    """
    
    STEP_RELAX = "relaxation"
    STEP_STATIC = "static-scf"
    STEP_BANDS = "bands"
    
    MAX_RETRIES = 3

    def __init__(self, connection: ClusterConnection):
        self.conn = connection
        self.parser = LogParser()
        self.debugger = AIDebugger()
        self.vaspkit = VaspkitDriver(connection)
        self.retry_counts = {} # Track retries per step path

    def process_folder(self, remote_path: str):
        """
        Main entry point to process a job folder.
        Determines the current state and executes the next step.
        """
        print(f"Processing {remote_path}...")
        
        # 1. Identify Current Stage (Reverse Order)
        
        if self._is_step_complete(remote_path, self.STEP_BANDS):
            print(f"Job {remote_path} is FULLY COMPLETED.")
            # Optional: Download specific results here
            return

        if self._is_step_complete(remote_path, self.STEP_STATIC):
            print(f"Transitioning to BANDS...")
            self._run_bands(remote_path)
            return

        if self._is_step_complete(remote_path, self.STEP_RELAX):
            print(f"Transitioning to STATIC-SCF...")
            self._run_static(remote_path)
            return
            
        # Default: Start or Continue Relaxation
        self._run_relaxation(remote_path)

    def _is_step_complete(self, base_path: str, step_name: str) -> bool:
        """
        Checks if a specific step is finished (e.g., OUTCAR contains 'reached required accuracy').
        """
        outcar = os.path.join(base_path, step_name, "OUTCAR")
        if not self.conn.exists(outcar):
            return False
            
        res = self.conn.run_command(f"grep 'reached required accuracy' {outcar}", warn=True)
        return res.ok if res else False

    def _submit_and_monitor(self, step_path: str):
        """
        Submits job.sh and monitors logs. Includes AI Debugging Loop.
        """
        job_script = os.path.join(step_path, "job.sh")
        if not self.conn.exists(job_script):
            print(f"Error: {job_script} not found.")
            return

        # Check if running
        q_res = self.conn.run_command(f"squeue -u $USER -h -o %Z", warn=True)
        # Identify job specifically helps, but for now simple check
        if q_res and step_path in q_res.stdout:
             # It is running, check logs but don't resubmit
             self._check_logs_and_fix(step_path)
             return

        # If not running and not complete, submit
        print(f"Submitting job in {step_path}...")
        self.conn.run_command(f"cd {step_path} && sbatch job.sh")

        # Initial check (async in real daemon)
        time.sleep(5) 
        self._check_logs_and_fix(step_path)
        
    def _check_logs_and_fix(self, step_path: str):
        """
        Reads run.log, detects errors, and uses AI to fix INCAR if needed.
        """
        log_file = os.path.join(step_path, "run.log")
        outcar_file = os.path.join(step_path, "OUTCAR")
        incar_file = os.path.join(step_path, "INCAR")

        if not self.conn.exists(log_file):
            return

        # Read Logs
        run_log = self.conn.run_command(f"tail -n 100 {log_file}").stdout
        outcar_tail = self.conn.run_command(f"tail -n 100 {outcar_file}").stdout if self.conn.exists(outcar_file) else ""
        
        # Check parser
        status = self.parser.parse(run_log)
        
        if status["action"] != LogParser.ACTION_CONTINUE:
            print(f"[Monitor] Issue detected in {step_path}: {status['error']}")
            
            # Check Max Retries
            retries = self.retry_counts.get(step_path, 0)
            if retries >= self.MAX_RETRIES:
                print(f"[Monitor] Max retries reached for {step_path}. Intervention needed.")
                return

            # AI Fix Strategy
            print(f"[AI Debugger] Analyzing failure...")
            
            # Fetch INCAR
            incar_content = self.conn.run_command(f"cat {incar_file}").stdout
            
            # Ask Gemini
            fixes = self.debugger.analyze(run_log, outcar_tail, incar_content)
            
            if fixes:
                print(f"[AI Debugger] Proposed Fixes: {fixes}")
                self._apply_incar_fixes(step_path, fixes)
                
                # Cancel current job if still technically running (often it crashes, but to be safe)
                # self.conn.run_command("scancel ...") # implement job ID tracking later
                
                print(f"[Monitor] Resubmitting {step_path} (Retry {retries + 1})...")
                self.conn.run_command(f"cd {step_path} && sbatch job.sh")
                self.retry_counts[step_path] = retries + 1
            else:
                 print("[AI Debugger] No fix proposed.")

    def _apply_incar_fixes(self, step_path: str, fixes: dict):
        """
        Applies the JSON fixes to the remote INCAR file using sed.
        """
        for tag, value in fixes.items():
            # SED: Replace existing tag or append if missing
            # Simple approach: Check if exists, replace. Else append.
            # Using grep to check
            check = self.conn.run_command(f"grep '{tag}' {step_path}/INCAR", warn=True)
            
            if check.ok:
                # Replace: s/TAG.*/TAG = Value/
                cmd = f"sed -i 's/^{tag}.*/{tag} = {value}/g' {step_path}/INCAR"
            else:
                # Append
                cmd = f"echo '{tag} = {value}' >> {step_path}/INCAR"
            
            self.conn.run_command(cmd)

    def _run_relaxation(self, base_path: str):
        work_dir = os.path.join(base_path, self.STEP_RELAX)
        if not self.conn.exists(work_dir):
            print("Relaxation directory missing.")
            return
        self._submit_and_monitor(work_dir)

    def _run_static(self, base_path: str):
        work_dir = os.path.join(base_path, self.STEP_STATIC)
        relax_dir = os.path.join(base_path, self.STEP_RELAX)
        
        if not self.conn.exists(work_dir):
             self.conn.run_command(f"mkdir -p {work_dir}")
             
        if not self.conn.exists(os.path.join(work_dir, "POSCAR")):
             print(f"Copying CONTCAR from {relax_dir} to {work_dir}/POSCAR")
             self.conn.run_command(f"cp {relax_dir}/CONTCAR {work_dir}/POSCAR")
        
        self._submit_and_monitor(work_dir)

    def _run_bands(self, base_path: str):
        work_dir = os.path.join(base_path, self.STEP_BANDS)
        static_dir = os.path.join(base_path, self.STEP_STATIC)
        
        if not self.conn.exists(work_dir):
             self.conn.run_command(f"mkdir -p {work_dir}")

        # 1. Copy Inputs
        if not self.conn.exists(os.path.join(work_dir, "CHGCAR")):
             print(f"Copying CHGCAR from {static_dir}...")
             self.conn.run_command(f"cp {static_dir}/CHGCAR {work_dir}/CHGCAR")
             
        if not self.conn.exists(os.path.join(work_dir, "POSCAR")):
             self.conn.run_command(f"cp {static_dir}/POSCAR {work_dir}/POSCAR")

        # 2. Generate KPOINTS (VASPkit)
        if not self.conn.exists(os.path.join(work_dir, "KPOINTS")):
             if not self.vaspkit.generate_kpoints(work_dir, task_id="303"):
                 print("Failed to generate KPOINTS for Bands. Stopping.")
                 return

        # 3. Submit
        self._submit_and_monitor(work_dir)
        
        # 4. Post-Process (Check if done first)
        if self._is_step_complete(base_path, self.STEP_BANDS):
             self.vaspkit.extract_bands(work_dir)
             # Download?
             # self.conn.get_file(...)
