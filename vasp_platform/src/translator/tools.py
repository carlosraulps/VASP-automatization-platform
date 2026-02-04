import os
from mp_api.client import MPRester
from dotenv import load_dotenv

class TranslatorTools:
    def __init__(self):
        load_dotenv()
        self.mp_api_key = os.environ.get('MP_API_KEY')
        if not self.mp_api_key:
            print("Warning: MP_API_KEY not found.")

    def analyze_crystallography(self, doc):
        """
        Truth Layer: Exact crystallography data to prevent hallucinations.
        """
        st = doc.structure
        lat = st.lattice
        
        # 1. System Truth
        system = "Unknown"
        if doc.symmetry:
            system = str(doc.symmetry.crystal_system).capitalize()
        
        # 2. Angles Truth
        angles = f"alpha={lat.alpha:.1f}, beta={lat.beta:.1f}, gamma={lat.gamma:.1f}"
        
        # 3. Dimensionality Heuristic
        is_slab = False
        if lat.c > 20.0:
            is_slab = True
            
        dims = f"a={lat.a:.2f}, b={lat.b:.2f}, c={lat.c:.2f}"
            
        return {
            "system": system,
            "lattice_angles": angles,
            "dimensions": dims,
            "is_slab": is_slab
        }

    def search_mp(self, formula: str):
        if not self.mp_api_key:
             return None
             
        try:
             with MPRester(self.mp_api_key) as mpr:
                 docs = mpr.materials.summary.search(
                     formula=formula, 
                     fields=["material_id", "structure", "symmetry", "band_gap", "is_stable"]
                 )
                 return docs
        except Exception as e:
            print(f"[MP Error] {e}")
            return None
    
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
            "formula": str(st.composition.reduced_formula),
            "species": [str(s) for s in st.species]
        }
