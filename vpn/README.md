# Playground VPN Configuration

The environment can be deployed on a remote server connected via WireGuard. The steps to configure the remote virtual network are as follows.

## Install WireGuard

Assuming a Debian-like system:

```bash
$ sudo apt-get install wireguard
```

## Generate Configuration

The Python script in this folder creates a series of client configurations and a server configuration. They are generated in a folder called .vpnconfig. 
At the moment, the script contains hard-coded networks used in the System and Network Security course at UNITO. Generate the configuration using the provided Python script and place it in the `/etc/wireguard` directory on both the client and server.

## Useful Commands

### Show Connections

```bash
$ sudo wg show
```

### Start/Stop Interface

```bash
$ wg-quick up wg0
$ wg-quick down wg0
```

### Start/Stop Service

```bash
$ sudo systemctl stop wg-quick@wg0.service
$ sudo systemctl start wg-quick@wg0.service
```

Make sure to replace `wg0` with the appropriate WireGuard interface name in your configuration.