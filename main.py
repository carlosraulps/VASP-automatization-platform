import os
import sys
from dotenv import load_dotenv

# Ensure we can import from vasp_platform
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vasp_platform.src.translator.agent import TranslatorAgent

def main():
    # 1. Load Environment
    load_dotenv()
    
    project_root = os.environ.get('PROJECT_ROOT')
    potentials_dir = os.environ.get('POTENTIALS_DIR')
    
    if not project_root:
        print("Critical: PROJECT_ROOT not set in .env")
        return

    # 2. Initialize Agent
    agent = TranslatorAgent(project_root, potentials_dir)
    
    # 3. Operations Loop
    manifest = agent.start_consultation_loop()
    
    # 4. Handoff
    if manifest:
        print("\n" + "="*40)
        print("JOB MANIFEST CREATED (Ready for Manager)")
        print("="*40)
        print(manifest.model_dump_json(indent=2))
        print("="*40)
    else:
        print("Session ended without job creation.")

if __name__ == "__main__":
    main()
