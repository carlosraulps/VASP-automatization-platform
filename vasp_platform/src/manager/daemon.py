
import os
import time
import subprocess
from dotenv import load_dotenv
from .connection import ClusterConnection
from .workflow import VaspWorkflow

# Configuration
QUEUE_DIR = "/opt/manager-vasp/queue"
REMOTE_BASE_DIR = "/scratch/user/vasp_jobs" # Adjust as needed

def sync_to_remote(local_folder: str, remote_folder: str, connection: ClusterConnection):
    """
    Syncs a local folder to the remote cluster using rsync over SSH.
    """
    # Example rsync command (needs specific key setup or ssh config)
    # We use -e to specify proxy jump if needed, or rely on .ssh/config
    # Ideally, we use the connection object to facilitate this, but rsync is a binary.
    # We assume 'huk' is configured in .ssh/config
    
    cmd = [
        "rsync", "-avz",
        local_folder,
        f"{connection.host}:{remote_folder}"
    ]
    
    print(f"Syncing {local_folder} to {connection.host}:{remote_folder}...")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Rsync failed: {e}")
        return False

def main():
    load_dotenv()
    
    # Ensure queue dir exists
    if not os.path.exists(QUEUE_DIR):
        print(f"Creating queue directory: {QUEUE_DIR}")
        os.makedirs(QUEUE_DIR, exist_ok=True)
        
    print("Initializing Manager Agent Daemon...")
    
    # Initialize Connection
    try:
        conn = ClusterConnection()
        workflow = VaspWorkflow(conn)
        print("Connected to Cluster.")
    except Exception as e:
        print(f"Fatal Connection Error: {e}")
        return

    print(f"Watching {QUEUE_DIR} for new jobs...")
    
    while True:
        try:
            # 1. Scan Local Queue
            jobs = [f for f in os.listdir(QUEUE_DIR) if os.path.isdir(os.path.join(QUEUE_DIR, f))]
            
            for job_name in jobs:
                local_path = os.path.join(QUEUE_DIR, job_name)
                remote_path = os.path.join(REMOTE_BASE_DIR, job_name)
                
                # 2. Sync
                if sync_to_remote(local_path, REMOTE_BASE_DIR, conn):
                    # 3. Trigger Workflow
                    workflow.process_folder(remote_path)
                
            # 4. Sleep
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("Stopping Daemon.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
