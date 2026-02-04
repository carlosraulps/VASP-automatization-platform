
import os
import sys
import json
import shutil
import argparse
from mp_api.client import MPRester
from pymatgen.io.vasp import Poscar, Potcar
from pymatgen.core import Structure
import templates

# Load Configuration
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

PROJECT_ROOT = CONFIG['PROJECT_ROOT']
POTENTIALS_DIR = CONFIG['POTENTIALS_DIR']
API_KEY_ENV_VAR = CONFIG['API_KEY_ENV_VAR']

def get_api_key():
    api_key = os.environ.get(API_KEY_ENV_VAR)
    if not api_key:
        print(f"Error: {API_KEY_ENV_VAR} environment variable not set.")
        sys.exit(1)
    return api_key

def phase_a_structure_retrieval(formula, api_key):
    print(f"Phase A: Retrieving structure for {formula}...")
    with MPRester(api_key) as mpr:
        docs = mpr.materials.summary.search(formula=formula, fields=["material_id", "structure", "symmetry"])
    
    if not docs:
        print(f"No structures found for {formula}.")
        sys.exit(1)

    print("Available options:")
    sorted_docs = sorted(docs, key=lambda x: x.material_id)
    for i, doc in enumerate(sorted_docs):
        crystal_system = doc.symmetry.crystal_system if doc.symmetry else "Unknown"
        print(f"{i+1}. {formula} ({doc.material_id}) - {crystal_system}")
    
    while True:
        try:
            choice = int(input("Select structure number: "))
            if 1 <= choice <= len(sorted_docs):
                selected_doc = sorted_docs[choice - 1]
                break
            else:
                print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")

    material_folder = os.path.join(PROJECT_ROOT, formula)
    os.makedirs(material_folder, exist_ok=True)
    
    poscar_path = os.path.join(material_folder, "POSCAR")
    poscar = Poscar(selected_doc.structure)
    poscar.write_file(poscar_path)
    print(f"Structure saved to {poscar_path}")
    
    return material_folder, selected_doc.structure

def phase_b_potential_construction(material_folder, structure):
    print("Phase B: Constructing POTCAR...")
    elements = [str(el) for el in structure.composition.elements]
    potcar_files = []

    for el in elements:
        # Priority mapping: Try _sv, then standard
        potential_path = None
        # Check specific mappings if needed, for now logic is:
        # Look for {Element}_sv, then {Element}_d (if Ga?), then {Element}
        # The prompt says: "Map: Check the potentials/ directory for the best match. Prefer _sv (semi-valence) or standard versions unless specified."
        # "Example: If Ga, look for Ga_d or Ga"
        
        candidates = [f"{el}_sv", f"{el}_d", f"{el}"]
        found = False
        for cand in candidates:
            path = os.path.join(POTENTIALS_DIR, cand, "POTCAR")
            if os.path.exists(path):
                potcar_files.append(path)
                print(f"  Found potential for {el}: {cand}")
                found = True
                break
        
        if not found:
            print(f"  Warning: No suitable potential found for {el} in {POTENTIALS_DIR}")
            # Try to find any folder starting with el? No, strictly follow directory structure.
            # Fail gracefully?
            sys.exit(f"Error: Missing potential for {el}")

    # Concatenate
    dest_potcar = os.path.join(material_folder, "POTCAR")
    with open(dest_potcar, 'wb') as outfile:
        for fname in potcar_files:
            with open(fname, 'rb') as infile:
                outfile.write(infile.read())
    print(f"POTCAR created at {dest_potcar}")

def phase_c_staging_configuration(material_folder, formula):
    print("Phase C: Staging and Configuration...")
    subdirs = ["static-scf", "bands"]
    
    files_to_copy = ["POSCAR", "POTCAR"]
    # Generate KPOINTS if not exists? Prompt says "Copy: POSCAR, POTCAR, and KPOINTS".
    # Wait, KPoint generation was listed in "Workflow" but not explicitly detailed in "Phase A" or "Phase B" instructions, 
    # except "Copy: POSCAR, POTCAR, and KPOINTS into both subdirectories."
    # I need to generate KPOINTS first.
    # I will generate a standard KPOINTS file.
    
    kpoints_path = os.path.join(material_folder, "KPOINTS")
    with open(kpoints_path, "w") as f:
        f.write("Automatic Mesh\n0\nGamma\n11 11 11\n0 0 0\n")
    files_to_copy.append("KPOINTS")

    for sub in subdirs:
        sub_path = os.path.join(material_folder, sub)
        os.makedirs(sub_path, exist_ok=True)
        
        for file in files_to_copy:
            src = os.path.join(material_folder, file)
            dst = os.path.join(sub_path, file)
            if os.path.exists(src):
                shutil.copy(src, dst)
        
        # Write INCAR
        incar_template = templates.INCAR_STATIC if sub == "static-scf" else templates.INCAR_BANDS
        # Generate MAGMOM string
        # Simple logic: 0.6 for all atoms for now, or per prompt "Generate standard magnetic moments based on elements"
        # Since I don't have a complex logic table, I will set a placeholder or read structure.
        # Let's use a dummy default for now, or based on structure if available (I didn't pass structure here).
        # We can re-read POSCAR or pass structure.
        # Let's pass structure to this function.
        
        # Write job.sh
        job_template = templates.JOB_SCRIPT
        job_type = "Static" if sub == "static-scf" else "Bands"
        
        # Populate templates
        # Need MAGMOM.
        # Let's read structure from POSCAR in the folder to be safe, or pass it.
        # I'll pass structure in next iteration, for now let's just use structure from Phase A.
        pass

def generate_magmom(structure):
    # Simple heuristic
    magmoms = []
    for site in structure.species:
        # Very basic defaults
        if str(site) in ["Fe", "Co", "Ni"]:
            magmoms.append("2.0")
        else:
            magmoms.append("0.6") # Default small moment
    return " ".join(magmoms)

def main():
    parser = argparse.ArgumentParser(description="VASP Translator Skill Automation")
    parser.add_argument("formula", help="Chemical formula (e.g., GaAs)")
    parser.add_argument("--test-connection", action="store_true", help="Test API connectivity only")
    
    args = parser.parse_args()
    api_key = get_api_key()

    if args.test_connection:
        print(f"Testing connection for {args.formula}...")
        with MPRester(api_key) as mpr:
             docs = mpr.materials.summary.search(formula=args.formula, fields=["material_id", "structure"])
        print(f"Connection successful. Found {len(docs)} structures.")
        return

    # Phase A
    material_folder, structure = phase_a_structure_retrieval(args.formula, api_key)

    # Phase B
    phase_b_potential_construction(material_folder, structure)

    # Phase C
    # We need to finish Phase C logic
    
    # Generate KPOINTS (Gamma centered 11x11x11 auto)
    kpoints_path = os.path.join(material_folder, "KPOINTS")
    with open(kpoints_path, "w") as f:
        f.write("Automatic Mesh\n0\nGamma\n11 11 11\n0 0 0\n") # Simple default
    
    subdirs = ["static-scf", "bands"]
    files_to_copy = ["POSCAR", "POTCAR", "KPOINTS"]

    magmom_str = " ".join(["2.0"] * len(structure)) # Fallback if not using element specific
    # Better MAGMOM
    magmom_str = generate_magmom(structure)

    for sub in subdirs:
        sub_path = os.path.join(material_folder, sub)
        os.makedirs(sub_path, exist_ok=True)
        
        for file in files_to_copy:
            src = os.path.join(material_folder, file)
            dst = os.path.join(sub_path, file)
            if os.path.exists(src):
                shutil.copy(src, dst)
        
        # Write INCAR
        if sub == "static-scf":
            content = templates.INCAR_STATIC.format(Material=args.formula, MAGMOM=magmom_str)
        else:
            content = templates.INCAR_BANDS.format(Material=args.formula, MAGMOM=magmom_str)
        
        with open(os.path.join(sub_path, "INCAR"), "w") as f:
            f.write(content)
            
        # Write job.sh
        job_type = "Static" if sub == "static-scf" else "Bands"
        job_content = templates.JOB_SCRIPT.format(Material=args.formula, JobType=job_type)
        with open(os.path.join(sub_path, "job.sh"), "w") as f:
            f.write(job_content)

    print(f"Process complete. Data staged in {material_folder}")

if __name__ == "__main__":
    main()
