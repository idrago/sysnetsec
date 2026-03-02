# ARP Spoofing — Man-in-the-Middle

## Network topology

```
  generator (172.30.0.12)
       |  sends FLAG via UDP packets
       v
  blackhole (172.30.0.11)   ← intended destination
       ^
  jumpbox  (172.30.0.10)    ← you are here (SSH in)
```

The **generator** continuously sends UDP packets containing the flag to the **blackhole**.
Your goal: poison the ARP table on the generator so it sends packets to the **jumpbox**
instead. Intercept the packet and read the flag.

## Start the challenge

```bash
cd challenges/spoofing
docker compose up -d
```

## Connect

```
ssh student@localhost -p 2240
```

Password: `password`

## Available tools (already installed on jumpbox)

| Tool | Purpose |
|------|---------|
| `arpspoof` | Send crafted ARP replies (from `dsniff`) |
| `arp-scan` | Discover hosts and MACs on the network |
| `arping` | Send ARP requests / verify MACs |
| `tcpdump` | Capture network traffic |
| `ip neigh` | Inspect the local ARP cache |

## Objective

1. From the jumpbox, confirm the other hosts are reachable (`ping`, `arp-scan`).
2. Use `arpspoof` to poison the generator's ARP cache — make it believe the blackhole's IP
   (`172.30.0.11`) resolves to the jumpbox's MAC address.
3. Capture the incoming UDP packets with `tcpdump` and extract the flag from the payload.

## Hint

`arpspoof -i eth0 -t <target> <host-to-impersonate>` poisons `<target>`'s ARP cache.
Enable IP forwarding first if you need bidirectional traffic.

## Flag

Embedded in the UDP payload sent by the generator. Read it with:
```bash
sudo tcpdump -i eth0 -A udp
```
(after a successful ARP poisoning)
