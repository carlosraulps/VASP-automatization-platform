
import os
from .connection import ClusterConnection

class VaspkitDriver:
    """
    Wrapper to execute vaspkit commands on the remote HPC cluster.
    Assumes vaspkit is installed at ~/vaspkit.1.5.1/bin/vaspkit (or in PATH).
    """

    # VASPkit Task IDs
    TASK_KPATH_3D = "303"
    TASK_KPATH_2D = "302"
    TASK_BAND_STRUCTURE = "211"
    
    # Common VASPkit inputs for piping
    # Format: TaskID \n SubOption...
    # For 303 (K-Path 3D): 303 -> 2 (K-Path for Band-Structure) -> ... (defaults usually work)
    INPUT_KPATH_3D = "303\n2\n" 
    
    # For 211 (Band Structure): 211 -> 1 (Projected) or just 211 output
    # Usually standard 211 generates BAND.dat, KLABELS, etc.
    INPUT_BANDS_EXTRACT = "211\n1\n0\n" # 211 -> 1 (Projected Band) -> 0 (No specific element selection/All) - approximates

    def __init__(self, connection: ClusterConnection, vaspkit_path="~/vaspkit.1.5.1/bin/vaspkit"):
        self.conn = connection
        self.executable = vaspkit_path

    def generate_kpoints(self, remote_path: str, task_id="303"):
        """
        Runs VASPkit to generate KPOINTS for Band Structure.
        Args:
            remote_path: The directory where the calculation setup is.
            task_id: 303 (3D) or 302 (2D).
        """
        # Construct the input pipe
        # We generally want Option 2: "K-Path for Band-Structure" within Task 303
        input_str = f"{task_id}\\n2\\n" 
        
        print(f"[VASPkit] Generating KPOINTS in {remote_path} using Task {task_id}...")
        
        # Command: echo -e "..." | vaspkit
        # We need to cd to the directory first
        cmd = f"cd {remote_path} && echo -e '{input_str}' | {self.executable}"
        
        result = self.conn.run_command(cmd)
        
        if result and result.ok:
            # Check if KPOINTS now exists
            if self.conn.exists(os.path.join(remote_path, "KPOINTS")):
                print("[VASPkit] KPOINTS generated successfully.")
                return True
        
        print(f"[VASPkit] Failed to generate KPOINTS. Output: {result.stdout if result else 'None'}")
        return False

    def extract_bands(self, remote_path: str):
        """
        Runs VASPkit Task 211 to extract band structure data (.dat files).
        """
        print(f"[VASPkit] Extracting Band Data in {remote_path}...")
        
        # Command: echo -e "211\n1\n0" | vaspkit
        # Task 211: Band Structure
        # Sub-option 1: Projected Band-Structure (or 2: Plain). Let's try plain first if possible or 1.
        # Simplest: "211" often suffices if no sub-menus, but often it asks for projected vs plain.
        # Let's assume standard behavior: 211 -> 1 (Projected) -> ...
        # Safer: 211\n (defaults?)
        # Let's try the input defined in constant.
        
        cmd = f"cd {remote_path} && echo -e '{self.INPUT_BANDS_EXTRACT}' | {self.executable}"
        
        result = self.conn.run_command(cmd)
        
        # Check for expected output files
        # BAND.dat is common, or REFORMATTED_BAND.dat
        expected_file = os.path.join(remote_path, "BAND.dat") 
        # vaspkit 1.3+ often produces BAND.dat or specific names.
        
        if result and result.ok:
            if self.conn.exists(expected_file) or self.conn.exists(os.path.join(remote_path, "BAND_O.dat")): # Spin up/down
                print("[VASPkit] Band data extracted.")
                return True
        
        print(f"[VASPkit] Failed to extract bands. Output: {result.stdout if result else 'None'}")
        return False
