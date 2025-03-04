# Environment Setup

This repository contains a Vagrant configuration for creating a customizable Capture The Flag (CTF) environment. It allows instructors to create multiple virtual machines for multiple students with isolated networks.

## Prerequisites

- [Vagrant](https://www.vagrantup.com/downloads) (2.2.0+)
- [Libvirt](https://libvirt.org/) and the [vagrant-libvirt](https://github.com/vagrant-libvirt/vagrant-libvirt) plugin
- [Ansible](https://www.ansible.com/) (optional, for VM provisioning)

## Quick Start

1. Clone this repository:
   
2. Launch the environment with default settings (1 student, 1 VM):
   ```bash
   vagrant up
   ```

3. To create environments for multiple students with multiple VMs:
   ```bash
   NUM_STUDENTS=3 VMS_PER_STUDENT=2 vagrant up
   ```

## Configuration Options

All configuration is done through environment variables:

### VM Configuration
- `VM_CPUS`: Number of CPUs per VM (default: 2)
- `VM_MEMORY`: Memory in MB per VM (default: 1024)
- `VM_DISK_SIZE`: Disk size in GB (default: 10)
- `VM_BOX`: Base Vagrant box (default: "debian/bookworm64")

### Student Configuration
- `NUM_STUDENTS`: Number of students (default: 1)
- `STUDENT_START_INDEX`: Starting student number (default: 2)
- `VMS_PER_STUDENT`: VMs per student (default: 1, max: 8)
- `STUDENT_FORMAT`: VM naming format (default: "student%02d-vm%d")

### Network Configuration
- `NET_BASE_SUBNET`: Base network segment (default: "192.198")
- `NET_BRIDGE_PREFIX`: Bridge device prefix (default: 10)
- `NET_START_SUBNET`: Starting subnet number (default: 254)
- `NET_SUBNET_MASK`: Subnet mask (default: "255.255.255.0")

### Docker Configuration
- `DOCKER_REGISTRY_HOST`: Docker registry mirror (default: "registry.local:5000")
- `DOCKER_NETWORK`: Docker container network CIDR (default: "10.128.0.0/9")

### Ansible Configuration
- `USE_ANSIBLE`: Enable/disable Ansible provisioning (default: true)
- `ANSIBLE_PLAYBOOK`: Playbook to use (default: "basicvm.yml")
- `ANSIBLE_COMPAT_MODE`: Compatibility mode (default: "2.0")

## Usage Examples

### Basic CTF classroom with 5 students, 1 VM each
```bash
NUM_STUDENTS=5 vagrant up
```

### Advanced setup with 3 students, 2 VMs each, custom specs
```bash
NUM_STUDENTS=3 VMS_PER_STUDENT=2 VM_CPUS=4 VM_MEMORY=4096 vagrant up
```

### Setup with custom Docker registry and network
```bash
DOCKER_REGISTRY_HOST="192.168.129.137:5000" DOCKER_NETWORK="172.16.0.0/12" NUM_STUDENTS=2 vagrant up
```

### Change the base image to Ubuntu
```bash
VM_BOX="ubuntu/jammy64" vagrant up
```

### Custom network configuration
```bash
NET_BASE_SUBNET=10.10 NET_START_SUBNET=100 vagrant up
```

### Custom naming scheme for teams
```bash
STUDENT_FORMAT="team%02d-machine%d" vagrant up
```

## Network Details

- Each VM type gets its own subnet
- For the default configuration:
  - VM1: 192.198.254.x (all students' VM1s share this subnet)
  - VM2: 192.198.253.x (all students' VM2s share this subnet)
  - VM3: 192.198.252.x (all students' VM3s share this subnet)
  - VM4: 192.198.251.x (all students' VM4s share this subnet)
  - VM5: 192.198.250.x (all students' VM5s share this subnet)
- Each student gets a unique IP in each subnet (student1 gets .10, student2 gets .11, etc.)

## Performance Optimizations

- Networks are only created or updated when necessary (during `vagrant up` or `vagrant reload`)
- Running `vagrant status` or other commands will not recreate networks
- Networks are cleaned up automatically when all VMs are destroyed

## Management Commands

- Start environment: `vagrant up`
- Check status: `vagrant status`
- Halt all VMs: `vagrant halt`
- Destroy environment: `vagrant destroy -f`
- Access a specific VM: `vagrant ssh student02-vm1`
- Start a specific VM: `vagrant up student02-vm1`

## Customizing VM Provisioning

The default Ansible playbook (`basicvm.yml`) sets up a basic environment. You can modify this playbook or create a new one and specify it with `ANSIBLE_PLAYBOOK`.

The playbook automatically receives the following variables:
- `student_id`: Student identifier (e.g., "student02")
- `vm_id`: VM identifier (e.g., "vm1")
- `student_index`: Numeric student index
- `vm_index`: Numeric VM index
- `ip_address`: The VM's IP address
- `network_name`: The network name the VM is connected to
- `registry_host`: Docker registry host (from DOCKER_REGISTRY_HOST)
- `docker_network`: Docker container network (from DOCKER_NETWORK)

## Troubleshooting

- Network issues: Check `sudo virsh net-list --all` to ensure networks are created
- Disk space: Verify available space before creating many VMs
- Memory: Ensure your host has enough RAM for all the VMs you're creating
- If network creation fails: Try running `sudo virsh net-destroy vmXnet` and `sudo virsh net-undefine vmXnet` manually to clean up, then retry