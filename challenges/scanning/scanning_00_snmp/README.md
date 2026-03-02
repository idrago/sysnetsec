# Scanning — SNMP Enumeration

## Objective

A service is running on this host. Identify the service, discover which port it listens on,
find the community string, and extract system information via SNMP. The flag is hidden inside
one of the standard SNMP OIDs.

## Start the challenge

```bash
cd challenges/scanning/scanning_00_snmp
docker compose up -d
```

## Vulnerability

SNMP v1/v2c uses a plaintext community string for authentication. Many deployments use the
default string `public`, which allows anyone on the network to query all system MIB objects
including device location, contact, and description.

## Tools you will need

```bash
# Discover the SNMP port (non-standard)
nmap -sU -p 1610 localhost

# Walk the entire MIB tree
snmpwalk -v2c -c <community_string> localhost:1610

# Query a specific OID (e.g. system location)
snmpget -v2c -c <community_string> localhost:1610 1.3.6.1.2.1.1.6.0
```

Install tools if needed: `sudo apt install snmp`

## Hint

The community string is one of the most common defaults. Walk the system group OIDs — the flag
is stored in a standard system information field.

## Flag location

Embedded in the SNMP `sysLocation` OID (`1.3.6.1.2.1.1.6.0`), retrievable via `snmpwalk` or
`snmpget` once you find the right community string.
