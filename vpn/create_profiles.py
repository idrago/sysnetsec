#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, List, Dict
import ipaddress
from python_wireguard import Key
import logging
import argparse

# Network Configuration Constants
DEFAULT_SERVER_IP = "REDACTED_IP_1"
DEFAULT_SERVER_PORT = "REDACTED_PORT"
DEFAULT_NUM_STUDENTS = 32
DEFAULT_START_ID = 2
DEFAULT_VMS_PER_STUDENT = 1
MAX_VMS_PER_STUDENT = 8  # Support up to 8 VMs per student

# WireGuard Network Constants
WG_NETWORK = "10.13.0.0/24"
WG_SERVER_IP = "10.13.0.1"
WG_CLIENT_PREFIX = "10.13.0"

# VM Network Constants for the actual VMs - Extended to 8 networks
VM_NETWORKS = [
    "192.198.254.0/24",  # VM1
    "192.198.253.0/24",  # VM2
    "192.198.252.0/24",  # VM3
    "192.198.251.0/24",  # VM4
    "192.198.250.0/24",  # VM5
    "192.198.249.0/24",  # VM6
    "192.198.248.0/24",  # VM7
    "192.198.247.0/24"   # VM8
]
VM_PREFIXES = [
    "192.198.254",  # VM1
    "192.198.253",  # VM2
    "192.198.252",  # VM3
    "192.198.251",  # VM4
    "192.198.250",  # VM5
    "192.198.249",  # VM6
    "192.198.248",  # VM7
    "192.198.247"   # VM8
]

# For multiple VMs, we'll divide the student-visible network into equal parts
STUDENT_VISIBLE_NETWORK = "10.128.0.0/9"  # The big network that students see

# Routing Constants
INTERNET_INTERFACE = "bond0"
BLOCKED_NETWORKS = "192.168.0.0/16"  # Internal networks blocked from VM access
ALLOWED_IPS = STUDENT_VISIBLE_NETWORK  # Networks the student can access through WireGuard

@dataclass
class VmSubnet:
    """Represents a subnet handled by a specific VM"""
    network_cidr: str  # The network CIDR, e.g. "10.128.0.0/12"
    vm_ip: str         # The VM's actual IP, e.g. "192.198.254.2"
    vm_index: int      # Which VM this is (0-7)

@dataclass
class StudentNetwork:
    student_id: int        # 2-254
    vms_per_student: int   # 1-8
    vm_subnets: List[VmSubnet] = None  # Will be populated in post_init
    
    def __post_init__(self):
        # Initialize the VM subnets
        self.vm_subnets = []
        
        # Validate vms_per_student is within range
        if self.vms_per_student < 1 or self.vms_per_student > MAX_VMS_PER_STUDENT:
            raise ValueError(f"VMs per student must be between 1 and {MAX_VMS_PER_STUDENT}")
        
        if self.vms_per_student == 1:
            # If only one VM, it handles the entire network
            self.vm_subnets.append(VmSubnet(
                network_cidr=STUDENT_VISIBLE_NETWORK,
                vm_ip=f"{VM_PREFIXES[0]}.{self.student_id}",
                vm_index=0
            ))
        else:
            # Divide the network for multiple VMs
            network = ipaddress.ip_network(STUDENT_VISIBLE_NETWORK)
            
            # Calculate subnet bits needed based on VM count
            subnet_bits = 0
            temp = self.vms_per_student - 1  # How many bits we need
            while temp > 0:
                subnet_bits += 1
                temp >>= 1
            
            new_prefix_len = network.prefixlen + subnet_bits
            subnets = list(network.subnets(new_prefix_len - network.prefixlen))
            
            # Assign subnets to VMs
            for vm_index in range(self.vms_per_student):
                if vm_index < len(subnets):
                    self.vm_subnets.append(VmSubnet(
                        network_cidr=str(subnets[vm_index]),
                        vm_ip=f"{VM_PREFIXES[vm_index]}.{self.student_id}",
                        vm_index=vm_index
                    ))
    
    @property
    def wg_ip(self) -> str:
        """WireGuard client IP: {WG_CLIENT_PREFIX}.X where X is student_id"""
        return f"{WG_CLIENT_PREFIX}.{self.student_id}"
    
    def vm_ip(self, vm_index: int) -> str:
        """VM IP for the given VM index: {VM_PREFIX[vm_index]}.X where X is student_id"""
        if vm_index < 0 or vm_index >= len(VM_PREFIXES) or vm_index >= self.vms_per_student:
            raise ValueError(f"VM index {vm_index} is out of range (0-{self.vms_per_student-1})")
        return f"{VM_PREFIXES[vm_index]}.{self.student_id}"

@dataclass
class ServerConfig:
    ip: str
    port: str
    private_key: str
    public_key: str
    interface_address: str = f"{WG_SERVER_IP}/32"  # Server is always .1
    output_dir: Path = Path(".vpnconfig")
    num_students: int = DEFAULT_NUM_STUDENTS
    start_id: int = DEFAULT_START_ID
    vms_per_student: int = DEFAULT_VMS_PER_STUDENT

    def __post_init__(self):
        if self.num_students > 254 - self.start_id:
            raise ValueError(f"Cannot have more than {254 - self.start_id} students when starting from ID {self.start_id}")
        if self.num_students < 1:
            raise ValueError("Number of students must be at least 1")
        if self.vms_per_student < 1 or self.vms_per_student > MAX_VMS_PER_STUDENT:
            raise ValueError(f"VMs per student must be between 1 and {MAX_VMS_PER_STUDENT}")

class WireGuardConfigurator:
    def __init__(self, server_config: ServerConfig):
        self.server = server_config
        self.peers = []
        self.peers_rules = []
        self._setup_logging()
        self._ensure_output_dir()
    
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _ensure_output_dir(self):
        self.server.output_dir.mkdir(exist_ok=True)
        self.logger.info(f"Using output directory: {self.server.output_dir}")

    def _generate_iptables_rules(self, student: StudentNetwork) -> str:
        """Generate iptables rules for a student with potentially multiple VMs"""
        student_table = 100 + student.student_id
        wg_client_ip = student.wg_ip
        
        rules = [
            f"# ******************************************************",
            f"# Student {student.student_id} iptables configuration",
            f"",
            f"# Create a dedicated routing table for this student",
            f"PostUp = ip rule add from {wg_client_ip}/32 table {student_table}"
        ]
        
        # Global allow rule for the student to reach the entire network
        rules.append(f"")
        rules.append(f"# Allow student to reach target networks and receive responses")
        rules.append(f"PostUp = iptables -A chain-pg -s {wg_client_ip}/32 -d {STUDENT_VISIBLE_NETWORK} -j ACCEPT")
        rules.append(f"PostUp = iptables -A chain-pg -s {STUDENT_VISIBLE_NETWORK} -d {wg_client_ip}/32 -j ACCEPT")
        
        # Add routing rules for each VM and its subnet
        for subnet in student.vm_subnets:
            vm_ip = subnet.vm_ip
            vm_subnet = subnet.network_cidr
            vm_index = subnet.vm_index
            
            # Add route in the student's routing table to direct traffic for the subnet to the VM
            rules.append(f"")
            rules.append(f"# Routes for VM{vm_index+1} ({vm_ip}) handling subnet {vm_subnet}")
            rules.append(f"PostUp = ip route add {vm_subnet} via {vm_ip} table {student_table}")
            
            # Allow this VM to access internet, but block internal networks
            rules.append(f"PostUp = iptables -A chain-pg -s {vm_ip}/32 -o {INTERNET_INTERFACE} ! -d {BLOCKED_NETWORKS} -j ACCEPT")
            
            # Allow communication between the WireGuard client and this VM
            rules.append(f"PostUp = iptables -A chain-pg -s {wg_client_ip}/32 -d {vm_ip}/32 -j ACCEPT")
            rules.append(f"PostUp = iptables -A chain-pg -s {vm_ip}/32 -d {wg_client_ip}/32 -j ACCEPT")
        
        # Add drop rules for all VMs to prevent access to other networks
        rules.append(f"")
        rules.append(f"# Block VMs from accessing unauthorized networks")
        for vm_index in range(student.vms_per_student):
            vm_ip = student.vm_ip(vm_index)
            rules.append(f"PostUp = iptables -A chain-pg -s {vm_ip}/32 -j DROP")
        
        # Final drop rule for the WireGuard client
        rules.append(f"PostUp = iptables -A chain-pg -s {wg_client_ip}/32 -j DROP")
        
        # Cleanup rules
        rules.append(f"")
        rules.append(f"# Cleanup rules")
        rules.append(f"PostDown = ip rule del from {wg_client_ip}/32 table {student_table}")
        
        # Consistent indentation for the entire rule set
        return "\n".join(rules)

    def generate_server_config(self) -> str:
        interface_config = [
            "[Interface]",
            f"Address = {self.server.interface_address}",
            f"PrivateKey = {self.server.private_key}",
            f"ListenPort = {self.server.port}",
            "",
            "# Create and setup main chain for filtering",
            "PostUp = iptables -N chain-pg",
            "PostUp = iptables -I FORWARD -j chain-pg",
            "",
            "# Cleanup filtering chain",
            "PostDown = iptables -D FORWARD -j chain-pg",
            "PostDown = iptables -F chain-pg",
            "PostDown = iptables -X chain-pg",
            ""
        ]
        
        # Build the full server config by combining interface config, peer rules, and peer entries
        config_parts = []
        config_parts.extend(interface_config)
        
        for rule_set in self.peers_rules:
            config_parts.append(rule_set)
            config_parts.append("")  # Add a blank line between rule sets
        
        config_parts.extend(self.peers)
        
        return "\n".join(config_parts)

    def generate_client_config(self, student: StudentNetwork, client_keys: Tuple[str, str]) -> str:
        private_key, _ = client_keys
        
        # Base configuration
        config = [
            "[Interface]",
            f"# Student {student.student_id} WireGuard configuration",
            f"Address = {student.wg_ip}/24",
            f"PrivateKey = {private_key}",
            "",
            "[Peer]",
            f"PublicKey = {self.server.public_key}",
            f"Endpoint = {self.server.ip}:{self.server.port}",
            f"AllowedIPs = {ALLOWED_IPS}",
            f"PersistentKeepalive = 5"
        ]
        
        return "\n".join(config)

    def add_peer(self, student: StudentNetwork, client_public_key: str) -> None:
        peer_config = [
            "",
            "[Peer]",
            f"# Student {student.student_id} peer configuration",
            f"PublicKey = {client_public_key}",
            f"AllowedIPs = {student.wg_ip}/32"
        ]
        self.peers.extend(peer_config)
        self.peers_rules.append(self._generate_iptables_rules(student))

    def generate_configs(self):
        """Generate configurations for all students"""
        start_id = self.server.start_id
        end_id = start_id + self.server.num_students
        
        # Generate a VM subnet mapping table for documentation
        subnet_map = {}
        
        for student_id in range(start_id, end_id):
            student = StudentNetwork(student_id, self.server.vms_per_student)
            
            # Store subnet mapping for this student
            student_subnets = {}
            for subnet in student.vm_subnets:
                student_subnets[f"VM{subnet.vm_index+1}"] = {
                    "subnet": subnet.network_cidr,
                    "vm_ip": subnet.vm_ip
                }
            subnet_map[f"student{student_id:03d}"] = student_subnets
            
            client_private, client_public = Key.key_pair()
            self.add_peer(student, client_public)
            
            client_file = self.server.output_dir / f"student_{student_id:03d}.conf"
            client_config = self.generate_client_config(student, (client_private, client_public))
            client_file.write_text(client_config)
            self.logger.info(f"Generated client config for student {student_id}: {client_file}")
            
        server_config = self.generate_server_config()
        server_file = self.server.output_dir / "wg0.conf"
        server_file.write_text(server_config)
        self.logger.info(f"Generated server config: {server_file}")
        
        # Save subnet mapping for reference
        import json
        subnet_map_file = self.server.output_dir / "subnet_mapping.json"
        subnet_map_file.write_text(json.dumps(subnet_map, indent=2))
        self.logger.info(f"Generated subnet mapping: {subnet_map_file}")
        
        # Also generate a more human-readable mapping for instructors
        readme_content = ["# VM Subnet Mapping", "", "This file shows which VM handles which portion of the 10.128.0.0/9 network for each student.", ""]
        
        for student_id, subnets in sorted(subnet_map.items()):
            readme_content.append(f"## {student_id}")
            for vm_name, vm_data in sorted(subnets.items()):
                readme_content.append(f"- {vm_name}: {vm_data['subnet']} → {vm_data['vm_ip']}")
            readme_content.append("")
        
        readme_file = self.server.output_dir / "subnet_mapping.md"
        readme_file.write_text("\n".join(readme_content))
        self.logger.info(f"Generated human-readable subnet mapping: {readme_file}")

def parse_args():
    parser = argparse.ArgumentParser(description='Generate WireGuard configurations for students')
    parser.add_argument('--students', type=int, default=DEFAULT_NUM_STUDENTS,
                      help=f'Number of students (default: {DEFAULT_NUM_STUDENTS})')
    parser.add_argument('--start-id', type=int, default=DEFAULT_START_ID,
                      help=f'Starting student ID (default: {DEFAULT_START_ID})')
    parser.add_argument('--vms-per-student', type=int, default=DEFAULT_VMS_PER_STUDENT,
                      help=f'Number of VMs per student (default: {DEFAULT_VMS_PER_STUDENT}, max: {MAX_VMS_PER_STUDENT})')
    parser.add_argument('--server-ip', type=str, default=DEFAULT_SERVER_IP,
                      help='WireGuard server IP address')
    parser.add_argument('--server-port', type=str, default=DEFAULT_SERVER_PORT,
                      help='WireGuard server port')
    parser.add_argument('--output-dir', type=str, default='.vpnconfig',
                      help='Output directory for configuration files')
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Generate server keys
    server_private, server_public = Key.key_pair()
    
    # Create server configuration
    server_config = ServerConfig(
        ip=args.server_ip,
        port=args.server_port,
        private_key=server_private,
        public_key=server_public,
        num_students=args.students,
        start_id=args.start_id,
        vms_per_student=args.vms_per_student,
        output_dir=Path(args.output_dir)
    )
    
    # Initialize configurator and generate configs
    configurator = WireGuardConfigurator(server_config)
    configurator.generate_configs()

if __name__ == "__main__":
    main()