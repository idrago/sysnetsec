# Access Control 03 — World-Writable Cron Script

## Objective
A cron job runs `/etc/cache.sh` as root every minute. The script has world-writable permissions (`chmod 777`), meaning any user on the system can modify it. The goal is to inject a payload into this script that copies the flag to a location the student can read, then wait for the cron job to execute it.

## Connect
```
ssh student@localhost -p 2203
```
Password: `password`

## Vulnerability
The cron entry `* * * * * root /etc/cache.sh` combined with `chmod 777 /etc/cache.sh` means any unprivileged user can overwrite or append to a script that runs with root privileges every minute. This is a classic cron-based privilege escalation via a misconfigured file permission.

## Hint
Append a command to `/etc/cache.sh` that copies the flag somewhere you can read it, then wait up to 60 seconds.

## Flag location
`/root/flag.txt`
