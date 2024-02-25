#!/bin/bash

local_id=0
sites=(1 2)

for site in "${sites[@]}"; do
    tries=0
    while [ $tries -lt 3 ]; do
        if /bin/ping -c 1 -W 2 "10.201.${site}.$((local_id+1))"; then
            logger -t "wg-watchdog" "wireguard to site ${site} working"
            break
        else
            sudo wg-quick down "wg${local_id}.${site}"
            sleep 3
            sudo wg-quick up "wg${local_id}.${site}"

            logger -t "wg-watchdog" "wireguard to site ${site} restarted"

            break
        fi
        tries=$((tries+1))
    done
done
