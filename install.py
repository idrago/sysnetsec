#!/usr/bin/env python3
import yaml
import os
import paramiko
import secrets
import ipaddress
from pathlib import Path
import argparse
import time
import random

def load_config(config_file='config.yaml'):
    """Load the configuration file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def generate_flag():
    """Generate a unique flag for an exercise."""
    return f"flag{{CTF_{secrets.token_hex(16)}}}\n"

def generate_docker_compose(config, vm_config, category_name):
    """Generate a simplified docker-compose.yml for a VM."""
    network_name = config['network']['name']
    compose = {
        'networks': {
            network_name: {
                'name': network_name,
                'external': False
            }
        },
        'services': {}
    }
    
    # Get default service config
    defaults = config.get('service_defaults', {})
    
    for ex_id in vm_config['exercises']:
        ex_id = int(ex_id) if isinstance(ex_id, str) and ex_id.isdigit() else ex_id
        ex = config['exercises']['configs'].get(ex_id)
        if not ex:
            continue
            
        service_name = ex['name']
        
        # Start with default settings
        service = {}
        for key, value in defaults.items():
            service[key] = value
        
        # Basic service settings
        service['container_name'] = service_name
        service['hostname'] = service_name
        
        # Set build context
        if 'build' in ex:
            service['build'] = f"./{service_name}"  # Updated path to include category subfolder
        else:
            service['build'] = f"./{service_name}"
        
        # Network config
        ip = ex.get('address', '').split('/')[0] if 'address' in ex else None
        service['networks'] = {network_name: {}}
        if ip:
            service['networks'][network_name]['ipv4_address'] = ip
        
        # Add volumes for flag and hints
        service['volumes'] = [
            f"{config['exercises']['base_path']}/{category_name}/{service_name}/hints:/home/student/hints:ro"
        ]
        
        # Add flag volume only if not using host_flag
        deploy_flags = ex.get('deploy_flags', True)
        if deploy_flags:
            # Use specified flag path if available, otherwise use default
            flag_path = ex.get('flag_path', '/root/flag.txt')
            service['volumes'].append(
                f"{config['exercises']['base_path']}/{category_name}/{service_name}/flag/flag.txt:{flag_path}:ro"
            )
        
        # Add exercise-specific volumes if defined
        if 'volumes' in ex:
            service['volumes'].extend(ex['volumes'])
            
        # Add ports if defined
        if 'ports' in ex:
            service['ports'] = ex['ports']
        
        # Add environment variables if defined
        if 'environment' in ex:
            service['environment'] = ex['environment']
        
        # Add capability overrides if specified
        if 'cap_add' in ex:
            service['cap_add'] = ex['cap_add']
        
        # Add service to compose file
        compose['services'][service_name] = service
        
    return compose

def get_random_file_path():
    """Generate a random file path for hiding a flag on the host VM."""
    base_dirs = [
        '/var/log',
        '/usr/local/share',
        '/etc',
        '/opt',
        '/home',
        '/var',
        '/var/opt',
        '/var/lib',
        '/usr/local/bin',
        '/usr/bin'
    ]
    
    # Choose a random base directory
    base = random.choice(base_dirs)
    
    # Generate a random subdirectory/filename
    subdir = f".{secrets.token_hex(4)}"
    filename = f".flag_{secrets.token_hex(4)}.txt"
    
    return os.path.join(base, subdir, filename)

def safe_put(sftp, local_path, remote_path, ssh, force=False, verbose=False):
    """Safely put a file on a remote server, handling permissions."""
    try:
        # Check if file exists and handle appropriately
        try:
            sftp.stat(remote_path)
            # File exists, handle according to force flag
            if force:
                # Create a backup if forcing overwrite
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                backup_path = f"{remote_path}.{timestamp}.bak"
                if verbose:
                    print(f"Backing up existing file: {remote_path} -> {backup_path}")
                ssh.exec_command(f"cp {remote_path} {backup_path}")
                
                # Make sure we have write permissions
                ssh.exec_command(f"chmod 644 {remote_path}")
            else:
                if verbose:
                    print(f"Skipping existing file: {remote_path}")
                return
        except IOError:
            # File doesn't exist, make sure parent directory exists
            parent_dir = os.path.dirname(remote_path)
            ssh.exec_command(f"mkdir -p {parent_dir}")
        
        # Create temporary file with guaranteed permissions
        temp_path = f"/tmp/{os.path.basename(remote_path)}.{secrets.token_hex(8)}"
        sftp.put(local_path, temp_path)
        
        # Move to final destination, handling permissions
        ssh.exec_command(f"mv {temp_path} {remote_path}")
        
        # Set permissions based on file type
        if remote_path.endswith('.sh') or '/bin/' in remote_path:
            ssh.exec_command(f"chmod 755 {remote_path}")
        elif '/hints/' in remote_path:
            ssh.exec_command(f"chmod 644 {remote_path}")
        else:
            ssh.exec_command(f"chmod 644 {remote_path}")
            
        if verbose:
            print(f"Copied: {local_path} -> {remote_path}")
            
    except Exception as e:
        print(f"Error copying {local_path} to {remote_path}: {str(e)}")
        raise

def deploy_to_vm(config, vm_config, config_dir, category_name, force=False):
    """Deploy exercises to a VM."""
    print(f"Deploying {category_name} exercises to {vm_config['ip']} ({vm_config['vm_suffix']})...")
    
    try:
        # Connect to the VM
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            vm_config['ip'],
            username=vm_config['ssh_user'],
            key_filename=os.path.expanduser(vm_config['ssh_key'])
        )
        
        sftp = ssh.open_sftp()
        
        # Create category directory
        base_path = config['exercises']['base_path']
        category_path = f"{base_path}/{category_name}"
        ssh.exec_command(f"mkdir -p {category_path}")
        
        # Generate and deploy docker-compose.yml
        compose = generate_docker_compose(config, vm_config, category_name)
        with open('/tmp/docker-compose.yml', 'w') as f:
            yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
        
        compose_path = f"{category_path}/docker-compose.yml"
        safe_put(sftp, '/tmp/docker-compose.yml', compose_path, ssh, force=True)
        
        # Track if host flag is used for any exercises in this VM
        host_flag_used = vm_config.get('host_flag', False)
        host_flag_path = vm_config.get('host_flag_path', None)
        host_flag_random = vm_config.get('host_flag_random', False)
        host_flag_content = None
        
        # Generate a flag for the host if needed (only generate one flag per VM)
        if host_flag_used:
            host_flag_content = generate_flag()
            
            # Determine where to put the flag
            if host_flag_random:
                host_flag_path = get_random_file_path()
                print(f"Generated random flag path: {host_flag_path}")
            elif not host_flag_path:
                host_flag_path = "/root/flag.txt"
                
            # Create flag file
            with open('/tmp/host_flag.txt', 'w') as f:
                f.write(host_flag_content)
                
            # Create directory for flag if it doesn't exist
            ssh.exec_command(f"sudo mkdir -p {os.path.dirname(host_flag_path)}")
            
            # Copy flag to VM
            safe_put(sftp, '/tmp/host_flag.txt', '/tmp/host_flag.txt', ssh, force=True)
            
            # Move to final destination with correct permissions (using sudo)
            ssh.exec_command(f"sudo mv /tmp/host_flag.txt {host_flag_path}")
            ssh.exec_command(f"sudo chown root:root {host_flag_path}")
            ssh.exec_command(f"sudo chmod 400 {host_flag_path}")
            
            print(f"Deployed host flag to: {host_flag_path}")
        
        # Deploy exercises
        for ex_id in vm_config['exercises']:
            ex_id = int(ex_id) if isinstance(ex_id, str) and ex_id.isdigit() else ex_id
            ex = config['exercises']['configs'].get(ex_id)
            if not ex:
                continue
                
            service_name = ex['name']
            print(f"Processing exercise {service_name}...")
            
            # Create exercise directories
            exercise_path = f"{category_path}/{service_name}"
            ssh.exec_command(f"mkdir -p {exercise_path}/{{flag,hints}}")
            
            # Handle flag deployment for containers
            deploy_flags = ex.get('deploy_flags', True)
            if deploy_flags:
                flag = generate_flag()
                flag_path = f"{exercise_path}/flag/flag.txt"
                with open('/tmp/flag.txt', 'w') as f:
                    f.write(flag)
                safe_put(sftp, '/tmp/flag.txt', flag_path, ssh, force=True)
                ssh.exec_command(f"sudo chmod 400 {flag_path}")
                ssh.exec_command(f"sudo chown root:root {host_flag_path}")
                print(f"Deployed container flag to: {flag_path}")

            # Get the build path - either from the build field or use service_name
            build_path = ex.get('build', f"./{service_name}")
            if isinstance(build_path, dict):
                # If build is a dictionary, extract the context
                build_path = build_path.get('context', f"./{service_name}")
            
            # Handle relative paths based on config file location
            if build_path.startswith('./'):
                build_path = build_path[2:]
            
            # Create full path relative to config file directory
            full_build_path = os.path.join(config_dir, build_path)
            print(f"Looking for build files in: {full_build_path}")
                
            # Copy exercise files if they exist
            local_exercise = Path(full_build_path)
            if local_exercise.exists():
                print(f"Found build directory: {local_exercise}")
                
                # Copy all files using safe_put
                for file in local_exercise.rglob('*'):
                    if file.is_file():
                        relative_path = file.relative_to(local_exercise)
                        remote_path = f"{exercise_path}/{relative_path}"
                        safe_put(sftp, str(file), remote_path, ssh, force=force, verbose=False)
                
                print(f"Copied all files for {service_name}")
            else:
                print(f"WARNING: Build directory not found: {local_exercise}")
        
        # Deploy service files
        safe_put(sftp, 'ctf-service.py', '/tmp/ctf-service.py', ssh, force=True)
        safe_put(sftp, 'ctf.service', '/tmp/ctf.service', ssh, force=True)
            
        ssh.exec_command('sudo mv /tmp/ctf-service.py /usr/local/bin/ctf-service.py')
        ssh.exec_command('sudo chmod +x /usr/local/bin/ctf-service.py')
        ssh.exec_command('sudo mv /tmp/ctf.service /etc/systemd/system/ctf.service')
            
        # Start the containers
        ssh.exec_command(f"cd {category_path} && docker compose up -d")
        ssh.exec_command('sudo systemctl daemon-reload')
        ssh.exec_command('sudo systemctl enable ctf.service')
        ssh.exec_command('sudo systemctl restart ctf.service')
        
        print(f"Deployment of {category_name} exercises to {vm_config['ip']} completed successfully")
        
    except Exception as e:
        print(f"Error deploying to {vm_config['ip']}: {str(e)}")
    finally:
        if 'sftp' in locals():
            sftp.close()
        if 'ssh' in locals():
            ssh.close()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Deploy CTF exercises to VMs')
    parser.add_argument('--config', default='config.yaml', help='Path to configuration file')
    parser.add_argument('--category', required=True, help='Category name for exercises (e.g., access_control, docker_escape)')
    parser.add_argument('--force', action='store_true', help='Force overwrite of existing files')
    args = parser.parse_args()
    
    # Get the directory containing the config file
    config_dir = os.path.dirname(os.path.abspath(args.config))
    if not config_dir:  # If config is in current directory
        config_dir = os.getcwd()
    
    print(f"Using configuration directory: {config_dir}")
    
    # Load configuration file
    config = load_config(args.config)
    
    # Process each VM group
    for group_name, group in config['vms']['groups'].items():
        start, end = group['range']
        
        # Get base network (using either ip_network or base_ip for compatibility)
        ip_network = group.get('ip_network', group.get('base_ip'))
        if not ip_network:
            # If not in group, try to get from vms.pattern
            pattern = config.get('vms', {}).get('pattern', {})
            ip_network = pattern.get('base_ip')
        
        network = ipaddress.ip_network(ip_network)
        
        # Get VM suffix
        pattern = config.get('vms', {}).get('pattern', {})
        vm_suffix = group.get('vm_suffix', pattern.get('vm_suffix', 'vm1'))
        
        # Get common VM settings
        student_prefix = config['vms'].get('student_prefix', pattern.get('student_prefix', 'student'))
        vagrant_path = config['vms'].get('vagrant_path', pattern.get('vagrant_path'))
        vm_provider = config['vms'].get('vm_provider', pattern.get('vm_provider', 'libvirt'))
        
        for i in range(start, end + 1):
            # Calculate IP address
            ip = str(network[i])
            
            # Generate SSH key path
            ssh_key_template = group.get('ssh_key', group.get('ssh_key_template'))
            ssh_key = ssh_key_template.format(
                vagrant_path=vagrant_path,
                student_prefix=student_prefix,
                vm_suffix=vm_suffix,
                id=str(i).zfill(2),
                vm_provider=vm_provider
            )
            
            vm_config = {
                'ip': ip,
                'ssh_user': group['ssh_user'],
                'ssh_key': ssh_key,
                'exercises': group['exercises'],
                'vm_suffix': vm_suffix,
                'host_flag': group.get('host_flag', False),
                'host_flag_path': group.get('host_flag_path', None),
                'host_flag_random': group.get('host_flag_random', False)
            }
            
            deploy_to_vm(config, vm_config, config_dir, args.category, force=args.force)

if __name__ == '__main__':
    main()