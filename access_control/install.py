#!/usr/bin/env python3
import yaml
import os
import paramiko
import secrets
import ipaddress
from pathlib import Path
import random

class CTFExercise:
    def __init__(self, exercise_id: int, config: dict):
        self.id = exercise_id
        self.config = config
        self.name = f'access_control_{exercise_id:02d}'
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
        return f"flag{{CTF_{secrets.token_hex(16)}}}\n"

class VMGroup:
    def __init__(self, name: str, config: dict, pattern: dict):
        self.name = name
        self.config = config
        self.pattern = pattern
        self.base_network = ipaddress.ip_network(pattern['base_ip'])

    def get_vms(self):
        """Generate list of VM configurations based on range."""
        start, end = self.config['range']
        vms = []

        for i in range(start, end + 1):
            # Calculate IP address
            ip = str(self.base_network[i])
            
            # Generate SSH key path
            ssh_key = self.config['ssh_key_template'].format(
                vagrant_path=self.pattern['vagrant_path'],
                student_prefix=self.pattern['student_prefix'],
                id=str(i).zfill(2),
                vm_provider=self.pattern['vm_provider']
            )

            vms.append({
                'ip': ip,
                'ssh_user': self.config['ssh_user'],
                'ssh_key': ssh_key,
                'exercises': self.config['exercises']
            })

        return vms

class CTFDeployment:
    def __init__(self, config_file='config.yaml'):
        self.config = self._load_config(config_file)
        
    def _load_config(self, config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)

    def generate_docker_compose(self, vm_config):
        """Generate docker-compose.yml for a specific VM."""
        network_name = self.config['network']['name']
        compose = {
            'version': '3',
            'services': {},
            'networks': {
                network_name: {
                    'name': network_name,
                    'ipam': {
                        'config': [
                            {'subnet': self.config['network']['subnet']}
                        ]
                    }
                }
            }
        }

        used_ips = set()
        for exercise_id in vm_config['exercises']:
            ex = CTFExercise(exercise_id, self.config)
            
            # Network configuration
            network_config = {
                network_name: {}
            }
            ip_address = ex.get_ip_address(used_ips)
            if ip_address:
                network_config[network_name]['ipv4_address'] = ip_address

            service_config = {
                'build': f'./{ex.name}',
                'container_name': ex.name,
                'hostname': ex.name,
                'networks': network_config,
                'volumes': [
                    f"{self.config['exercises']['base_path']}/{ex.name}/flag:/root/flag:ro",
                    f"{self.config['exercises']['base_path']}/{ex.name}/hints:/home/student/hints:ro"
                ],
                'healthcheck': self.config['exercises']['healthcheck'],
                'init': True,
                'tty': True,
                'restart': 'unless-stopped',
                'cap_drop': ex.exercise_config['capabilities']['drop'],
                'cap_add': ex.exercise_config['capabilities']['add']
            }
            
            compose['services'][ex.name] = service_config
            
        return compose

    def deploy_to_vm(self, vm_config):
        """Deploy exercises to a specific VM."""
        print(f"Deploying to {vm_config['ip']}...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                vm_config['ip'],
                username=vm_config['ssh_user'],
                key_filename=os.path.expanduser(vm_config['ssh_key'])
            )
            
            compose_config = self.generate_docker_compose(vm_config)
            with open('/tmp/docker-compose.yml', 'w') as f:
                yaml.dump(compose_config, f, 
                        default_flow_style=False, 
                        sort_keys=False,
                        allow_unicode=True,
                        canonical=False)
            
            for exercise_id in vm_config['exercises']:
                ex = CTFExercise(exercise_id, self.config)
                
                # Create remote directories
                ssh.exec_command(
                    f"mkdir -p {self.config['exercises']['base_path']}/{ex.name}/{{flag,hints}}"
                )
                
                # Generate and copy flag
                flag = ex.generate_flag()
                sftp = ssh.open_sftp()
                flag_path = f"{self.config['exercises']['base_path']}/{ex.name}/flag/flag.txt"
                flag_file = sftp.file(flag_path, 'w')
                flag_file.write(flag)
                flag_file.close()
                
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
                    if hints_path.exists():
                        for hint_file in hints_path.rglob('*'):
                            if hint_file.is_file():
                                remote_hint_path = f"{self.config['exercises']['base_path']}/{ex.name}/hints/{hint_file.relative_to(hints_path)}"
                                sftp.put(str(hint_file), remote_hint_path)
                                # Set appropriate permissions for hint files
                                ssh.exec_command(f"chmod 644 {remote_hint_path}")
                
            # Copy docker-compose.yml
            sftp.put('/tmp/docker-compose.yml', f"{self.config['exercises']['base_path']}/docker-compose.yml")
            
            # Start containers
            ssh.exec_command(f"cd {self.config['exercises']['base_path']} && docker compose up -d")
            
        except Exception as e:
            print(f"Error deploying to {vm_config['ip']}: {str(e)}")
        finally:
            ssh.close()

def main():
    deployment = CTFDeployment()
    
    # Process each VM group
    for group_name, group_config in deployment.config['vms']['groups'].items():
        vm_group = VMGroup(group_name, group_config, deployment.config['vms']['pattern'])
        
        # Deploy to each VM in the group
        for vm in vm_group.get_vms():
            deployment.deploy_to_vm(vm)

if __name__ == '__main__':
    main()