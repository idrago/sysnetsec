# Docker Security Access Control Exercises

This repository contains a series of Docker containers designed to help learn and practice various access control and privilege escalation techniques in Linux environments.

## Deployment Instructions

### Prerequisites
- Python 3.x
- SSH access to target VMs (see scripts to deploy the VMs)

### Configuration
1. Edit the `config.yaml` file to define:
   ```yaml
   network:
     name: ctf_network
     subnet: 10.128.0.0/9

   exercises:
     # Global exercise settings
     base_path: /home/vagrant
     default_address:
       ip: 10.128.0.0/9   

   vms:
     pattern:
       base_ip: 192.198.254.0/24
       student_prefix: "student"
       vagrant_path: "../vms/.vagrant/machines"
       vm_provider: "libvirt"
     
     groups:
       lab01:
         range: [2, 29]  # VM IP range
         ssh_user: vagrant
         ssh_key_template: "{vagrant_path}/{student_prefix}{id}/{vm_provider}/private_key"
         exercises: [0, 1, 2, 3, 4]  # Exercise numbers to deploy
   ```

2. Ensure exercise directories (access_control_XX) contain required files:
   - Dockerfile
   - Configuration files
   - Any additional required resources

### Deployment
1. Run the deployment script:
   ```bash
   python3 install.py
   ```

The script will:
- Connect to each VM in the configured ranges
- Copy exercise files and generate flags
- Create and start Docker containers
- Configure networking

## Environment Overview

Each exercise runs in its own Docker container within the student's VM. Some exercises have fixed IP addresses, while others get random IPs within the configured subnet - finding these services is part of the challenge!

### Network Structure
- Main network: 10.128.0.0/9
- Each VM hosts multiple exercise containers
- Other services get random IPs - students must discover them

Each exercise runs in its own Docker container, accessible via SSH:
- `access_control_00`: Sudo Rights Exercise
- `access_control_01`: SSH Key Exercise
- `access_control_02`: Cron Job Exercise
- `access_control_03`: SUID Binary Exercise
- `access_control_04`: Custom Binary Vulnerability
- `access_control_05`: Make Command Exercise
- `access_control_06`: GDB Privilege Escalation
- `access_control_07`: Python Library Path
- `access_control_08`: Nginx Configuration (+ Port 8080)
- `access_control_09`: PostgreSQL Access (+ Port 5432)

## Exercise Details

### Access Control 00 - Sudo Rights
- **Objective**: Exploit misconfigured sudo rights
- **Vulnerability**: NOPASSWD configuration in sudoers
- **Target**: Gain root access using sudo privileges

### Access Control 01 - SSH Keys
- **Objective**: Leverage SSH key misconfigurations
- **Vulnerability**: Poorly configured authorized_keys
- **Target**: Gain unauthorized access using SSH keys

### Access Control 02 - Cron Jobs
- **Objective**: Exploit writable cron jobs
- **Vulnerability**: World-writable root cron script
- **Target**: Execute commands as root via cron

### Access Control 03 - SUID Binary
- **Objective**: Exploit SUID binary permissions
- **Vulnerability**: SUID bit set on find command
- **Target**: Execute commands with elevated privileges

### Access Control 04 - Custom Binary
- **Objective**: Exploit a custom SUID binary
- **Vulnerability**: Buffer overflow in SUID program
- **Target**: Gain root shell through binary exploitation

### Access Control 05 - Make Command
- **Objective**: Exploit SUID make command
- **Vulnerability**: SUID bit on make binary
- **Target**: Execute arbitrary commands as root

### Access Control 06 - GDB
- **Objective**: Use GDB for privilege escalation
- **Vulnerability**: SUID bit on GDB
- **Target**: Debug and modify running processes

### Access Control 07 - Python Path
- **Objective**: Exploit Python library path
- **Vulnerability**: Writable Python library path
- **Target**: Execute code through Python imports

### Access Control 08 - Nginx
- **Objective**: Exploit Nginx configuration
- **Vulnerability**: Writable nginx configuration
- **Target**: Gain access through web server misconfiguration

### Access Control 09 - PostgreSQL
- **Objective**: Exploit database permissions
- **Vulnerability**: Trust authentication in PostgreSQL
- **Target**: Escalate privileges through database access

## Usage Instructions

1. Connect to exercises using SSH:
   ```bash
   ssh student@[VM_IP]
   ```

2. Each exercise container includes:
   - A flag file in /root/flag
   - Hint files in /opt/hints
   - Exercise-specific configurations and tools

3. Successfully complete an exercise by:
   - Finding and exploiting the vulnerability
   - Gaining root access
   - Reading the flag file

## Security Notes

- All exercises are intentionally vulnerable for educational purposes
- Each container is isolated using Docker security features
- Host system access is restricted through container capabilities
- Exercises should only be run in a controlled environment

## Troubleshooting

If you encounter issues:
1. Verify container status: `docker ps`
2. Check container logs: `docker logs access_control_XX`
3. Ensure proper network connectivity
4. Verify SSH service is running in container

## Resetting Exercises

To reset any exercise to its initial state:
```bash
docker-compose stop access_control_XX
docker-compose rm -f access_control_XX
docker-compose up -d access_control_XX
```