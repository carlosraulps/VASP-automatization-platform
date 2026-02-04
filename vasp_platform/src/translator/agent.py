import os
import json
import shutil
from typing import Optional

from pymatgen.io.vasp import Poscar

# VASP Platform Imports
from vasp_platform.schema.manifest import VaspJob, JobManifest, JobStatus, JobType
from vasp_platform.src.core.llm import GoogleGenAIAdapter
from vasp_platform.src.translator.tools import TranslatorTools
from vasp_platform.src.translator.builder import IncarBuilder, JOB_SCRIPT_TEMPLATE

class TranslatorAgent:
    def __init__(self, project_root: str, potentials_dir: str):
        self.project_root = project_root
        self.potentials_dir = potentials_dir
        
        self.llm = GoogleGenAIAdapter()
        self.tools = TranslatorTools()
        self.incar_builder = IncarBuilder()
        
        self.selected_doc = None
        self.current_materials = []
        
    def start_consultation_loop(self) -> Optional[JobManifest]:
        """
        Main interactive loop for the Translator.
        Returns a JobManifest if jobs are created, else None.
        """
        print("\n--- VASP Translator Agent (Platform v2) ---")
        
        while True:
            try:
                user_msg = input("User: ")
                if user_msg.lower() in ['exit', 'quit']:
                    return None
                
                # 1. Query Interpretation
                formula = self._interpret_request(user_msg)
                if not formula:
                    continue
                    
                # 2. Materials Search
                self.current_materials = self.tools.search_mp(formula)
                if not self.current_materials:
                    print(f"No materials found for {formula}.")
                    continue
                    
                # 3. Present Options
                self._present_options(formula)
                
                # 4. Selection
                if self._handle_selection():
                    # 5. Engineering Phase (Negotiation + Job Creation)
                    manifest = self.run_engineering()
                    if manifest:
                        return manifest
                    
                    # Reset after job creation or cancellation
                    self.selected_doc = None
                    self.current_materials = []
                    print("\nReady for next request.")
                    
            except KeyboardInterrupt:
                return None
            except Exception as e:
                print(f"[Error] {e}")
                import traceback
                traceback.print_exc()
                
    def _interpret_request(self, user_msg: str) -> Optional[str]:
        prompt = f"""
        Extract the chemical formula from: "{user_msg}"
        Return ONLY formula (e.g. GaAs) or INVALID.
        """
        result = self.llm.generate(prompt)
        if result == "INVALID":
            print("AI: Could not identify formula.")
            return None
        return result

    def _present_options(self, formula: str):
        # Gather data string
        data_str = ""
        for i, doc in enumerate(self.current_materials[:5]):
            struct = f"{doc.symmetry.crystal_system}" if doc.symmetry else "Unknown"
            data_str += f"Option {i+1}: ID={doc.material_id}, Structure={struct}, Gap={doc.band_gap:.2f}eV\n"
            
        # Get AI advice
        prompt = f"""
        Review these options for '{formula}':
        {data_str}
        Provide a ONE-sentence comment for each (stability, use case).
        Format: Option N: [Comment]
        """
        advice = self.llm.generate(prompt)
        advice_map = {}
        for line in advice.split('\n'):
            if line.startswith("Option"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    advice_map[parts[0].strip()] = parts[1].strip()
        
        print(f"{'Opt':<4} | {'ID':<15} | {'Structure':<15} | {'Gap':<6} | {'Comment'}")
        print("-" * 80)
        for i, doc in enumerate(self.current_materials[:5]):
            opt = f"Option {i+1}"
            cmt = advice_map.get(opt, "")
            print(f"{i+1:<4} | {doc.material_id:<15} | {str(doc.symmetry.crystal_system):<15} | {doc.band_gap:<6.2f} | {cmt}")

    def _handle_selection(self) -> bool:
        while True:
            sel = input("\nSelect Option # (0 to cancel): ")
            try:
                idx = int(sel)
                if idx == 0: return False
                if 1 <= idx <= len(self.current_materials):
                    self.selected_doc = self.current_materials[idx-1]
                    print(f"Selected: {self.selected_doc.material_id}")
                    return True
            except: pass
        return False

    def run_engineering(self) -> Optional[JobManifest]:
        if not self.selected_doc: return None
        
        print("\n[Engineer: Analyzing Structure...]")
        
        # 1. Diagnostics (Tools)
        diagnostics = self.tools.analyze_material(self.selected_doc)
        cryst_truth = self.tools.analyze_crystallography(self.selected_doc)
        
        # 2. Initial Proposal
        settings = self._propose_settings(diagnostics)
        
        # 3. Negotiation Loop
        if not self._negotiate_settings(settings, diagnostics, cryst_truth):
            return None
            
        # 4. Job Generation & Manifest
        manifest = self._generate_jobs(settings, diagnostics)
        return manifest

    def _propose_settings(self, diagnostics):
         return {
            "is_metal": diagnostics['is_metal'],
            "use_dft_u": False,
            "relaxation": {"kpoints": "Gamma 8 8 8", "incar_overrides": {}},
            "static": {"kpoints": "Monkhorst 12 12 12", "incar_overrides": {}},
            "bands": {"kpoints": "Line_Mode", "incar_overrides": {}}
        }

    def _negotiate_settings(self, settings, diagnostics, cryst_truth) -> bool:
        print("\n--- Strategy Proposal ---")
        print(f"[Crystallography] {cryst_truth['system']} ({cryst_truth['lattice_angles']})")
        print(f"[Chemistry] Gap: {diagnostics['gap']:.2f}eV, TM: {diagnostics['transition_metals']}")
        
        if diagnostics['transition_metals']:
             if input("\nTransition Metals detected. Enable DFT+U? (y/n): ").lower().startswith('y'):
                 settings['use_dft_u'] = True
                 print("DFT+U Enabled.")

        while True:
            self._print_settings(settings)
            user_msg = input("User (Approve/Modify/Preview): ")
            
            prompt = f"""
            Analyze user response: "{user_msg}"
            Current Settings: {json.dumps(settings)}
            Crystallography: {cryst_truth}
            
            Determine intent:
            1. APPROVE/RUN: Explicit confirmation.
            2. MODIFY: Update params.
            3. PREVIEW: Show files.
            4. CANCEL
            
            PROTOCOL: explain physics reason for modifications.
            RULES: 
            - Check Angles {cryst_truth['lattice_angles']} vs System.
            - Warn if DFT+U disabled for TM data {diagnostics['transition_metals']}.
            
            JSON: {{ "action": "...", "updates": {{...}}, "reply": "..." }}
            """
            
            resp = self.llm.generate(prompt)
            # Simple cleaning
            if "```" in resp: resp = resp.split("```")[1].replace("json\n","")
            
            try:
                dec = json.loads(resp)
                print(f"AI: {dec.get('reply', '')}")
                
                act = dec['action'] 
                if act == 'APPROVE': return True
                if act == 'CANCEL': return False
                if act == 'PREVIEW': self._preview(settings, diagnostics)
                if act == 'MODIFY':
                     # Apply updates logic
                     upd = dec.get('updates', {})
                     for k in ['relaxation','static','bands']:
                         if k in upd:
                             for sk, sv in upd[k].items():
                                 if isinstance(sv, dict) and sk in settings[k]:
                                     settings[k][sk].update(sv)
                                 else:
                                     settings[k][sk] = sv
                     if 'kpoints' in upd:
                         settings['static']['kpoints'] = upd['kpoints']
                         settings['relaxation']['kpoints'] = upd['kpoints']
            except Exception as e:
                print(f"Error parsing AI: {e}")
                
    def _print_settings(self, settings):
        u = "On" if settings.get('use_dft_u') else "Off"
        print(f"\n1. Relax ({settings['relaxation']['kpoints']}) [U={u}]")
        print(f"2. Static ({settings['static']['kpoints']}) [U={u}]")
        print(f"3. Bands ({settings['bands']['kpoints']}) [U={u}]")

    def _preview(self, settings, diagnostics):
        print("\n--- PREVIEW ---")
        # Prepare context
        st_species = diagnostics['species'] # passed from tools
        diag_ctx = diagnostics.copy()
        
        for jt in ['relaxation', 'static']:
             ctx = settings[jt].copy()
             ctx['job_type'] = jt
             ctx['is_metal'] = settings['is_metal']
             ctx['use_dft_u'] = settings['use_dft_u']
             print(f"--- {jt.upper()} INCAR ---")
             print(self.incar_builder.generate_incar(ctx, diag_ctx))

    def _generate_jobs(self, settings, diagnostics) -> JobManifest:
        print("\n[Engineer: Generating VaspJob Manifest...]")
        manifest = JobManifest(
            project_root=self.project_root
        )
        
        formula = diagnostics['formula']
        folder = os.path.join(self.project_root, formula)
        os.makedirs(folder, exist_ok=True)
        
        # 1. Base Files (POSCAR/POTCAR)
        poscar_path = os.path.join(folder, "POSCAR")
        Poscar(self.selected_doc.structure).write_file(poscar_path)
        self._write_potcar(folder, self.selected_doc.structure)
        
        # 2. Create Jobs
        # Pass species for Magmom
        diag_ctx = diagnostics.copy()
        
        for job_type in ['relaxation', 'static', 'bands']:
            # Directory Map
            dir_name = "static-scf" if job_type == "static" else job_type
            sub_path = os.path.join(folder, dir_name)
            os.makedirs(sub_path, exist_ok=True)
            
            # Copy Dependencies
            for f in ["POSCAR", "POTCAR"]:
                if os.path.exists(os.path.join(folder, f)):
                     shutil.copy(os.path.join(folder, f), os.path.join(sub_path, f))
            
            # KPOINTS
            kpts = settings[job_type]['kpoints']
            self._write_kpoints(sub_path, kpts)
            
            # INCAR
            ctx = settings[job_type].copy()
            ctx['job_type'] = job_type
            ctx['is_metal'] = settings['is_metal']
            ctx['use_dft_u'] = settings['use_dft_u']
            
            incar_content = self.incar_builder.generate_incar(ctx, diag_ctx)
            with open(os.path.join(sub_path, "INCAR"), "w") as f:
                f.write(incar_content)

            # Job Script
            jname = job_type.capitalize()
            script = JOB_SCRIPT_TEMPLATE.format(Material=formula, JobType=jname)
            with open(os.path.join(sub_path, "job.sh"), "w") as f:
                f.write(script)
                
            # Add to Manifest
            job = VaspJob(
                material_id=str(self.selected_doc.material_id),
                formula=formula,
                directory_path=sub_path,
                job_type=JobType(job_type) if job_type in ['relaxation','static','bands'] else JobType.STATIC,
                parameters={"kpoints": kpts, "dft_u": settings['use_dft_u']},
                status=JobStatus.CREATED
            )
            manifest.jobs.append(job)
            
        print(f"Jobs generated in {folder}")
        return manifest

    def _write_kpoints(self, folder, setting):
        path = os.path.join(folder, "KPOINTS")
        content = "Automatic\n0\nGamma\n1 1 1\n0 0 0" # Default
        if "Gamma" in setting or "Monkhorst" in setting:
             parts = setting.split()
             content = f"Automatic\n0\n{parts[0]}\n{' '.join(parts[1:])}\n0 0 0"
        elif "Line_Mode" in setting:
             content = "Line Mode\n10\nLine\nReciprocal\n0 0 0\n0.5 0.5 0.5" # Simplified
             
        with open(path, "w") as f:
             f.write(content)

    def _write_potcar(self, folder, structure):
        # reuse POTENTIALS_DIR logic
        # For brevity, implementing simple concatenation if dir exists
        if not self.potentials_dir or not os.path.exists(self.potentials_dir):
            return
        
        potfiles = []
        for el in structure.composition.elements:
            # Check potential options
            for cand in [f"{el}_sv", f"{el}_d", f"{el}"]:
                p = os.path.join(self.potentials_dir, cand, "POTCAR")
                if os.path.exists(p):
                    potfiles.append(p)
                    break
        
        if potfiles:
            with open(os.path.join(folder, "POTCAR"), 'wb') as outfile:
                 for fname in potfiles:
                     with open(fname, 'rb') as infile:
                         outfile.write(infile.read())
