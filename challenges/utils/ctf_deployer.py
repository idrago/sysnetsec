import os
import yaml
import secrets
import tempfile
import subprocess
import random
import ipaddress

from .template_processor import TemplateProcessor
from .file_manager import FileManager
from .docker_compose_generator import DockerComposeGenerator
from .exercise_deployer import ExerciseDeployer

class CTFDeployer:
    """
    Main class for deploying CTF exercises to LXD VMs.
    Handles configuration processing, VM management, and exercise deployment.
    """
    
    def __init__(self, config_file, category, force=False):
        """
        Initialize the deployer with configuration and parameters.
        
        Args:
            config_file (str): Path to the YAML configuration file
            category (str): Category of exercises to deploy (e.g., 'access_control')
            force (bool): Whether to force overwrite existing files
        """
        self.config_file = config_file
        self.category = category
        self.force = force
        self.config_dir = os.path.dirname(os.path.abspath(config_file))
        if not self.config_dir:  # If config is in current directory
            self.config_dir = os.getcwd()
            
        # Load configuration
        self.config = self._load_config()
        
        # Initialize template functions
        self.template_functions = {
            'generate_flag': self.generate_flag,
            'random_port': self.random_port,
            'random_range': self.random_range,
            'random_ip': self.random_ip
        }
        
        # Initialize components
        self.template_processor = TemplateProcessor(self.template_functions)
        self.file_manager = FileManager()
        self.docker_compose_generator = DockerComposeGenerator(self.config, self.template_processor)
        self.exercise_deployer = ExerciseDeployer(self.config, self.template_processor, self.file_manager)
    
    def _load_config(self):
        """Load the configuration file."""
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def deploy(self):
        """Main deployment method that processes all VM groups."""
        print(f"Using configuration directory: {self.config_dir}")
        
        # Process each VM group
        for group_name, group in self.config['vms']['groups'].items():
            self._deploy_to_group(group_name, group)
    
    def _deploy_to_group(self, group_name, group):
        """
        Deploy exercises to a group of VMs.
        
        Args:
            group_name (str): Name of the VM group
            group (dict): Group configuration
        """
        start, end = group['range']
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
            
            self._deploy_to_vm(vm_config)
    
    def _deploy_to_vm(self, vm_config):
        """
        Deploy exercises to a single VM.
        
        Args:
            vm_config (dict): VM configuration
        """
        vm_name = f"{self.config['vms'].get('student_prefix', 'student')}{vm_config['id']:02d}-{vm_config['vm_suffix']}"
        print(f"Deploying {self.category} exercises to VM {vm_name}...")
        
        try:
            # Check if VM exists and is running
            if not self._check_vm_status(vm_name):
                return
            
            # Create category directory
            base_path = self.config['exercises']['base_path']
            category_path = f"{base_path}/{self.category}"
            
            self._execute_vm_command(vm_name, ['mkdir', '-p', category_path])
            
            # Clean up any existing Docker resources
            print("Cleaning up any existing Docker resources...")
            subprocess.run(
                ['lxc', 'exec', vm_name, '--', 'sh', '-c', 
                f"[ -f {category_path}/docker-compose.yml ] && cd {category_path} && docker-compose down || true"],
                check=False
            )            
            
            # Setup Docker network
            self._setup_docker_network(vm_name)
            
            # Generate and deploy docker-compose.yml
            compose = self.docker_compose_generator.generate(vm_config, self.category)
            compose_path = f"{category_path}/docker-compose.yml"
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
                yaml.dump(compose, temp_file, default_flow_style=False, sort_keys=False)
                temp_compose_path = temp_file.name
            
            self.file_manager.safe_push_file(vm_name, temp_compose_path, compose_path, force=True)
            os.unlink(temp_compose_path)
            
            # Deploy host flag if configured
            self.exercise_deployer.deploy_host_flag(vm_name, vm_config)
            
            # Deploy individual exercises
            self.exercise_deployer.deploy_exercises(
                vm_name, 
                vm_config, 
                self.config_dir, 
                self.category, 
                self.force
            )
            
            # Deploy service files
            self.exercise_deployer.deploy_service_files(vm_name)
            
            # Start containers
            print(f"Starting Docker containers in {category_path}...")
            self._execute_vm_shell(vm_name, f"cd {category_path} && docker-compose up -d --build")
            
            # Configure systemd service
            self.exercise_deployer.configure_systemd_service(vm_name)
            
            print(f"Deployment of {self.category} exercises to VM {vm_name} completed successfully")
            
        except subprocess.SubprocessError as e:
            print(f"Error deploying to VM {vm_name}: {str(e)}")
    
    def _check_vm_status(self, vm_name):
        """
        Check if a VM exists and is running.
        
        Args:
            vm_name (str): Name of the VM
            
        Returns:
            bool: True if VM exists and is running, False otherwise
        """
        result = subprocess.run(
            ['lxc', 'info', vm_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error: VM {vm_name} does not exist.")
            return False
            
        if "Status: RUNNING" not in result.stdout:
            print(f"Error: VM {vm_name} is not running. Please start it first.")
            return False
            
        return True
    
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
    
    def _execute_vm_shell(self, vm_name, shell_command, check=True):
        """
        Execute a shell command on a VM.
        
        Args:
            vm_name (str): Name of the VM
            shell_command (str): Shell command to execute
            check (bool): Whether to check for errors
            
        Returns:
            subprocess.CompletedProcess: Result of the command
        """
        return subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sh', '-c', shell_command],
            check=check,
            capture_output=not check
        )
    
    def _setup_docker_network(self, vm_name):
        """
        Set up the Docker network on the VM.
        
        Args:
            vm_name (str): Name of the VM
        """
        network_name = self.config['network']['name']
        network_subnet = self.config['network'].get('subnet', '10.128.0.0/9')
        
        # Just create the network, ignoring if it already exists
        print(f"Ensuring Docker network exists: {network_name}")
        subprocess.run(
            ['lxc', 'exec', vm_name, '--', 'sh', '-c', 
            f"docker network create --subnet={network_subnet} {network_name} || true"],
            check=False
        )
    
    # Template Functions
    def generate_flag(self):
        """Generate a unique flag for an exercise."""
        return f"flag{{CTF_{secrets.token_hex(16)}}}"
    
    def random_port(self, min_port=1024, max_port=65535):
        """Generate a random port number."""
        return str(random.randint(int(min_port), int(max_port)))
    
    def random_range(self, range_str):
        """Generate a random number within a specified range."""
        try:
            min_val, max_val = map(int, range_str.split('-'))
            return str(random.randint(min_val, max_val))
        except (ValueError, AttributeError):
            return "30"  # Default value if parsing fails
    
    def generate_random_ip(self, subnet_str):
        """
        Generate a random IP address within the specified subnet.
        
        Args:
            subnet_str (str): Subnet in CIDR notation (e.g., '10.128.0.0/9')
            
        Returns:
            str: A random IP address within the subnet
        """
        try:
            # Parse the network
            network = ipaddress.IPv4Network(subnet_str)
            
            # Debug output
            print(f"Generating IP in range: {network.network_address} to {network.broadcast_address}")
            
            # Calculate the usable range (excluding network and broadcast addresses)
            network_size = network.num_addresses
            
            # Generate a random integer between the first and last usable IP
            # Skip the first IP (network address) and last IP (broadcast)
            if network_size > 2:
                random_int = random.randint(1, network_size - 2)
            else:
                random_int = 1
            
            # Convert to IP address
            random_ip = str(network[random_int])
            
            # Debug
            print(f"Generated IP: {random_ip}, subnet: {subnet_str}, network size: {network_size}")
            
            return random_ip
        except Exception as e:
            print(f"Error generating random IP: {str(e)}")
            raise ValueError(f"Invalid subnet: {subnet_str}. Error: {str(e)}")
    
    def random_ip(self, subnet_param=None):
        """Template function to generate a random IP."""
        # If a parameter was provided via the template, use it
        if subnet_param:
            return self.generate_random_ip(subnet_param)
        else:
            # Use default subnet from config
            subnet = self.config['network'].get('subnet', '10.128.0.0/9')
            return self.generate_random_ip(subnet)