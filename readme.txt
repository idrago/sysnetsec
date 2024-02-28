- Install WireGuard

$ sudo apt-get install wireguard

- Generate the configuration with the python script e put on /etc/wireguard (both on client and server)

- Useful commands

Show connections
$ sudo wg show

Start/stop interface
$ wg-quick up wg0
$ wg-quick down wg0

Start/stop service
$ sudo systemctl stop wg-quick@wg0.service
$ sudo systemctl start wg-quick@wg0.service
