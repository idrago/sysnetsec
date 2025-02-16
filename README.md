# SysNetSec - System and Network Security Exercises

This repository houses a collection of exercises utilized in the System and Network Security course at UNITO.

## Project Structure

- **vpn**: This folder contains support scripts utilized for constructing the VPN necessary to execute the exercises.

- **vm**: This folder contains the scripts to creare an individual VM to each student. Traffic from VPN clients end in the VMs.

- **Other subfolders**: Each subfolder represents an independent set of exercises. Refer to the README.md within each subfolder for a comprehensive description of the exercise.

## Vagrant Installation

**Step 1** - Install Vagrant: open a terminal in this folder and run 
```
$ sudo apt install vagrant-libvirt
```

**Step 2** - Install libvirt and kvm:
```
$ sudo apt install libvirt-clients libvirt-daemon-system virtinst bridge-utils
$ sudo systemctl enable libvirtd
$ sudo systemctl start libvirtd
```

**Step 3** - Install ansible:
```
$ sudo apt install ansible
```

**Step4** - Move to `vms` folder and start the Vagrant boxes:
```
$ cd vms
$ vagrant up
```

Happy learning! 🚀
