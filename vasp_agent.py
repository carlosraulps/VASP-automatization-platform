
import os
import sys
import json
import shutil
import argparse
from google import genai
from mp_api.client import MPRester
from pymatgen.io.vasp import Poscar
from pymatgen.core import Structure
from dotenv import load_dotenv
import templates

# Load Environment Variables from .env
load_dotenv()

# Load Configuration
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

PROJECT_ROOT = CONFIG['PROJECT_ROOT']
POTENTIALS_DIR = CONFIG['POTENTIALS_DIR']
# Handle if value is a Key string or Env Var name
api_key_val = CONFIG.get('API_KEY_ENV_VAR', '')
MP_API_KEY = os.environ.get(api_key_val, api_key_val) if api_key_val and len(api_key_val) < 20 else api_key_val

# Gemini Setup
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

class VASPSkill:
    def __init__(self):
        self.check_env()
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        self.model_name = 'gemini-3-flash-preview' # Defaulting to a likely valid model, user requested 'gemini-3' which might be invalid/typo
        # Logic to respect user's choice from previous edit if valid, but 'gemini-3' is suspicious. 
        # I will use a safe default or try to support their intent.
        # Let's stick to a known working model for now: gemini-1.5-flash or gemini-2.0-flash-exp
        
        self.project_root = PROJECT_ROOT
        self.potentials_dir = POTENTIALS_DIR
        
        self.current_materials = [] # Cache for selection
        self.selected_doc = None
        
    def check_env(self):
        if not MP_API_KEY:
             print("Error: Materials Project API Key not found in config or environment.")
             # sys.exit(1) # Soft fail for agent loop
        if not GOOGLE_API_KEY:
             print("Error: GOOGLE_API_KEY not found. Please set 'GOOGLE_API_KEY' environment variable.")
             sys.exit(1)

    def start_interaction(self):
        print("\n--- VASP Agent Skill Initialized (google-genai SDK) ---")
        print("I am your AI Physicist and VASP Expert.")
        print("Tell me what you want to calculate (e.g., 'Bands for GaAs').\n")
        
        while True:
            try:
                user_input = input("User: ")
                if user_input.lower() in ['exit', 'quit']:
                    print("Exiting...")
                    break
                
                # Phase 1: Consultant
                self.phase_consultant(user_input)
                
                # Selection
                self.handle_selection()
                
                # Phase 2: Engineer
                if self.selected_doc:
                    self.phase_engineer()
                    print("\nReady for next task. What would you like to do?")
                    self.selected_doc = None
                    self.current_materials = []

            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
                import traceback
                traceback.print_exc()

    def phase_consultant(self, user_input):
        print("\n[AI Action: Parsing Request...]")
        
        # 1. Query Formulation using Gemini
        prompt = f"""
        Extract the chemical formula from this user request: "{user_input}".
        Return ONLY the formula (e.g., GaAs). If no formula is found, return INVALID.
        """
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        formula = response.text.strip()
        
        if formula == "INVALID":
            print("AI: I couldn't identify a chemical formula. Please try again.")
            return

        print(f"[Tool: Querying Materials Project for '{formula}'...]")
        
        # 2. Tool Execution
        # Handle MP API import or instantiation error gracefully
        try:
             with MPRester(MP_API_KEY) as mpr:
                 docs = mpr.materials.summary.search(formula=formula, fields=["material_id", "structure", "symmetry", "band_gap", "is_stable"])
        except Exception as e:
            print(f"Error connecting to Materials Project: {e}")
            return
        
        if not docs:
            print(f"AI: No materials found for {formula}.")
            return

        # 3. Advisory (Gemini analyzes the list)
        print("\n[AI Action: Analyzing Options...]\n")
        
        self.current_materials = sorted(docs, key=lambda x: x.material_id)[:5] 
        material_data_str = ""
        for i, doc in enumerate(self.current_materials):
            struct_info = f"{doc.symmetry.crystal_system}" if doc.symmetry else "Unknown"
            material_data_str += f"Option {i+1}: ID={doc.material_id}, Structure={struct_info}, BandGap={doc.band_gap:.2f}eV, Stable={doc.is_stable}\n"
            
        advice_prompt = f"""
        Act as a DFT Physicist. Review these material options for '{formula}':
        {material_data_str}
        
        For each option, provide a ONE-sentence "AI Comment" advising on its suitability.
        Focus on stability, phase (standard vs high pressure), and typical use cases.
        Format output strictly as:
        Option N: [AI Comment]
        """
        
        advice_response = self.client.models.generate_content(model=self.model_name, contents=advice_prompt)
        advice_map = {}
        if advice_response and advice_response.text:
            for line in advice_response.text.split('\n'):
                if line.startswith("Option"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        advice_map[parts[0].strip()] = parts[1].strip()

        # Print Table
        print(f"{'Option':<10} | {'MP-ID':<15} | {'Structure':<15} | {'Gap (eV)':<8} | {'AI Comment'}")
        print("-" * 100)
        for i, doc in enumerate(self.current_materials):
            opt_key = f"Option {i+1}"
            comment = advice_map.get(opt_key, "No comment.")
            print(f"{i+1:<10} | {str(doc.material_id):<15} | {str(doc.symmetry.crystal_system):<15} | {doc.band_gap:<8.2f} | {comment}")
            
    def handle_selection(self):
        if not self.current_materials:
            return

        while True:
            try:
                sel = input("\nSelect Option # (or 0 to cancel): ")
                idx = int(sel)
                if idx == 0:
                    break
                if 1 <= idx <= len(self.current_materials):
                    self.selected_doc = self.current_materials[idx-1]
                    print(f"\nSelected: {self.selected_doc.material_id}")
                    break
                else:
                    print("Invalid selection.")
            except ValueError:
                print("Please enter a number.")

    def phase_engineer(self):
        if not self.selected_doc:
            return

        print("\n[Engineer: Starting File Generation...]")
        
        # Reduced formula can be tricky if composition object, ensure string
        formula = str(self.selected_doc.structure.composition.reduced_formula)
        material_folder = os.path.join(self.project_root, formula)
        
        # 1. POSCAR
        print(f"  -> Generating POSCAR for {formula}...")
        os.makedirs(material_folder, exist_ok=True)
        poscar = Poscar(self.selected_doc.structure)
        poscar.write_file(os.path.join(material_folder, "POSCAR"))
        
        # 2. POTCAR (Copy Logic)
        print(f"  -> Constructing POTCAR (PBE default)...")
        self.construct_potcar(material_folder, self.selected_doc.structure)
        
        # 3. KPOINTS (Wise Logic)
        print(f"  -> Generating KPOINTS (Band Gap Analysis)...")
        band_gap = self.selected_doc.band_gap
        self.generate_wise_kpoints(material_folder, band_gap)
        
        # 4. INCAR & Job Script (Staging)
        print(f"  -> Staging 'static-sci' and 'bands' directories...")
        self.stage_directories(material_folder, formula, self.selected_doc.structure)
        
        print(f"\n[Success] VASP inputs prepared in {material_folder}")

    def construct_potcar(self, material_folder, structure):
        elements = [str(el) for el in structure.composition.elements]
        potcar_files = []

        for el in elements:
            candidates = [f"{el}_sv", f"{el}_d", f"{el}"]
            found = False
            # Fix: POTENTIALS_DIR might be None if user didn't config, assume config validation passed or check here
            if not self.potentials_dir or not os.path.exists(self.potentials_dir):
                print(f"    [Error] Potentials directory not found: {self.potentials_dir}")
                return

            for cand in candidates:
                path = os.path.join(self.potentials_dir, cand, "POTCAR")
                if os.path.exists(path):
                    potcar_files.append(path)
                    found = True
                    break
            
            if not found:
                print(f"    [Warning] Potential not found for {el} in {self.potentials_dir}")

        dest_potcar = os.path.join(material_folder, "POTCAR")
        # Only write if we have files
        if potcar_files:
            with open(dest_potcar, 'wb') as outfile:
                for fname in potcar_files:
                    with open(fname, 'rb') as infile:
                        outfile.write(infile.read())
        else:
             print("    [Warning] POTCAR not created (no potentials found).")

    def generate_wise_kpoints(self, material_folder, band_gap):
        kpoints_path = os.path.join(material_folder, "KPOINTS")
        
        if band_gap == 0:
            comment = "Metal - High Density - Methfessel-Paxton"
            kpts = "21 21 21" 
        else:
             comment = "Semiconductor - Medium Density - Tetrahedron/Gaussian"
             kpts = "11 11 11" 
             
        content = f"{comment}\n0\nGamma\n{kpts}\n0 0 0\n"
        with open(kpoints_path, "w") as f:
            f.write(content)
        print(f"    [Logic] Gap={band_gap:.2f}eV -> {comment}")

    def stage_directories(self, material_folder, formula, structure):
        subdirs = ["static-sci", "bands"]
        files_to_copy = ["POSCAR", "POTCAR", "KPOINTS"]
        
        magmoms = []
        for site in structure.species:
             sz = str(site)
             if sz in ["Fe", "Co", "Ni", "Mn"]: magmoms.append("2.0")
             else: magmoms.append("0.6")
        magmom_str = " ".join(magmoms)

        for sub in subdirs:
            sub_path = os.path.join(material_folder, sub)
            os.makedirs(sub_path, exist_ok=True)
            
            for file in files_to_copy:
                src = os.path.join(material_folder, file)
                dst = os.path.join(sub_path, file)
                if os.path.exists(src):
                    shutil.copy(src, dst)
            
            # INCAR
            if sub == "static-sci":
                content = templates.INCAR_STATIC.format(Material=formula, MAGMOM=magmom_str)
            else:
                content = templates.INCAR_BANDS.format(Material=formula, MAGMOM=magmom_str)
            
            with open(os.path.join(sub_path, "INCAR"), "w") as f:
                f.write(content)
                
            # Job Script
            job_type = "Static" if sub == "static-sci" else "Bands"
            job_content = templates.JOB_SCRIPT.format(Material=formula, JobType=job_type)
            with open(os.path.join(sub_path, "job.sh"), "w") as f:
                f.write(job_content)

if __name__ == "__main__":
    agent = VASPSkill()
    agent.start_interaction()
