#!/bin/bash
set -e
set -x

sudo apt install -y proot

mkdir -pv /sio2/deployment/logs/database

echo "LOG: Launching worker at `hostname`"
exec python3 $(which twistd) --nodaemon --pidfile=/home/oioioi/worker.pid \
        -l /sio2/deployment/logs/worker`hostname`.log worker \
        --can-run-cpu-exec \
        -n worker`hostname` -c 2 web \
        > /sio2/deployment/logs/twistd_worker.out \
        2> /sio2/deployment/logs/twistd_worker.err
