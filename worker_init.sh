#!/bin/bash
set -e

sudo apt install -y proot

echo "LOG: Launching worker at `hostname`"
export FILETRACKER_URL="http://web:9999"
twistd --pidfile=/home/oioioi/worker.pid \
       -l /sio2/logs/worker`hostname`.log worker -n worker`hostname` -c 2 web \
	   > /sio2/logs/twistd_worker.out \
	   2> /sio2/logs/twistd_worker.err

sleep 1000000
