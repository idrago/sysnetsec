# Access Control 00 — sudo NOPASSWD

## Objective
The student account on this machine has been granted unrestricted sudo access without a password requirement. Once connected via SSH, any command can be run as root using `sudo` without authentication. The goal is to leverage this misconfiguration to read the flag stored in root's home directory.

## Connect
```
ssh student@localhost -p 2200
```
Password: `password`

## Vulnerability
The sudoers file contains `student ALL=(ALL) NOPASSWD: ALL`, which allows the student user to execute any command as root without supplying a password. This is a common misconfiguration that grants full privilege escalation with zero effort.

## Hint
`sudo` lets you run commands as another user — try running a read command directly as root.

## Flag location
`/root/flag.txt`
