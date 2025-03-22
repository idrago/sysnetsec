import os
import subprocess
import tempfile

class FileManager:
    """
    Handles file operations between local and remote systems.
    Provides methods for safe file transfers and permission management.
    """
    
    def __init__(self):
        """Initialize the file manager."""
        self.temp_files = []
    
    def __del__(self):
        """Clean up any temporary files on destruction."""
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    def safe_push_file(self, vm_name, local_path, remote_path, force=False, verbose=False):
        """
        Safely push a file to an LXC VM, handling permissions.
        
        Args:
            vm_name (str): Name of the VM
            local_path (str): Local path to the file
            remote_path (str): Remote path on the VM
            force (bool): Whether to force overwrite existing files
            verbose (bool): Whether to print verbose output
        """
        try:
            # Check if file exists and handle appropriately
            result = subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'test', '-e', remote_path],
                capture_output=True
            )
            file_exists = result.returncode == 0
            
            if file_exists:
                if force:
                    # Make sure we have write permissions
                    subprocess.run(
                        ['lxc', 'exec', vm_name, '--', 'chmod', '644', remote_path],
                        check=True
                    )
                else:
                    if verbose:
                        print(f"Skipping existing file: {remote_path}")
                    return
            else:
                # File doesn't exist, make sure parent directory exists
                parent_dir = os.path.dirname(remote_path)
                subprocess.run(
                    ['lxc', 'exec', vm_name, '--', 'mkdir', '-p', parent_dir],
                    check=True
                )
            
            # Push file to VM
            subprocess.run(
                ['lxc', 'file', 'push', local_path, f"{vm_name}{remote_path}"],
                check=True
            )
            
            # Set permissions based on file type
            if remote_path.endswith('.sh') or '/bin/' in remote_path:
                subprocess.run(
                    ['lxc', 'exec', vm_name, '--', 'chmod', '755', remote_path],
                    check=True
                )
            else:
                subprocess.run(
                    ['lxc', 'exec', vm_name, '--', 'chmod', '644', remote_path],
                    check=True
                )
                
            if verbose:
                print(f"Copied: {local_path} -> {remote_path}")
                
        except subprocess.SubprocessError as e:
            print(f"Error copying {local_path} to {remote_path}: {str(e)}")
            raise
    
    def create_temp_file(self, content):
        """
        Create a temporary file with the given content.
        
        Args:
            content (str): Content to write to the file
            
        Returns:
            str: Path to the temporary file
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
            self.temp_files.append(temp_path)
            return temp_path
    
    def remove_temp_file(self, path):
        """
        Remove a temporary file.
        
        Args:
            path (str): Path to the temporary file
        """
        if path in self.temp_files:
            os.unlink(path)
            self.temp_files.remove(path)


