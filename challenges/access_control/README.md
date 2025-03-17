# Docker Security Access Control Exercises

This repository contains a series of Docker containers designed to help learn and practice various access control and privilege escalation techniques in Linux environments.

## Deployment Instructions

### Prerequisites
- Python 3.x
- SSH access to target VMs (see scripts to deploy the VMs)

### Configuration
1. Edit the `config.yaml` file to define network settings, exercise configurations, and VM deployment parameters.

2. Ensure exercise directories (access_control_XX) contain required files:
   - Dockerfile
   - Configuration files (e.g., sshd_config)
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

Each exercise runs in its own Docker container within the student's VM. Containers are configured with specific network settings and security capabilities.

### Network Structure
- Main network: 10.128.0.0/9
- Each VM hosts multiple exercise containers
- Containers have fixed IP addresses within the configured subnet

### Exercise List
Each exercise runs in its own Docker container, accessible via SSH with credentials student:password:

1. **Access Control 00 - Sudo Rights**
   - Objective: Exploit misconfigured sudo rights
   - Vulnerability: Unrestricted NOPASSWD sudo access
   - Target: Gain root access using sudo privileges

2. **Access Control 01 - Shadow File Access**
   - Objective: Exploit file permissions
   - Vulnerability: Read/write access to /etc/shadow
   - Target: Modify password hashes to gain access

3. **Access Control 02 - SSH Key Exploitation**
   - Objective: Leverage SSH key misconfigurations
   - Vulnerability: Student's public key in root's authorized_keys
   - Target: Gain root access using SSH key authentication

4. **Access Control 03 - Cron Job**
   - Objective: Exploit writable cron jobs
   - Vulnerability: World-writable root cron script
   - Target: Execute commands as root via cron

5. **Access Control 04 - SUID Find**
   - Objective: Exploit SUID binary permissions
   - Vulnerability: SUID bit set on find command
   - Target: Execute commands with elevated privileges

6. **Access Control 05 - SUID Binary with ENV_VARS**
   - Objective: Exploit a custom SUID binary
   - Vulnerability: Misuse of environment variables
   - Target: Gain root shell by injecting environment variables

7. **Access Control 08 - Python Library Path**
   - Objective: Exploit Python library path
   - Vulnerability: User-writable PYTHONPATH for root cron job
   - Target: Execute code through Python imports

8. **Access Control 09 - Nginx Config**
    - Objective: Exploit Nginx configuration
    - Vulnerability: Student can write nginx configs running as root
    - Target: Gain access through web server misconfiguration
    
9. **Access Control 10 - PostgreSQL**
    - Objective: Exploit database permissions
    - Vulnerability: Trust authentication and superuser access
    - Target: Escalate privileges through database access
    
## Usage Instructions

1. Connect to exercises using SSH:
   ```bash
   ssh student@[VM_IP]
   ```

2. Each exercise container includes:
   - A flag file in /root/flag
   - Hint files in /home/student/hints
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
- Default password for student user is 'password'

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