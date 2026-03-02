# Access Control 02 — SSH Key Pivot

## Objective
The student account has an SSH key pair generated at login time. Due to a misconfiguration, the student's public key has been placed in root's `authorized_keys` file. The goal is to use the student's private key — which is already on the machine — to authenticate directly as root via SSH.

## Connect
```
ssh student@localhost -p 2202
```
Password: `password`

## Vulnerability
During container setup, `/home/student/.ssh/id_rsa.pub` was copied into `/root/.ssh/authorized_keys`. This means the private key at `/home/student/.ssh/id_rsa` can authenticate SSH sessions as root. No password cracking or sudo abuse is needed — just a lateral SSH connection.

## Hint
Once logged in as student, try establishing an SSH connection to root@localhost using the key already present in your home directory.

## Flag location
`/root/flag.txt`
