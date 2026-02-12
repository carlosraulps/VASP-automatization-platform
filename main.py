
import os
import sys
import time
import subprocess
from dotenv import load_dotenv

# Ensure we can import from vasp_platform
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vasp_platform.src.translator.agent import TranslatorAgent
from vasp_platform.src.manager import daemon, connection

def print_header():
    print("========================================")
    print("   VASP AUTOMATION PLATFORM (v2.0)      ")
    print("========================================")

def run_deploy():
    """
    Mode 1: Deploy & Updater
    Checks environment, installs dependencies, restarts daemon, and manages git status.
    """
    print("\n[DEPLOYMENT & UPDATER]")
    
    # 1. Environment & Credentials
    print("\n🔍 Checking Environment...")
    required_vars = ['GOOGLE_API_KEY', 'MP_API_KEY', 'PROJECT_ROOT', 'POTENTIALS_DIR']
    missing = [v for v in required_vars if not os.environ.get(v)]
    
    if missing:
        print(f"❌ Missing Environment Variables: {', '.join(missing)}")
    else:
        print("✅ Environment Variables: OK")

    # 2. Dependencies (Auto-Install)
    if os.path.exists("requirements.txt"):
        print("\n📦 Checking Dependencies...")
        try:
            # Install quietly, upgrade if needed
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Dependencies Installed/Updated")
        except subprocess.CalledProcessError as e:
            print(f"❌ Dependency Installation Failed: {e}")
            
    # 3. SSH Connection
    print("\n⏳ Testing SSH Connection...")
    try:
        conn = connection.ClusterConnection()
        res = conn.run_command("echo 'Connection Successful'", hide=True)
        if res and res.ok:
            print(f"✅ SSH Connection ({conn.host}): OK")
        else:
            print(f"❌ SSH Connection ({conn.host}): FAILED")
    except Exception as e:
        print(f"❌ SSH Connection Error: {e}")

    # 4. Daemon Management
    print("\n🔄 Service Management")
    if input("Restart 'vasp-manager' systemd service? (y/n): ").strip().lower() == 'y':
        try:
            print("   Running: sudo systemctl restart vasp-manager")
            subprocess.run(["sudo", "systemctl", "restart", "vasp-manager"], check=True)
            print("✅ Service Restarted Successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to restart service. (Ensure sudo access and service exists)")
            print("   Template available: /etc/systemd/system/vasp-manager.service")

    # 5. Version Control (Git)
    print("\n🚀 Version Control")
    if input("Commit and Push all changes? (y/n): ").strip().lower() == 'y':
        msg = input("   Commit Message: ").strip()
        if msg:
            try:
                subprocess.run(["git", "add", "."], check=True)
                subprocess.run(["git", "commit", "-m", msg], check=True)
                print("✅ Changes Committed")
                
                if input("   Push to remote? (y/n): ").strip().lower() == 'y':
                    subprocess.run(["git", "push"], check=True)
                    print("✅ Changes Pushed")
            except subprocess.CalledProcessError as e:
                print(f"❌ Git Operation Failed: {e}")

def run_translator():
    """
    Mode 2: Translator (The Consultant)
    Runs the AI Agent to generate VASP inputs.
    """
    print("\n[TRANSLATOR MODE]")
    project_root = os.environ.get('PROJECT_ROOT')
    potentials_dir = os.environ.get('POTENTIALS_DIR')
    
    agent = TranslatorAgent(project_root, potentials_dir)
    manifest = agent.start_consultation_loop()
    
    if manifest:
        print("\n✅ Job Manifest Created!")
        print(f"   Save Path: {os.path.join(project_root, 'manifests')}")
        
        # Optional: Handoff to manager immediately
        choice = input("\nDo you want to switch to Manager Mode now? (y/n): ").strip().lower()
        if choice == 'y':
            daemon.main()
    else:
        print("\n(Session ended without job creation)")

def run_manager():
    """
    Mode 3: Manager (The Executor)
    Starts the persistent daemon loop.
    """
    print("\n[MANAGER MODE]")
    print("Starting Daemon Loop...")
    daemon.main()

def main():
    load_dotenv()
    
    # Check if run with flags (e.g. for systemd)
    if "--manager" in sys.argv:
        run_manager()
        return

    while True:
        print_header()
        print("1. Deploy (Health Check & Setup)")
        print("2. Translator (Create VASP Inputs)")
        print("3. Manager (Start Daemon Integration)")
        print("q. Quit")
        
        choice = input("\nSelect Option: ").strip().lower()
        
        if choice == '1':
            run_deploy()
            input("\nPress Enter to return to menu...")
        elif choice == '2':
            run_translator()
            # Translator might end session, loop back to menu
        elif choice == '3':
            run_manager()
            # Manager is an infinite loop, so we won't return unless it crashes or breaks
        elif choice == 'q':
            print("Goodbye.")
            break
        else:
            print("Invalid option.")
            time.sleep(1)

if __name__ == "__main__":
    main()
