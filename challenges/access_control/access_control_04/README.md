# Access Control 04 — SUID find

## Objective
The `find` binary has been given the SUID bit, causing it to run with root privileges regardless of who invokes it. The goal is to exploit `find`'s ability to execute arbitrary commands via `-exec` to spawn a root shell or directly read the flag.

## Connect
```
ssh student@localhost -p 2204
```
Password: `password`

## Vulnerability
Setting the SUID bit on `/usr/bin/find` (`chmod u+s /usr/bin/find`) allows any user to execute `find` as root. The `-exec` flag can then be used to run arbitrary commands with elevated privileges. This is a well-known GTFOBins escalation technique.

## Hint
`find` can execute commands — check GTFOBins for the exact invocation that drops a privileged shell.

## Flag location
`/root/flag.txt`
