import os
import fabric
from fabric import Connection, Config
from invoke.exceptions import UnexpectedExit

class ClusterConnection:
    """
    Manages SSH connections to the HPC cluster via a bastion host (Gateway).
    Uses the fabric library for ensuring persistent connections and command execution.
    """
    def __init__(self, host='huk', gateway='bastiao', user=None):
        """
        Initialize the connection.
        
        Args:
            host (str): The target HPC hostname (as defined in ~/.ssh/config or IP).
            gateway (str): The jump host (bastion) to route through.
            user (str): SSH username (optional, defaults to config).
        """
        self.host = host
        self.gateway_host = gateway
        self.user = user or os.environ.get('SSH_USER')
        
        # Configure the Gateway (Jump Host)
        # We assume the gateway is accessible directly or via SSH config
        self.gateway_conn = Connection(host=self.gateway_host, user=self.user)
        
        # Configure the Target Connection through the Gateway
        self.conn = Connection(host=self.host, user=self.user, gateway=self.gateway_conn)
        
    def run_command(self, command: str, hide=True, warn=True):
        """
        Executes a shell command on the remote cluster.
        """
        try:
            result = self.conn.run(command, hide=hide, warn=warn)
            return result
        except Exception as e:
            print(f"[SSH Error] Failed to run '{command}': {e}")
            return None

    def put_file(self, local_path: str, remote_path: str):
        """
        Uploads a file to the remote cluster.
        """
        try:
            self.conn.put(local_path, remote=remote_path)
            return True
        except Exception as e:
            print(f"[SSH Error] Failed to upload {local_path}: {e}")
            return False

    def get_file(self, remote_path: str, local_path: str):
        """
        Downloads a file from the remote cluster.
        """
        try:
            self.conn.get(remote_path, local=local_path)
            return True
        except Exception as e:
            print(f"[SSH Error] Failed to download {remote_path}: {e}")
            return False

    def exists(self, remote_path: str) -> bool:
        """
        Checks if a file or directory exists on the remote system.
        """
        cmd = f"test -e {remote_path}"
        result = self.run_command(cmd, warn=True)
        return result.ok if result else False
