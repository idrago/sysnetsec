#!/bin/bash

# get the flag and destination from the environment
FLAG=${FLAG}
DESTINATION=${DESTINATION} 

# check if the flag is set
if [ -z "$FLAG" ]; then
    echo "FLAG is not set"
    exit 1
fi
# check if the destination is set   
if [ -z "$DESTINATION" ]; then
    echo "DESTINATION is not set"
    exit 1
fi

# while forever
while true; do
    # pick a random number from 1 to 10
    random_number=$(( ( RANDOM % 10 )  + 1 ))

    # pick a random port number from 1 to 65535
    random_port=$(( ( RANDOM % 65535 )  + 1 ))

    # send a packet with a string as payload to another unreachable machine
    echo  $FLAG >/dev/udp/$DESTINATION/$random_port

    # clean the arp cache
    ip -s -s neigh flush all >/dev/null 2>&1

    # wait random_number seconds
    sleep $random_number
done
