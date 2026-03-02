# SysNetSec — Standalone CTF Exercises

Self-contained security exercises. Each challenge runs with a single `docker compose up -d`
and requires no external infrastructure.

## Prerequisites

- Docker Engine ≥ 24 and Docker Compose plugin (`docker compose`)
- Basic familiarity with SSH and the Linux command line

## Quick start

```bash
# Pick an exercise directory and bring it up
cd challenges/access_control/access_control_00
docker compose up -d

# Connect
ssh student@localhost -p 2200   # password: password

# Tear down
docker compose down
```

---

## Exercise index

### Access Control

| Exercise | Port | Vulnerability | Flag |
|----------|------|--------------|------|
| `access_control/access_control_00` | 2200 | sudo NOPASSWD for all | `flag{ac00_sudo_nopasswd}` |
| `access_control/access_control_01` | 2201 | ACL on /etc/shadow (rwx) | `flag{ac01_shadow_acl}` |
| `access_control/access_control_02` | 2202 | Student key in root's authorized_keys | `flag{ac02_ssh_key_pivot}` |
| `access_control/access_control_03` | 2203 | World-writable cron script | `flag{ac03_cron_writeable_script}` |
| `access_control/access_control_04` | 2204 | SUID bit on `/usr/bin/find` | `flag{ac04_suid_find}` |
| `access_control/access_control_05` | 2205 | SUID custom C binary | `flag{ac05_suid_binary}` |
| `access_control/access_control_06` | 2206 | Python path hijack via PYTHONPATH | `flag{ac06_python_path_hijack}` |
| `access_control/access_control_07` | 2207 | nginx config injection (cron reload) | `flag{ac07_nginx_conf_injection}` |
| `access_control/access_control_08` | 2208 | PostgreSQL superuser → read /root/flag.txt | `flag{ac08_postgres_privesc}` |

Connect: `ssh student@localhost -p PORT` (password: `password`)
Flag at: `/root/flag.txt` in each container

---

### Docker Escape

| Exercise | Port | Vulnerability |
|----------|------|--------------|
| `docker_escape/variant_0` | 2220 | Docker socket (`/var/run/docker.sock`) mounted |
| `docker_escape/variant_1` | 2221 | Excessive capabilities: `SYS_ADMIN` + `SYS_MODULE` |

Connect: `ssh student@localhost -p PORT` (password: `password`)

```bash
cd challenges/docker_escape/variant_0   # or variant_1
docker compose up -d
ssh student@localhost -p 2220
```

---

### Scanning — SNMP Enumeration

| Exercise | Port | Protocol |
|----------|------|---------|
| `scanning/scanning_00_snmp` | 1610/udp | SNMP v2c |

```bash
cd challenges/scanning/scanning_00_snmp
docker compose up -d
# Discover the community string and walk the MIB
snmpwalk -v2c -c public localhost:1610
```

Flag embedded in `sysLocation` OID.

---

### CVE Exercises

| CVE | Port | Software | Vulnerability |
|-----|------|---------|--------------|
| [CVE-2018-12613](challenges/cves/cve-2018-12613/README.md) | 8080 | phpMyAdmin 4.8.1 | LFI → RCE |
| [CVE-2021-34429](challenges/cves/cve-2021-34429/README.md) | 8081 | Cacti 1.2.22 | SQL injection → RCE |

```bash
cd challenges/cves/cve-2018-12613   # or cve-2021-34429
docker compose up -d
# CVE-2018-12613: http://localhost:8080/phpmyadmin/
# CVE-2021-34429: http://localhost:8081/
```

---

### ARP Spoofing

```bash
cd challenges/spoofing
docker compose up -d
ssh student@localhost -p 2240   # password: password
```

Three-container topology on a Docker bridge (`172.30.0.0/24`):

| Container | IP | Role |
|-----------|-----|------|
| jumpbox | 172.30.0.10 | Student entry point |
| blackhole | 172.30.0.11 | Intended packet destination |
| generator | 172.30.0.12 | Sends flag via UDP to blackhole |

Goal: poison the generator's ARP cache so its UDP packets reach the jumpbox.
Intercept with `tcpdump` to extract the flag.

---

## Directory structure

```
challenges/
├── access_control/
│   ├── access_control_00/ … access_control_08/
├── cves/
│   ├── cve-2018-12613/
│   └── cve-2021-34429/
├── docker_escape/
│   ├── variant_0/
│   └── variant_1/
├── scanning/
│   └── scanning_00_snmp/
└── spoofing/
    ├── docker-compose.yml
    └── arpspoofing/
        ├── jumpbox/
        ├── blackhole/
        └── generator/
```
