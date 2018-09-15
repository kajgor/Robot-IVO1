#!/bin/bash

cd $(dirname $0)

# 0    Exit Server
# 250  Exit Server & reboot RPI
# 251  (Re)start Server
# 252  Restart Server and USB ports

EXIT_CODE=251

while [ $EXIT_CODE -ne 0 ]; do
    killall -q ServerGui
    if [ $? -ne 0 ]; then
        sleep 3; # Give time to shutdown sockets
    fi

    ./ServerGui start

    EXIT_CODE=$?
    echo "EXIT_CODE:" $EXIT_CODE

    if [ $EXIT_CODE -eq 252 ]; then
        sudo hub-ctrl -h 0 -P 2 -p 0
        sleep 3
        sudo hub-ctrl -h 0 -P 2 -p 1
        sleep 2
    fi

    if [ $EXIT_CODE -eq 250 ]; then
        sudo shutdown -r --no-wall now
        EXIT_CODE=0
    fi

done

exit $EXIT_CODE
