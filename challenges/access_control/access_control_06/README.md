# Access Control 06 — Python Path Hijack

## Objective
A root cron job runs `/root/backup.py` every minute using `python3` with `PYTHONPATH=/usr/lib/python`. That directory is owned and writable by the student user. The goal is to plant a malicious Python module in `/usr/lib/python` that gets imported by `backup.py`, achieving remote code execution as root.

## Connect
```
ssh student@localhost -p 2206
```
Password: `password`

## Vulnerability
When Python resolves imports, it searches directories in `PYTHONPATH` before the standard library paths. Since `/usr/lib/python` is student-writable and appears in `PYTHONPATH`, a module placed there will be imported instead of the legitimate one. A root cron job importing any such module will execute the attacker-controlled code as root.

## Hint
Inspect `backup.py` to find which modules it imports, then create a file with the same name in `/usr/lib/python` containing a payload.

## Flag location
`/root/flag.txt`
