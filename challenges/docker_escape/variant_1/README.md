# Docker Escape — Variant 1: Excessive Capabilities (SYS_ADMIN + SYS_MODULE)

## Objective

Escape a Docker container that has been granted excessive Linux capabilities. The container runs
with `SYS_ADMIN` and `SYS_MODULE` capabilities, both of which break container isolation:
`SYS_ADMIN` permits mounting host filesystems and manipulating namespaces; `SYS_MODULE` allows
loading arbitrary kernel modules, giving full kernel-level code execution.

## Connect

```
ssh student@localhost -p 2221
```

Password: `password`

## Start the challenge

```bash
cd challenges/docker_escape/variant_1
docker compose up -d
```

## Vulnerability

`SYS_ADMIN` allows `mount()` syscalls without restriction. A container with this capability can
mount the host's root disk (if the device is visible) or use `unshare` to create user namespaces.
`SYS_MODULE` allows `insmod`/`modprobe`, which inserts code directly into the running kernel —
trivially bypassing all container boundaries.

## Hint

Check what capabilities your container has (`capsh --print`). Then look for ways to use
`SYS_ADMIN` (mount, namespace tricks) or `SYS_MODULE` (loading a kernel module) to read
host files.

## Flag location

`/root/flag.txt` (inside this container — escape to read it as root, or read the host's
filesystem after a successful mount-based escape)
