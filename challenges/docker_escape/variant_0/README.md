# Docker Escape — Variant 0: Docker Socket Mount

## Objective

Escape a Docker container by abusing a mounted Docker socket. The container has the Docker CLI
available and `/var/run/docker.sock` is mounted read-write. A motivated attacker with access to
the Docker socket can spawn a new privileged container that mounts the host filesystem, then
read sensitive files from the host.

## Connect

```
ssh student@localhost -p 2220
```

Password: `password`

## Start the challenge

```bash
cd challenges/docker_escape/variant_0
docker compose up -d
```

## Vulnerability

The Docker daemon socket (`/var/run/docker.sock`) is mounted inside the container. Any process
with write access to this socket can issue Docker API calls — including launching new containers
with arbitrary host mounts or `--privileged` flags. This effectively grants the container user
root-level access to the host.

## Hint

The `docker` CLI is already installed. Can you use it to mount the host root filesystem inside
another container?

## Flag location

`/root/flag.txt` (inside this container — read it from the host-mounted filesystem after escaping)
