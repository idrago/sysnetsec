#!/usr/bin/env python3
import yaml
import os
import paramiko
import secrets
import ipaddress
from pathlib import Path
import random
import argparse

class CTFExercise:
    def __init__(self, exercise_id: int, config: dict, category_name: str):
        self.id = exercise_id
        self.config = config
        self.category_name = category_name
        self.name = f'{self.category_name}_{exercise_id:02d}'
        self.exercise_config = self._get_exercise_config()

    def _get_exercise_config(self):
        """Get exercise-specific configuration."""
        # Get base exercise config
        exercise_config = self.config['exercises']['configs'].get(int(self.id), {})
        
        # If empty, try with string ID
        if not exercise_config:
            exercise_config = self.config['exercises']['configs'].get(str(self.id), {})
        
        # If we have a config, merge with default capabilities
        if exercise_config:
            # Get default capabilities
            capabilities = self.config['exercises']['capabilities'].copy()
            # Update with exercise-specific capabilities if they exist
            if 'capabilities' in exercise_config:
                for key, value in exercise_config['capabilities'].items():
                    if key == 'add':
                        capabilities['add'] = list(set(capabilities['add'] + value))
                    else:
                        capabilities[key] = value
            # Add capabilities back to exercise config
            exercise_config['capabilities'] = capabilities
            
        return exercise_config

    def get_ip_address(self, used_ips=None):
        """Get IP address for the exercise."""
        if used_ips is None:
            used_ips = set()

        # Case 1: Exercise has /32 address
        if 'address' in self.exercise_config:
            address = self.exercise_config['address']['ip']
            if '/32' in address:
                return address.split('/')[0]
            # Case 2: Exercise has specific range
            network = ipaddress.ip_network(address)
            available_ips = set(str(ip) for ip in network.hosts()) - used_ips
        else:
            # Case 3: Use default range
            network = ipaddress.ip_network(self.config['exercises']['default_address']['ip'])
            available_ips = set(str(ip) for ip in network.hosts()) - used_ips
        
        if not available_ips:
            raise ValueError(f"No available IPs in network {network}")
        
        ip = random.choice(list(available_ips))
        used_ips.add(ip)
        return ip

    def generate_flag(self):
        """Generate a unique flag for this exercise."""
        return f"flag{{{secrets.token_hex(16)}}}\n"

class VMGroup:
    def __init__(self, name: str, config: dict, pattern: dict):
        self.name = name
        self.config = config
        self.pattern = pattern
        
        # Get the base network, either from group config or pattern
        base_ip = config.get('base_ip', pattern.get('base_ip'))
        if not base_ip:
            raise ValueError(f"No base IP found for VM group {name}")
        
        self.base_network = ipaddress.ip_network(base_ip)

    def get_vms(self):
        """Generate list of VM configurations based on range."""
        start, end = self.config['range']
        vms = []

        for i in range(start, end + 1):
            # Calculate IP address
            ip = str(self.base_network[i])
            
            # Get VM suffix, either from group config or pattern
            vm_suffix = self.config.get('vm_suffix', self.pattern.get('vm_suffix', 'vm1'))
            
            # Generate SSH key path
            ssh_key = self.config['ssh_key_template'].format(
                vagrant_path=self.pattern['vagrant_path'],
                student_prefix=self.pattern['student_prefix'],
                vm_suffix=vm_suffix,
                id=str(i).zfill(2),
                vm_provider=self.pattern['vm_provider']
            )

            vms.append({
                'ip': ip,
                'ssh_user': self.config['ssh_user'],
                'ssh_key': ssh_key,
                'exercises': self.config['exercises'],
                'vm_type': vm_suffix  # Store VM type for reference
            })

        return vms

class CTFDeployment:
    def __init__(self, config_file='config.yaml', category_name=None):
        self.config = self._load_config(config_file)
        self.category_name = category_name or self.config.get('category_name', 'ctf_exercise')
        
    def _load_config(self, config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def generate_docker_compose(self, vm_config):
        """Generate docker-compose.yml for a specific VM."""
        network_name = self.config['network']['name']
        compose = {
            'networks': {
                network_name: {
                    'name': network_name,
                    'external': True  # Mark the network as external since we create it separately
                }
            },
            'services': {}
        }

        used_ips = set()
        for exercise_id in vm_config['exercises']:
            ex = CTFExercise(exercise_id, self.config, self.category_name)
            
            # Network configuration
            network_config = {
                network_name: {}
            }
            ip_address = ex.get_ip_address(used_ips)
            if ip_address:
                network_config[network_name]['ipv4_address'] = ip_address

            # Start with default service configuration from global settings
            default_service_config = self.config.get('service_defaults', {})

            # Create base service config with required settings
            service_config = {
                'container_name': ex.name,
                'hostname': ex.name,
                'networks': network_config,
            }

            # Add build context if not explicitly set to false in exercise config
            if ex.exercise_config.get('build', True) is not False:
                service_config['build'] = ex.exercise_config.get('build_context', f'./{ex.name}')

            # Merge in global default service settings
            for key, value in default_service_config.items():
                # Skip network settings as we've already set them
                if key != 'networks':
                    service_config[key] = value
            
            # Add standard volumes if flag and hints are enabled
            volumes = []
            
            # Add flag volume if flag is enabled for this exercise and flag is in container
            if ex.exercise_config.get('flag_enabled', True) and ex.exercise_config.get('flag_in_container', True):
                flag_path = ex.exercise_config.get('flag_path', '/root/flag.txt')
                flag_mount = ex.exercise_config.get('flag_mount', 
                    f"{self.config['exercises']['base_path']}/{ex.name}/flag/flag.txt:{flag_path}:ro")
                volumes.append(flag_mount)
            
            # Add hints volume if hints are enabled for this exercise
            if ex.exercise_config.get('hints_enabled', True):
                hints_path = ex.exercise_config.get('hints_path', '/home/student/hints')
                hints_mount = ex.exercise_config.get('hints_mount',
                    f"{self.config['exercises']['base_path']}/{ex.name}/hints:{hints_path}:ro")
                volumes.append(hints_mount)
            
            # Set volumes in service config if we have any
            if volumes:
                service_config['volumes'] = volumes
            
            # Override with exercise-specific configuration
            for key, value in ex.exercise_config.items():
                # Skip special keys used internally or already processed
                if key not in ['flag_enabled', 'hints_enabled', 'flag_path', 'hints_path', 
                               'flag_mount', 'hints_mount', 'build', 'build_context', 'flag_in_container']:
                    
                    # For volumes, append rather than overwrite
                    if key == 'volumes' and 'volumes' in service_config:
                        service_config['volumes'].extend(value)
                    # For capabilities, use the merged values from _get_exercise_config
                    elif key == 'capabilities':
                        service_config['cap_drop'] = value['drop']
                        service_config['cap_add'] = value['add']
                    # For all other keys, just set the value
                    elif key not in ['name', 'description', 'address']:  # Skip metadata fields
                        service_config[key] = value
            
            compose['services'][ex.name] = service_config
            
        return compose
    
    def deploy_to_vm(self, vm_config):
        """Deploy exercises to a specific VM."""
        print(f"Deploying to {vm_config['ip']} ({vm_config['vm_type']})...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                vm_config['ip'],
                username=vm_config['ssh_user'],
                key_filename=os.path.expanduser(vm_config['ssh_key'])
            )
            
            sftp = ssh.open_sftp()

            # First deploy all exercise files and docker-compose
            compose_config = self.generate_docker_compose(vm_config)
            with open('/tmp/docker-compose.yml', 'w') as f:
                yaml.dump(compose_config, f, 
                        default_flow_style=False, 
                        sort_keys=False,
                        allow_unicode=True,
                        canonical=False)
            
            # Check if any VM-level flags need to be deployed
            vm_flags = self.config.get('vm_flags', {})
            for flag_name, flag_config in vm_flags.items():
                if vm_config['vm_type'] in flag_config.get('vm_types', []) or 'all' in flag_config.get('vm_types', []):
                    # Create directory for the flag
                    flag_dir = flag_config.get('path', '/root').rsplit('/', 1)[0]
                    ssh.exec_command(f"sudo mkdir -p {flag_dir}")
                    
                    # Generate flag content
                    flag_prefix = flag_config.get('prefix', self.config.get('flag_prefix', self.category_name.upper()))
                    flag_content = f"flag{{{flag_prefix}_{secrets.token_hex(16)}}}\n"
                    
                    # Create temporary flag file
                    with open('/tmp/vm_flag.txt', 'w') as f:
                        f.write(flag_content)
                    
                    # Copy flag to VM
                    sftp.put('/tmp/vm_flag.txt', '/tmp/vm_flag.txt')
                    
                    # Move flag to destination with proper permissions
                    flag_path = flag_config.get('path', '/root/flag.txt')
                    ssh.exec_command(f"sudo mv /tmp/vm_flag.txt {flag_path}")
                    ssh.exec_command(f"sudo chmod {flag_config.get('permissions', '400')} {flag_path}")
                    ssh.exec_command(f"sudo chown {flag_config.get('owner', 'root:root')} {flag_path}")
                    
                    print(f"Deployed VM-level flag '{flag_name}' to {vm_config['ip']} at {flag_path}")
            
            for exercise_id in vm_config['exercises']:
                ex = CTFExercise(exercise_id, self.config, self.category_name)
                
                # Skip flag deployment if flag is at VM level for this exercise
                should_deploy_container_flag = ex.exercise_config.get('flag_in_container', True)
                
                # Create remote directories
                ssh.exec_command(
                    f"mkdir -p {self.config['exercises']['base_path']}/{ex.name}/{{flag,hints}}"
                )
                
                # Generate and copy flag if needed for container
                if should_deploy_container_flag and ex.exercise_config.get('flag_enabled', True):
                    flag = ex.generate_flag()
                    flag_path = f"{self.config['exercises']['base_path']}/{ex.name}/flag/flag.txt"
                    flag_file = sftp.file(flag_path, 'w')
                    flag_file.write(flag)
                    flag_file.close()
                    
                    # Set proper permissions for flag file
                    ssh.exec_command(f"chmod 400 {flag_path}")
                
                # Copy exercise files and hints
                local_path = Path(f'./{ex.name}')
                if local_path.exists():
                    # Copy main exercise files
                    for file in local_path.rglob('*'):
                        if file.is_file():
                            remote_path = f"{self.config['exercises']['base_path']}/{ex.name}/{file.relative_to(local_path)}"
                            sftp.put(str(file), remote_path)
                    
                    # Copy hints specifically
                    hints_path = local_path / 'hints'
                    if hints_path.exists() and ex.exercise_config.get('hints_enabled', True):
                        for hint_file in hints_path.rglob('*'):
                            if hint_file.is_file():
                                remote_hint_path = f"{self.config['exercises']['base_path']}/{ex.name}/hints/{hint_file.relative_to(hints_path)}"
                                sftp.put(str(hint_file), remote_hint_path)
                                # Set appropriate permissions for hint files
                                ssh.exec_command(f"chmod 644 {remote_hint_path}")
                
            # Copy docker-compose.yml
            sftp.put('/tmp/docker-compose.yml', f"{self.config['exercises']['base_path']}/docker-compose.yml")
            
            # Now set up the systemd service for future reboots
            sftp.put('ctf-service.py', '/tmp/ctf-service.py')
            sftp.put('ctf.service', '/tmp/ctf.service')
            
            ssh.exec_command('sudo mv /tmp/ctf-service.py /usr/local/bin/ctf-service.py')
            ssh.exec_command('sudo chmod +x /usr/local/bin/ctf-service.py')
            ssh.exec_command('sudo mv /tmp/ctf.service /etc/systemd/system/ctf.service')
            
            # Initial start of containers
            ssh.exec_command(f"cd {self.config['exercises']['base_path']} && docker compose up -d")
            
            # Enable service for future reboots
            ssh.exec_command('sudo systemctl daemon-reload')
            ssh.exec_command('sudo systemctl enable ctf.service')
            ssh.exec_command('sudo systemctl start ctf.service')
            
            print(f"Deployment to {vm_config['ip']} ({vm_config['vm_type']}) completed successfully.")
            
        except Exception as e:
            print(f"Error deploying to {vm_config['ip']} ({vm_config['vm_type']}): {str(e)}")
        finally:
            if 'sftp' in locals():
                sftp.close()
            ssh.close()
    
def main():
    parser = argparse.ArgumentParser(description='Deploy CTF exercises to VMs')
    parser.add_argument('--config', default='config.yaml', help='Path to configuration file')
    parser.add_argument('--category', help='Category name for exercises (e.g., access_control, docker_escape)')
    args = parser.parse_args()
    
    deployment = CTFDeployment(config_file=args.config, category_name=args.category)
    
    # Process each VM group
    for group_name, group_config in deployment.config['vms']['groups'].items():
        vm_group = VMGroup(group_name, group_config, deployment.config['vms']['pattern'])
        
        # Deploy to each VM in the group
        for vm in vm_group.get_vms():
            deployment.deploy_to_vm(vm)

if __name__ == '__main__':
    main()