import os
import subprocess
import random
import secrets
from pathlib import Path

from .template_processor import TemplateProcessor
from .file_manager import FileManager

class ExerciseDeployer:
    """
    Handles deployment of CTF exercises to VMs.
    Manages file copying, flag generation, and directory creation.
    """
    
    def __init__(self, config, template_processor, file_manager):
        """
        Initialize the deployer.
        
        Args:
            config (dict): Global configuration
            template_processor (TemplateProcessor): Template processor for variable substitution
            file_manager (FileManager): File manager for file operations
        """
        self.config = config
        self.template_processor = template_processor
        self.file_manager = file_manager
        
    def deploy_exercises(self, vm_name, vm_config, config_dir, category_name, force=False):
        """
        Deploy exercises to a VM.
        
        Args:
            vm_name (str): Name of the VM
            vm_config (dict): VM configuration
            config_dir (str): Configuration directory
            category_name (str): Category name
            force (bool): Whether to force overwrite existing files
        """
        base_path = self.config['exercises']['base_path']
        category_path = f"{base_path}/{category_name}"

        # Deploy each exercise
        for ex_id in vm_config['exercises']:
            ex_id = int(ex_id) if isinstance(ex_id, str) and ex_id.isdigit() else ex_id
            ex = self.config['exercises']['configs'].get(ex_id)
            if not ex:
                continue
                
            service_name = ex['name']
            print(f"Processing exercise {service_name}...")
            
            # Create exercise path on VM
            exercise_path = f"{category_path}/{service_name}"
                        
            # Create flag directory and deploy flag if needed
            deploy_flags = ex.get('deploy_flags', True)
            if deploy_flags:
                self._execute_vm_command(vm_name, ['mkdir', '-p', f"{exercise_path}/flag"])
                self._deploy_flag(vm_name, exercise_path, force)
            
            # Copy exercise files
            self._deploy_exercise_files(vm_name, ex, config_dir, exercise_path, force)
    
    def _execute_vm_command(self, vm_name, command, check=True):
        """
        Execute a command on a VM.
        
        Args:
            vm_name (str): Name of the VM
            command (list): Command to execute
            check (bool): Whether to check for errors
            
        Returns:
            subprocess.CompletedProcess: Result of the command
        """
        return subprocess.run(
            ['lxc', 'exec', vm_name, '--'] + command,
            check=check,
            capture_output=not check
        )
    
    def _deploy_flag(self, vm_name, exercise_path, force):
        """
        Deploy a flag file to an exercise.
        
        Args:
            vm_name (str): Name of the VM
            exercise_path (str): Path to the exercise
            force (bool): Whether to force overwrite existing files
        """
        # Generate flag
        flag = self.template_processor.functions['generate_flag']()
        flag_path = f"{exercise_path}/flag/flag.txt"
        
        # Create temporary file with flag
        temp_path = self.file_manager.create_temp_file(flag)
        
        try:
            # Push flag to VM
            self.file_manager.safe_push_file(vm_name, temp_path, flag_path, force=force)
            
            # Set permissions
            self._execute_vm_command(vm_name, ['sudo', 'chmod', '444', flag_path])
            self._execute_vm_command(vm_name, ['sudo', 'chown', 'root:root', flag_path])
            
            print(f"Deployed container flag to: {flag_path}")
        finally:
            # Clean up temp file
            self.file_manager.remove_temp_file(temp_path)
    
    def _deploy_exercise_files(self, vm_name, ex, config_dir, exercise_path, force):
        """
        Deploy exercise files to a VM.
        
        Args:
            vm_name (str): Name of the VM
            ex (dict): Exercise configuration
            config_dir (str): Configuration directory
            exercise_path (str): Path to the exercise
            force (bool): Whether to force overwrite existing files
        """
        # Get build path
        build_path = ex.get('build', f"./{ex['name']}")
        if isinstance(build_path, dict):
            build_path = build_path.get('context', f"./{ex['name']}")
        
        if build_path.startswith('./'):
            build_path = build_path[2:]
        
        full_build_path = os.path.join(config_dir, build_path)
        print(f"Looking for build files in: {full_build_path}")
        
        # Check if build directory exists
        local_exercise = Path(full_build_path)
        if not local_exercise.exists():
            print(f"WARNING: Build directory not found: {local_exercise}")
            return
        
        print(f"Found build directory: {local_exercise}")
        
        # Get template files and variables
        template_files = ex.get('template_files', [])
        template_vars = ex.get('template_vars', {})
        
        # Process and deploy files
        for file in local_exercise.rglob('*'):
            if not file.is_file():
                continue
                
            relative_path = file.relative_to(local_exercise)
            remote_path = f"{exercise_path}/{relative_path}"
            
            # Check if this file needs templating
            if str(relative_path) in template_files:
                print(f"Processing template file: {relative_path}")
                
                # Read the file content
                with open(file, 'r') as f:
                    content = f.read()
                
                # Process the template
                processed_content = self.template_processor.process_string(content, template_vars)
                
                # Create temporary file with processed content
                temp_path = self.file_manager.create_temp_file(processed_content)
                
                try:
                    # Push file to VM
                    self.file_manager.safe_push_file(vm_name, temp_path, remote_path, force=force)
                finally:
                    # Clean up temp file
                    self.file_manager.remove_temp_file(temp_path)
            else:
                # Push file as-is
                self.file_manager.safe_push_file(vm_name, str(file), remote_path, force=force)
        
        print(f"Copied all files for {ex['name']}")
    
    def deploy_host_flag(self, vm_name, vm_config):
        """
        Deploy a flag to the host VM if configured.
        
        Args:
            vm_name (str): Name of the VM
            vm_config (dict): VM configuration
        """
        # Check if host flag is enabled
        host_flag_used = vm_config.get('host_flag', False)
        if not host_flag_used:
            return
        
        # Generate flag
        flag = self.template_processor.functions['generate_flag']()
        
        # Determine flag path
        if vm_config.get('host_flag_random', False):
            # Generate a random path
            base_dirs = [
                '/var/log', '/usr/local/share', '/etc', '/opt', '/home', 
                '/var', '/var/opt', '/var/lib', '/usr/local/bin', '/usr/bin'
            ]
            base = random.choice(base_dirs)
            subdir = f".{secrets.token_hex(4)}"
            filename = f".flag_{secrets.token_hex(4)}.txt"
            host_flag_path = os.path.join(base, subdir, filename)
            print(f"Generated random flag path: {host_flag_path}")
        else:
            # Use specified path or default
            host_flag_path = vm_config.get('host_flag_path', '/root/flag.txt')
        
        # Create temporary file with flag
        temp_path = self.file_manager.create_temp_file(flag)
        
        try:
            # Create parent directory
            parent_dir = os.path.dirname(host_flag_path)
            self._execute_vm_command(vm_name, ['sudo', 'mkdir', '-p', parent_dir])
            
            # Push flag to VM
            self.file_manager.safe_push_file(vm_name, temp_path, '/tmp/host_flag.txt', force=True)
            
            # Move to final location and set permissions
            self._execute_vm_command(vm_name, ['sudo', 'mv', '/tmp/host_flag.txt', host_flag_path])
            self._execute_vm_command(vm_name, ['sudo', 'chown', 'root:root', host_flag_path])
            self._execute_vm_command(vm_name, ['sudo', 'chmod', '444', host_flag_path])
            
            print(f"Deployed host flag to: {host_flag_path}")
        finally:
            # Clean up temp file
            self.file_manager.remove_temp_file(temp_path)
    
    def deploy_service_files(self, vm_name):
        """
        Deploy service files to a VM.
        
        Args:
            vm_name (str): Name of the VM
        """
        # Deploy ctf-service.py
        with open('ctf-service.py', 'r') as f:
            content = f.read()
        
        temp_path = self.file_manager.create_temp_file(content)
        try:
            self.file_manager.safe_push_file(vm_name, temp_path, '/tmp/ctf-service.py', force=True)
        finally:
            self.file_manager.remove_temp_file(temp_path)
        
        # Deploy ctf.service
        with open('ctf.service', 'r') as f:
            content = f.read()
        
        temp_path = self.file_manager.create_temp_file(content)
        try:
            self.file_manager.safe_push_file(vm_name, temp_path, '/tmp/ctf.service', force=True)
        finally:
            self.file_manager.remove_temp_file(temp_path)
        
        # Move files to correct locations and set permissions
        self._execute_vm_command(vm_name, ['sudo', 'mv', '/tmp/ctf-service.py', '/usr/local/bin/ctf-service.py'])
        self._execute_vm_command(vm_name, ['sudo', 'chmod', '+x', '/usr/local/bin/ctf-service.py'])
        self._execute_vm_command(vm_name, ['sudo', 'mv', '/tmp/ctf.service', '/etc/systemd/system/ctf.service'])
    
    def configure_systemd_service(self, vm_name):
        """
        Configure the systemd service on a VM.
        
        Args:
            vm_name (str): Name of the VM
        """
        self._execute_vm_command(vm_name, ['sudo', 'systemctl', 'daemon-reload'])
        self._execute_vm_command(vm_name, ['sudo', 'systemctl', 'enable', 'ctf.service'])
        self._execute_vm_command(vm_name, ['sudo', 'systemctl', 'restart', 'ctf.service'])

