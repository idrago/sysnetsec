#!/usr/bin/env python3
import yaml
import os
import secrets
import argparse
import tempfile
import subprocess
import random
from pathlib import Path

def load_config(config_file='config.yaml'):
    """Load the configuration file."""
    with open(config_file, 'r') as f:
        return yaml.safe_load(f)

def generate_flag():
    """Generate a unique flag for an exercise."""
    return f"flag{{CTF_{secrets.token_hex(16)}}}\n"

def generate_docker_compose(config, vm_config, category_name):
    """Generate docker-compose.yml for VM, using existing network."""
    network_name = config['network']['name']
    
    # Create compose configuration that uses external network
    compose = {
        'networks': {
            network_name: {
                'external': True  # Use existing network instead of creating a new one
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
        '/var/log', '/usr/local/share', '/etc', '/opt', '/home', 
        '/var', '/var/opt', '/var/lib', '/usr/local/bin', '/usr/bin'
    ]
    
    base = random.choice(base_dirs)
    subdir = f".{secrets.token_hex(4)}"
    filename = f".flag_{secrets.token_hex(4)}.txt"
    
    return os.path.join(base, subdir, filename)

def safe_push_file(vm_name, local_path, remote_path, force=False, verbose=False):
    """Safely push a file to an LXC VM, handling permissions."""
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

def deploy_to_vm(config, vm_config, config_dir, category_name, force=False):
    """Deploy exercises to a LXD VM."""
    vm_name = f"{config['vms'].get('student_prefix', 'student')}{vm_config['id']:02d}-{vm_config['vm_suffix']}"
    print(f"Deploying {category_name} exercises to VM {vm_name}...")
    
    try:
        # Check if VM exists and is running
        result = subprocess.run(
            ['lxc', 'info', vm_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error: VM {vm_name} does not exist.")
            return
            
        if "Status: RUNNING" not in result.stdout:
            print(f"Error: VM {vm_name} is not running. Please start it first.")
            return
        
        # Create category directory
        base_path = config['exercises']['base_path']
        category_path = f"{base_path}/{category_name}"
        
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'mkdir', '-p', category_path],
            check=True
        )
        
        # Clean up any existing Docker resources
        print("Cleaning up any existing Docker resources...")
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sh', '-c', f"cd {category_path} && (docker-compose down || true)"],
            check=False
        )
        
        # Create the Docker network first to avoid conflicts
        network_name = config['network']['name']
        network_subnet = config['network'].get('subnet', '10.128.0.0/9')
        
        # Check if network already exists
        network_exists = subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sh', '-c', 
             f"docker network inspect {network_name} >/dev/null 2>&1 && echo 'EXISTS' || echo 'NOT_EXISTS'"],
            capture_output=True,
            text=True
        ).stdout.strip()
        
        if network_exists == 'NOT_EXISTS':
            print(f"Creating Docker network: {network_name} with subnet {network_subnet}")
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'sh', '-c', 
                 f"docker network create --subnet={network_subnet} {network_name}"],
                check=True
            )
        else:
            print(f"Docker network {network_name} already exists, reusing it")
        
        # Generate and deploy docker-compose.yml with external network reference
        compose = generate_docker_compose(config, vm_config, category_name)
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            yaml.dump(compose, temp_file, default_flow_style=False, sort_keys=False)
            temp_compose_path = temp_file.name
        
        compose_path = f"{category_path}/docker-compose.yml"
        safe_push_file(vm_name, temp_compose_path, compose_path, force=True)
        os.unlink(temp_compose_path)
        
        # Handle host flag deployment if needed
        host_flag_used = vm_config.get('host_flag', False)
        if host_flag_used:
            host_flag_content = generate_flag()
            host_flag_path = vm_config.get('host_flag_path', None)
            
            if vm_config.get('host_flag_random', False):
                host_flag_path = get_random_file_path()
                print(f"Generated random flag path: {host_flag_path}")
            elif not host_flag_path:
                host_flag_path = "/root/flag.txt"
                
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                temp_file.write(host_flag_content)
                temp_host_flag_path = temp_file.name
                
            # Create directory and deploy flag
            parent_dir = os.path.dirname(host_flag_path)
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'sudo', 'mkdir', '-p', parent_dir],
                check=True
            )
            
            safe_push_file(vm_name, temp_host_flag_path, '/tmp/host_flag.txt', force=True)
            os.unlink(temp_host_flag_path)
            
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'sudo', 'mv', '/tmp/host_flag.txt', host_flag_path],
                check=True
            )
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'sudo', 'chown', 'root:root', host_flag_path],
                check=True
            )
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'sudo', 'chmod', '400', host_flag_path],
                check=True
            )
            
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
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'mkdir', '-p', f"{exercise_path}/flag"],
                check=True
            )
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'mkdir', '-p', f"{exercise_path}/hints"],
                check=True
            )
            
            # Handle flag deployment for containers
            deploy_flags = ex.get('deploy_flags', True)
            if deploy_flags:
                flag = generate_flag()
                flag_path = f"{exercise_path}/flag/flag.txt"
                
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                    temp_file.write(flag)
                    temp_flag_path = temp_file.name
                
                safe_push_file(vm_name, temp_flag_path, flag_path, force=True)
                os.unlink(temp_flag_path)
                
                subprocess.run(
                    ['lxc', 'exec', vm_name, '--', 'sudo', 'chmod', '444', flag_path],
                    check=True
                )
                subprocess.run(
                    ['lxc', 'exec', vm_name, '--', 'sudo', 'chown', 'root:root', flag_path],
                    check=True
                )
                print(f"Deployed container flag to: {flag_path}")

            # Get the build path for exercise files
            build_path = ex.get('build', f"./{service_name}")
            if isinstance(build_path, dict):
                build_path = build_path.get('context', f"./{service_name}")
            
            if build_path.startswith('./'):
                build_path = build_path[2:]
            
            full_build_path = os.path.join(config_dir, build_path)
            print(f"Looking for build files in: {full_build_path}")
                
            # Copy exercise files if they exist
            local_exercise = Path(full_build_path)
            if local_exercise.exists():
                print(f"Found build directory: {local_exercise}")
                
                for file in local_exercise.rglob('*'):
                    if file.is_file():
                        relative_path = file.relative_to(local_exercise)
                        remote_path = f"{exercise_path}/{relative_path}"
                        safe_push_file(vm_name, str(file), remote_path, force=force, verbose=False)
                
                print(f"Copied all files for {service_name}")
            else:
                print(f"WARNING: Build directory not found: {local_exercise}")
        
        # Deploy service files
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            with open('ctf-service.py', 'r') as src_file:
                temp_file.write(src_file.read())
            temp_service_path = temp_file.name
        
        safe_push_file(vm_name, temp_service_path, '/tmp/ctf-service.py', force=True)
        os.unlink(temp_service_path)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            with open('ctf.service', 'r') as src_file:
                temp_file.write(src_file.read())
            temp_systemd_path = temp_file.name
            
        safe_push_file(vm_name, temp_systemd_path, '/tmp/ctf.service', force=True)
        os.unlink(temp_systemd_path)
            
        # Move files to correct locations and set permissions
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sudo', 'mv', '/tmp/ctf-service.py', '/usr/local/bin/ctf-service.py'],
            check=True
        )
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sudo', 'chmod', '+x', '/usr/local/bin/ctf-service.py'],
            check=True
        )
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sudo', 'mv', '/tmp/ctf.service', '/etc/systemd/system/ctf.service'],
            check=True
        )
        
        # Start the containers
        print(f"Starting Docker containers in {category_path}...")
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sh', '-c', f"cd {category_path} && docker-compose up -d --build"],
            check=True
        )
        
        # Enable and restart the systemd service
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sudo', 'systemctl', 'daemon-reload'],
            check=True
        )
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sudo', 'systemctl', 'enable', 'ctf.service'],
            check=True
        )
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sudo', 'systemctl', 'restart', 'ctf.service'],
            check=True
        )
        
        print(f"Deployment of {category_name} exercises to VM {vm_name} completed successfully")
        
    except subprocess.SubprocessError as e:
        print(f"Error deploying to VM {vm_name}: {str(e)}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Deploy CTF exercises to LXD VMs')
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
        
        # Get VM suffix
        vm_suffix = group.get('vm_suffix', 'vm1')
        
        for i in range(start, end + 1):
            vm_config = {
                'id': i,
                'exercises': group['exercises'],
                'vm_suffix': vm_suffix,
                'host_flag': group.get('host_flag', False),
                'host_flag_path': group.get('host_flag_path', None),
                'host_flag_random': group.get('host_flag_random', False)
            }
            
            deploy_to_vm(config, vm_config, config_dir, args.category, force=args.force)

if __name__ == '__main__':
    main()