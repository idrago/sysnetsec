#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
from python_wireguard import Key
import logging
import argparse

# Network Configuration Constants
DEFAULT_SERVER_IP = "REDACTED_IP_1"
DEFAULT_SERVER_PORT = "REDACTED_PORT"
DEFAULT_NUM_STUDENTS = 32
DEFAULT_START_ID = 2

# WireGuard Network Constants
WG_NETWORK = "10.13.0.0/24"
WG_SERVER_IP = "10.13.0.1"
WG_CLIENT_PREFIX = "10.13.0"

# VM Network Constants
VM_NETWORK = "192.198.254.0/24"
VM_PREFIX = "192.198.254"

# Routing Constants
ALLOWED_NETWORKS = "10.128.0.0/9"  # Networks allowed through WireGuard
INTERNET_INTERFACE = "bond0"
BLOCKED_NETWORKS = "192.168.0.0/16"  # Internal networks blocked from VM access

@dataclass
class StudentNetwork:
    student_id: int  # 2-254
    
    @property
    def wg_ip(self) -> str:
        """WireGuard client IP: {WG_CLIENT_PREFIX}.X where X is student_id"""
        return f"{WG_CLIENT_PREFIX}.{self.student_id}"
    
    @property
    def vm_ip(self) -> str:
        """VM IP: {VM_PREFIX}.X where X is student_id"""
        return f"{VM_PREFIX}.{self.student_id}"

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

    def __post_init__(self):
        if self.num_students > 254 - self.start_id:
            raise ValueError(f"Cannot have more than {254 - self.start_id} students when starting from ID {self.start_id}")
        if self.num_students < 1:
            raise ValueError("Number of students must be at least 1")

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
        return f"""
        # ******************************************************
        #  Student {student.student_id} iptables configuration
        # NAT: Route VPN client traffic to the VM
        PostUp = iptables -t nat -A chain-pg-nat -s {student.wg_ip}/32 -j DNAT --to-destination {student.vm_ip}
        
        # Allow bidirectional traffic between VPN client and their VM
        PostUp = iptables -A chain-pg -s {student.wg_ip}/32 -d {student.vm_ip}/32 -j ACCEPT
        PostUp = iptables -A chain-pg -s {student.vm_ip}/32 -d {student.wg_ip}/32 -j ACCEPT
        
        # Allow VM to access internet through {INTERNET_INTERFACE}, but block internal networks
        PostUp = iptables -A chain-pg -s {student.vm_ip}/32 -o {INTERNET_INTERFACE} ! -d {BLOCKED_NETWORKS} -j ACCEPT
        
        # Drop any other traffic from this VM (to other VMs or internal networks)
        PostUp = iptables -A chain-pg -s {student.vm_ip}/32 -j DROP
        """

    def generate_server_config(self) -> str:
        interface_config = f"""
[Interface]
        Address = {self.server.interface_address}
        PrivateKey = {self.server.private_key}
        ListenPort = {self.server.port}
        """
        
        postup = """
        # Create and setup main chain for filtering
        PostUp = iptables -N chain-pg
        PostUp = iptables -I FORWARD -j chain-pg
        
        # Create and setup NAT chain
        PostUp = iptables -t nat -N chain-pg-nat
        PostUp = iptables -t nat -I PREROUTING -j chain-pg-nat
"""
        
        postdown = """
        # Cleanup filtering chain
        PostDown = iptables -D FORWARD -j chain-pg
        PostDown = iptables -F chain-pg
        PostDown = iptables -X chain-pg
        
        # Cleanup NAT chain
        PostDown = iptables -t nat -D PREROUTING -j chain-pg-nat
        PostDown = iptables -t nat -F chain-pg-nat
        PostDown = iptables -t nat -X chain-pg-nat
"""
        
        return (interface_config + postup + postdown +  "".join(self.peers_rules) + "".join(self.peers)).strip()

    def generate_client_config(self, student: StudentNetwork, client_keys: Tuple[str, str]) -> str:
        private_key, _ = client_keys
        return f"""
[Interface]
        # Student {student.student_id} WireGuard configuration
        Address = {student.wg_ip}/24
        PrivateKey = {private_key}

[Peer]
        PublicKey = {self.server.public_key}
        Endpoint = {self.server.ip}:{self.server.port}
        AllowedIPs = {ALLOWED_NETWORKS}
        PersistentKeepalive = 5
""".strip()

    def add_peer(self, student: StudentNetwork, client_public_key: str) -> None:
        peer_config = f"""
[Peer]
        # Student {student.student_id} peer configuration
        PublicKey = {client_public_key}
        AllowedIPs = {student.wg_ip}/32
    """
        self.peers.append(peer_config)
        self.peers_rules.append(self._generate_iptables_rules(student))

    def generate_configs(self):
        """Generate configurations for all students"""
        start_id = self.server.start_id
        end_id = start_id + self.server.num_students
        
        for student_id in range(start_id, end_id):
            student = StudentNetwork(student_id)
            
            client_private, client_public = Key.key_pair()
            self.add_peer(student, client_public)
            
            client_file = self.server.output_dir / f"student_{student_id:03d}.conf"
            client_config = self.generate_client_config(student, (client_private, client_public))
            client_file.write_text(client_config)
            

        server_config = self.generate_server_config()
        server_file = self.server.output_dir / "wg0.conf"
        server_file.write_text(server_config)
        self.logger.info(f"Generated server config: {server_file}")

def parse_args():
    parser = argparse.ArgumentParser(description='Generate WireGuard configurations for students')
    parser.add_argument('--students', type=int, default=DEFAULT_NUM_STUDENTS,
                      help=f'Number of students (default: {DEFAULT_NUM_STUDENTS})')
    parser.add_argument('--start-id', type=int, default=DEFAULT_START_ID,
                      help=f'Starting student ID (default: {DEFAULT_START_ID})')
    parser.add_argument('--server-ip', type=str, default=DEFAULT_SERVER_IP,
                      help='WireGuard server IP address')
    parser.add_argument('--server-port', type=str, default=DEFAULT_SERVER_PORT,
                      help='WireGuard server port')
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
        start_id=args.start_id
    )
    
    # Initialize configurator and generate configs
    configurator = WireGuardConfigurator(server_config)
    configurator.generate_configs()

if __name__ == "__main__":
    main()