#!/usr/bin/env python3
import yaml
import sys
import time
import subprocess
import logging
from pathlib import Path

class CTFServiceManager:
    def __init__(self, base_path="/home/vagrant"):
        self.base_path = Path(base_path)
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Configure logging to both file and console."""
        logger = logging.getLogger('ctf_service')
        logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler('/var/log/ctf-service.log')
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def wait_for_docker(self, timeout=300):
        """Wait for Docker daemon to be ready."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                subprocess.run(["docker", "info"], 
                             check=True, 
                             capture_output=True)
                self.logger.info("Docker daemon is ready")
                return True
            except subprocess.CalledProcessError:
                time.sleep(5)
        
        self.logger.error("Timeout waiting for Docker daemon")
        return False

    def ensure_network_exists(self):
        """Ensure the CTF network exists."""
        try:
            result = subprocess.run(
                ["docker", "network", "ls", "--format", "{{.Name}}"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if "ctf_network" not in result.stdout:
                self.logger.info("Creating CTF network")
                subprocess.run(
                    ["docker", "network", "create", 
                    "--subnet", "10.128.0.0/9",
                    "--label", "com.docker.compose.network=ctf_network",
                    "ctf_network"],
                    check=True
                )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error managing network: {str(e)}")
            raise

    def start_services(self):
        """Start all CTF services using docker-compose."""
        compose_file = self.base_path / "docker-compose.yml"
        
        if not compose_file.exists():
            self.logger.error(f"docker-compose.yml not found in {self.base_path}")
            return False
            
        try:
            # Pull images first
            self.logger.info("Pulling latest images...")
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "pull"],
                check=True,
                cwd=str(self.base_path)
            )
            
            # Start services
            self.logger.info("Starting services...")
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "up", "-d"],
                check=True,
                cwd=str(self.base_path)
            )
            
            self.logger.info("Services started successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error starting services: {str(e)}")
            return False

    def run(self):
        """Main service routine."""
        try:
            # Wait for Docker to be ready
            if not self.wait_for_docker():
                return 1
                
            # Ensure network exists
            self.ensure_network_exists()
            
            # Start services
            if not self.start_services():
                return 1
                
            return 0
            
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return 1

if __name__ == "__main__":
    service = CTFServiceManager()
    sys.exit(service.run())