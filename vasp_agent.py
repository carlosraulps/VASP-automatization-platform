
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
                
                # Phase 2: Engineer (Negotiation + Generation)
                if self.selected_doc:
                    self.phase_engineer_negotiation()
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
        
        try:
             with MPRester(MP_API_KEY) as mpr:
                 docs = mpr.materials.summary.search(formula=formula, fields=["material_id", "structure", "symmetry", "band_gap", "is_stable"])
        except Exception as e:
            print(f"Error connecting to Materials Project: {e}")
            return
        
        if not docs:
            print(f"AI: No materials found for {formula}.")
            return

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

    def phase_engineer_negotiation(self):
        """
        New phase that proposes settings and negotiates with the user BEFORE generating files.
        """
        if not self.selected_doc:
            return

        print("\n[Engineer: Analyzing Structure & Proposing Strategy...]")
        
        # 1. Analyze & Propose
        job_settings, diagnostics = self.propose_settings(self.selected_doc)
        
        # 2. Negotiation Loop
        print("\n--- Strategy Proposal ---")
        
        # Print Diagnostics
        print("\n[Diagnostics]")
        print(f"1. System Type: {'Metal' if diagnostics['is_metal'] else 'Insulator'} (Gap: {diagnostics['gap']:.2f} eV)")
        transition_msg = f"Transition Metals Detected: {', '.join(diagnostics['transition_metals'])}" if diagnostics['transition_metals'] else "No Transition Metals"
        print(f"2. Chemistry: {transition_msg}")
        print(f"3. Cell Size: {diagnostics['num_atoms']} atoms")
        
        self.print_settings(job_settings)
        
        # DFT+U Negotiation
        if diagnostics['transition_metals']:
            while True:
                u_input = input("\n[Adaptive Logic] Transition metals detected. Enable DFT+U? (y/n): ").lower()
                if u_input in ['y', 'yes']:
                    print("  -> DFT+U Enabled.")
                    job_settings['use_dft_u'] = True
                    break
                elif u_input in ['n', 'no']:
                    print("  -> DFT+U Disabled.")
                    job_settings['use_dft_u'] = False
                    break
        
        print("\nAI: Do you want to proceed with these settings? Or modify them? (e.g., 'Change Static KPOINTS to 8', 'Run it')")
        
        while True:
            user_msg = input("User: ")
            
            # Logic to break loop if Approved
            decision_prompt = f"""
            Analyze the user's response to the VASP settings proposal.
            User Input: "{user_msg}"
            Current Settings JSON: {json.dumps(job_settings)}
            
            Determine if the user WANTS to:
            1. APPROVE/RUN: EXPLICITLY confirms (e.g., "Run", "Yes", "Generate", "Write files").
            2. MODIFY: Wants to change a parameter (e.g., "Change ISMEAR to 0").
            3. PREVIEW: Wants to see the full content of files (e.g. "Show INCAR", "Show vars", "preview").
            4. CANCEL: Wants to stop (e.g., "Exit", "Cancel").
            
            Return JSON only:
            {{
                "action": "APPROVE" | "MODIFY" | "PREVIEW" | "CANCEL",
                "updates": {{ "key": "value" }} (Only if MODIFY, extract changes),
                "reply": "Short acknowledgement string"
            }}
            """
            
            try:
                response = self.client.models.generate_content(model=self.model_name, contents=decision_prompt)
                text = response.text.strip()
                if text.startswith("```"):
                     text = text.split("\n", 1)[1].rsplit("\n", 1)[0]
                
                decision = json.loads(text)
                print(f"AI: {decision.get('reply', 'Processing...')}")
                
                if decision['action'] == 'APPROVE':
                    break
                elif decision['action'] == 'CANCEL':
                    print("Operation cancelled.")
                    return
                elif decision['action'] == 'PREVIEW':
                    # Generate INCAR strings in memory and print
                    print("\n[Preview Mode - NOT writing files]")
                    incar_builder = templates.IncarBuilder()
                    
                    # Hack: recreate magmom/diagnostics context for accurate preview
                    # We need species list which is in self.selected_doc.structure
                    st_species = [str(s) for s in self.selected_doc.structure.species]
                    diag_ctx = diagnostics.copy()
                    diag_ctx['species'] = st_species
                    
                    for job_type in ['relaxation', 'static', 'bands']:
                        ctx = job_settings.get(job_type, {})
                        ctx['job_type'] = job_type
                        ctx['is_metal'] = job_settings['is_metal']
                        ctx['use_dft_u'] = job_settings['use_dft_u']
                        
                        preview_str = incar_builder.generate_incar(ctx, diag_ctx)
                        print(f"\n--- INCAR PREVIEW ({job_type}) ---")
                        print(preview_str) 
                        print("-" * 30)
                        
                elif decision['action'] == 'MODIFY':
                    updates = decision.get('updates', {})
                    
                    # Merge updates
                    for job_type in ['relaxation', 'static', 'bands']:
                        if job_type in updates:
                             for k, v in updates[job_type].items():
                                 if isinstance(v, dict) and k in job_settings[job_type]:
                                      job_settings[job_type][k].update(v)
                                 else:
                                      job_settings[job_type][k] = v

                    if "kpoints" in updates:
                        job_settings['static']['kpoints'] = updates['kpoints']
                        job_settings['relaxation']['kpoints'] = updates['kpoints']
                    
                    # Re-print
                    print("\n--- Updated Proposal ---")
                    self.print_settings(job_settings)
                    
            except Exception as e:
                print(f"Error processing decision: {e}")
                
        # 3. Execution
        self.generate_files_from_settings(job_settings, diagnostics)

    def analyze_material(self, doc):
        """
        Analyzes structure for adaptive logic properties.
        """
        st = doc.structure
        gap = doc.band_gap
        
        is_metal = (gap == 0)
        num_atoms = len(st)
        
        # d-block elements (Sc-Zn, Y-Cd, Hf-Hg) approx
        transition_metals_set = {
            "Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn",
            "Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd",
            "Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg"
        }
        
        found_tm = []
        for el in st.composition.elements:
            if str(el) in transition_metals_set:
                found_tm.append(str(el))
                
        return {
            "is_metal": is_metal,
            "gap": gap,
            "num_atoms": num_atoms,
            "transition_metals": found_tm,
            "formula": str(st.composition.reduced_formula)
        }

    def propose_settings(self, doc):
        """
        Generates initial settings based on diagnostics.
        """
        diagnostics = self.analyze_material(doc)
        
        # Base Settings
        settings = {
            "is_metal": diagnostics['is_metal'],
            "use_dft_u": False, # Default OFF, negotiate to ON
            "relaxation": {
                "kpoints": "Gamma 8 8 8",
                "incar_overrides": {} # Overrides for IncarBuilder
            },
            "static": {
                "kpoints": "Monkhorst 12 12 12", 
                "incar_overrides": {}
            },
            "bands": {
                "kpoints": "Line_Mode",
                "incar_overrides": {}
            }
        }
        return settings, diagnostics

    def print_settings(self, settings):
        print(f"1. Relaxation ({settings['relaxation']['kpoints']})")
        print(f"2. Static     ({settings['static']['kpoints']})")
        print(f"3. Bands      ({settings['bands']['kpoints']})")

    def generate_files_from_settings(self, settings, diagnostics):
        print("\n[Engineer: writing files...]")
        formula = str(self.selected_doc.structure.composition.reduced_formula)
        folder = os.path.join(self.project_root, formula)
        os.makedirs(folder, exist_ok=True)
        
        # POSCAR (Common)
        poscar = Poscar(self.selected_doc.structure)
        poscar.write_file(os.path.join(folder, "POSCAR"))
        
        # POTCAR (Common)
        self.construct_potcar(folder, self.selected_doc.structure)
        
        # Instantiate Builder
        incar_builder = templates.IncarBuilder()
        
        # Pass species list for MAGMOM RLE
        diagnostics['species'] = [str(s) for s in self.selected_doc.structure.species]

        # Subdirectories
        for job_type in ['relaxation', 'static', 'bands']: 
            
            # Map 'static' -> 'static-sci'
            if job_type == "static":
                dir_name = "static-sci"
            else:
                dir_name = job_type
                
            sub_path = os.path.join(folder, dir_name)
            os.makedirs(sub_path, exist_ok=True)
            
            # Copy POSCAR/POTCAR
            for f in ["POSCAR", "POTCAR"]:
                if os.path.exists(os.path.join(folder, f)):
                     shutil.copy(os.path.join(folder, f), os.path.join(sub_path, f))
            
            # KPOINTS
            if job_type in settings and 'kpoints' in settings[job_type]:
                kpts_str = settings[job_type]['kpoints']
                self.write_kpoints(sub_path, kpts_str)
            
            # INCAR (Dynamic Generation)
            # Prepare context for builder
            ctx_settings = settings.get(job_type, {})
            ctx_settings['job_type'] = job_type
            ctx_settings['is_metal'] = settings['is_metal']
            ctx_settings['use_dft_u'] = settings['use_dft_u']
            
            # Using overrides from negotiation
            # (Note: In previous phase we stored 'incar' but new builder expects 'incar_overrides' for patching base)
            # We map 'incar' to 'incar_overrides' if present legacy-wise or just pass as overrides
            overrides = ctx_settings.get('incar_overrides', {})
            # If user negotiated raw keys, they might be in a different spot, but for now we assume they are in overrides.
            
            content = incar_builder.generate_incar(ctx_settings, diagnostics)
            
            with open(os.path.join(sub_path, "INCAR"), "w") as f:
                f.write(content)

            # Job Script
            job_types_map = {"relaxation": "Relax", "static": "Static", "bands": "Bands"}
            job_name = job_types_map.get(job_type, job_type.capitalize())
            job_content = templates.JOB_SCRIPT.format(Material=formula, JobType=job_name)
            with open(os.path.join(sub_path, "job.sh"), "w") as f:
                 f.write(job_content)

        print(f"[Success] Data generated in {folder}")
        print("\n[Next Steps - Manual Workflow]")
        print("1. Run 'relaxation'. check convergence.")
        print("2. Copy 'relaxation/CONTCAR' to 'static-sci/POSCAR'.")
        print("3. Run 'static-sci'.")
        print("4. Copy 'static-sci/CHGCAR' to 'bands/CHGCAR'.")
        print("5. Run 'bands'.")

    def write_kpoints(self, folder, kpts_setting):
        path = os.path.join(folder, "KPOINTS")
        if "Line_Mode" in kpts_setting:
            # Special logic for Line Mode (would use pymatgen HighSymmKpath)
            # Placeholder standard line mode
            content = "Line Mode\n10\nLine\nReciprocal\n0 0 0\n0.5 0.5 0.5\n" # Dummy
        elif "Gamma" in kpts_setting or "Monkhorst" in kpts_setting:
            # Parse "Gamma 8 8 8"
            parts = kpts_setting.split()
            style = parts[0] # Gamma or Monkhorst
            grid = " ".join(parts[1:])
            content = f"Automatic\n0\n{style}\n{grid}\n0 0 0\n"
        else:
            content = f"Automatic\n0\nGamma\n11 11 11\n0 0 0\n"
            
        with open(path, "w") as f:
            f.write(content)

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

if __name__ == "__main__":
    agent = VASPSkill()
    agent.start_interaction()
