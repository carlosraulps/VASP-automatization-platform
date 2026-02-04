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
