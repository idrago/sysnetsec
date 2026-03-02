# Access Control 01 — Shadow File ACL

## Objective
The student account has been granted read and write access to `/etc/shadow` via a POSIX ACL. This file normally holds the hashed passwords of all system users, including root. The goal is to exploit this access — either by cracking root's password hash or by replacing it — to authenticate as root and read the flag.

## Connect
```
ssh student@localhost -p 2201
```
Password: `password`

## Vulnerability
A POSIX ACL entry (`setfacl -m u:student:rwx /etc/shadow`) gives the student user direct read and write access to `/etc/shadow`. An attacker can extract root's password hash and crack it offline, or overwrite it with a known hash to set a new root password.

## Hint
If you can read `/etc/shadow`, you can also write to it — and `su` reads from it.

## Flag location
`/root/flag.txt`
