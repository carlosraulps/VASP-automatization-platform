# Templates for VASP Input Files

INCAR_STATIC = """# --- SYSTEM & ELECTRONIC ---
SYSTEM  = {Material} Static SCF
ENCUT   = 400
EDIFF   = 1.0e-06
PREC    = Normal
ISPIN   = 2
MAGMOM  = {MAGMOM}
ISYM    = 0

# --- SLAB CORRECTIONS ---
LDIPOL  = .TRUE.
IDIPOL  = 3

# --- PARALLELIZATION ---
NCORE   = 2

# --- STATIC CALCULATION ---
IBRION  = -1
NSW     = 0
ISIF    = 2

# --- OUTPUTS ---
LWAVE   = .TRUE.
LCHARG  = .TRUE.
LORBIT  = 11

# --- CONVERGENCE ---
LREAL   = Auto
ALGO    = Fast
NELM    = 100
ISMEAR  = 0
SIGMA   = 0.05
"""

INCAR_BANDS = """# --- SYSTEM & ELECTRONIC ---
SYSTEM  = {Material} Band Structure
ENCUT   = 400
EDIFF   = 1.0e-06
PREC    = Normal
ISPIN   = 2
MAGMOM  = {MAGMOM}
ISYM    = 0

# --- SLAB CORRECTIONS ---
LDIPOL  = .TRUE.
IDIPOL  = 3

# --- PARALLELIZATION ---
NCORE   = 2

# --- STATIC SETTINGS ---
IBRION  = -1
NSW     = 0
ISIF    = 2

# --- ALGORITHM ---
LREAL   = Auto
ALGO    = Normal
NELM    = 100

# --- BAND SETTINGS ---
ICHARG  = 11     # Read charge from static run
LWAVE   = .FALSE.
LCHARG  = .FALSE.
LORBIT  = 11
ISMEAR  = 0
SIGMA   = 0.05
NEDOS   = 2000
"""

JOB_SCRIPT = """#!/bin/bash
#SBATCH -J {Material}_{JobType}
#SBATCH -o job.%j.out
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --time=168:00:00
#SBATCH -p normal

export OMP_NUM_THREADS=1
mpirun -np $SLURM_NTASKS vasp_std > run.log 2>&1
"""

class IncarBuilder:
    def __init__(self):
        self.base_config = {
            "PREC": "Normal",
            "ENCUT": 400,
            "EDIFF": "1.0e-06",
            "ISPIN": 2,
            "ISYM": 0,
            "NCORE": 2,
            "LREAL": "Auto",
            "ALGO": "Fast"
        }

    def format_magmom(self, structure_info):
        """
        Generates Run-Length Encoded MAGMOM string (e.g., '8*4.0 8*0.6')
        """
        magmoms = []
        # We need the actual structure species list to group correctly.
        # Use structure_info['species'] which we need to make sure is passed
        species_list = structure_info.get('species', [])
        
        if not species_list:
            return structure_info.get('magmom', '') # Fallback

        # Heuristic assignment
        raw_moments = []
        tm_set = {"Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn",
                  "Y","Zr","Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd",
                  "Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg"}
        
        for sp in species_list:
             el = "".join([c for c in sp if c.isalpha()]) # Remove oxidation state numbers if any
             if el in tm_set:
                 raw_moments.append(4.0) # High spin default
             else:
                 raw_moments.append(0.6)

        # Run-Length Encoding using itertools.groupby
        from itertools import groupby
        parts = []
        for val, group in groupby(raw_moments):
            count = sum(1 for _ in group)
            parts.append(f"{count}*{val}")
            
        return " ".join(parts)

    def generate_incar(self, settings, structure_info):
        """
        Generates INCAR string based on settings and structure info.
        settings: dict containing 'job_type', 'incar_overrides', 'is_metal', 'use_dft_u', etc.
        structure_info: dict containing 'num_atoms', 'formula', 'magmom', 'species'
        """
        job_type = settings.get('job_type', 'static')
        is_metal = settings.get('is_metal', False)
        use_dft_u = settings.get('use_dft_u', False)
        
        # Start with base
        incar = self.base_config.copy()
        incar['SYSTEM'] = f"{structure_info.get('formula', 'System')} {job_type.capitalize()}"
        
        # MAGMOM RLE
        incar['MAGMOM'] = self.format_magmom(structure_info)

        # Job Type Specifics
        if job_type == 'relaxation':
            incar.update({
                "IBRION": 2,
                "NSW": 50,
                "ISIF": 3,
                "EDIFFG": -0.01,
                "LWAVE": ".FALSE.",
                "LCHARG": ".FALSE."
            })
        elif job_type == 'static':
            incar.update({
                "IBRION": -1,
                "NSW": 0,
                "LWAVE": ".TRUE.",
                "LCHARG": ".TRUE.",
                "ALGO": "Normal", # Physics Fix
                "LREAL": ".FALSE." # Physics Fix
            })
        elif job_type == 'bands':
            incar.update({
                "IBRION": -1,
                "NSW": 0,
                "ICHARG": 11,
                "LWAVE": ".FALSE.",
                "LCHARG": ".FALSE.",
                "ALGO": "Normal", # Physics Fix
                "LREAL": ".FALSE." # Physics Fix
            })

        # Logic Rule 1: Smearing
        if is_metal:
            incar['ISMEAR'] = 1
            incar['SIGMA'] = 0.2
        else:
            if job_type == 'static':
                incar['ISMEAR'] = -5 # Tetrahedron
            else:
                incar['ISMEAR'] = 0  # Gaussian
                incar['SIGMA'] = 0.05

        # Logic Rule 2: DFT+U
        if use_dft_u:
            incar['LDAU'] = ".TRUE."
            incar['LDAUTYPE'] = 2
            incar['LMAXMIX'] = 4
            # Simplified U-value placeholder
            # In production, this needs mapping to specific LDAUU/LDAUL

        # Logic Rule 3: Precision (LREAL) - Only applied if not already set strictly above
        # But allow small cell override if strictly small
        num_atoms = structure_info.get('num_atoms', 100)
        if num_atoms < 10:
             incar['LREAL'] = ".FALSE."

        # Apply Overrides
        overrides = settings.get('incar_overrides', {})
        incar.update(overrides)

        # Build String
        out = []
        out.append(f"# --- Generated by IncarBuilder for {job_type} ---")
        for k, v in incar.items():
            if v: # Only write non-empty
                out.append(f"{k:<8} = {v}")
        
        return "\n".join(out)
