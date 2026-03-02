# Access Control 05 — SUID Custom Binary

## Objective
A custom binary `/etc/updater` has been compiled from C source and given the SUID bit with root ownership. The binary contains a vulnerability (command injection via `system()`) that can be triggered to execute arbitrary commands as root. The goal is to exploit it to read the flag.

## Connect
```
ssh student@localhost -p 2205
```
Password: `password`

## Vulnerability
`/etc/updater` is a root-owned SUID binary compiled with `gcc`. It passes user-controlled input to `system()` without sanitization, enabling command injection. Because the binary runs as root due to the SUID bit, injected commands execute with full root privileges.

## Hint
Run `/etc/updater` and observe how it handles its arguments — look for a way to append shell metacharacters to escape into a command.

## Flag location
`/root/flag.txt`
