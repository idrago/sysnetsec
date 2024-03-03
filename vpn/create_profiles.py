#!/usr/bin/env python3

# pip install python_wireguard

from python_wireguard import Key
import os

SERVERIP= "REDACTED_IP_2"
SERVERPORT= "REDACTED_PORT"

server_private, server_public = Key.key_pair()

server_config = """
[Interface]
Address = 10.200.0.1/32
DNS = 8.8.8.8
PrivateKey = {PrivateKey}
ListenPort = {ServerPort}
""".format(PrivateKey=server_private, ServerPort=SERVERPORT)

#PostUp = echo 0 > /proc/sys/kernel/randomize_va_space
server_config_postup = """
PostUp = iptables -A FORWARD -o %i -j ACCEPT
"""

#PostDown = echo 2 > /proc/sys/kernel/randomize_va_space
server_config_postdown = """
PostDown = iptables -D FORWARD -o %i -j ACCEPT
"""

server_postup_template = """
PostUp = iptables -I FORWARD -s 10.{ID}.0.0/13 -j DROP
PostUP = iptables -I FORWARD -s 10.{ID}.0.0/13 -o %i -j ACCEPT
PostUP = iptables -I FORWARD -s 10.{ID}.0.0/13 -d 10.{ID}.0.0/13 -j ACCEPT
PostUp = iptables -I FORWARD -i %i -s 10.200.0.{ID}/32 -d 10.{ID}.0.0/13 -j ACCEPT
"""

server_postdown_template = """
PostDown = iptables -D FORWARD -s 10.{ID}.0.0/13 -j DROP
PostDown = iptables -D FORWARD -s 10.{ID}.0.0/13 -o %i -j ACCEPT
PostDown = iptables -D FORWARD -s 10.{ID}.0.0/13 -d 10.{ID}.0.0/13 -j ACCEPT
PostDown = iptables -D FORWARD -i %i -s 10.200.0.{ID}/32 -d 10.{ID}.0.0/13 -j ACCEPT
"""

template_server_peer = """
[Peer]
PublicKey = {PublicKey}
AllowedIPs = 10.200.0.{ID}/32
"""
server_peer_config = ""

template_client_config = """
[Interface]
Address = 10.200.0.{ID}/24
PrivateKey = {PrivateKey}

[Peer]
PublicKey = {ServerPublicKey}
Endpoint = {ServerIP}:{ServerPort}
AllowedIPs = 10.{ID}.0.0/13
PersistentKeepalive = 5
"""

# print("Server Private Key: {}".format(server_private))
# create the output folder if it doesn't exist
if not os.path.exists("config"):
    os.makedirs("config")

for i in range(0, 256, 8):
    client_private, client_public = Key.key_pair()

    # print("Client{} Private Key: {}".format(i, client_private))
    # print("Client{} Public Key: {}".format(i, client_public))

    server_peer_config += template_server_peer.format(PublicKey=client_public, ID=i)
    server_config_postup += server_postup_template.format(ID=i)
    server_config_postdown += server_postdown_template.format(ID=i)
    client_config = template_client_config.format(PrivateKey=client_private,
                                                  ServerPublicKey=server_public,
                                                  ServerIP=SERVERIP,
                                                  ServerPort=SERVERPORT, ID=i)

    output = open(".vpnconfig/client{}.conf".format(i), "w")
    output.write(client_config)
    output.close()

output = open("config/wg0.conf", "w")
output.write(server_config)
output.write(server_config_postup)
output.write(server_config_postdown)
output.write(server_peer_config)
output.close()
