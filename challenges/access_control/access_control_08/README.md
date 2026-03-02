# Access Control 08 — PostgreSQL Privilege Escalation

## Objective
The student user has been granted superuser privileges in PostgreSQL. PostgreSQL superusers can read arbitrary files from the filesystem using built-in server functions. The goal is to use PostgreSQL's file access capabilities to read `/root/flag.txt` from within the database.

## Connect
```
ssh student@localhost -p 2208
```
Password: `password`

## Vulnerability
The student database user has been granted `SUPERUSER` in PostgreSQL. This grants access to functions such as `pg_read_file()` and the `COPY ... TO/FROM` mechanism, which can read files from the server's filesystem with the privileges of the PostgreSQL process. No OS-level privilege escalation is needed — the database itself is the attack surface.

## Hint
PostgreSQL superusers have functions that can read files from the server — check the documentation for `pg_read_file` or `COPY TO stdout`.

## Flag location
`/root/flag.txt`
