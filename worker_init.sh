#!/bin/bash
set -e
set -x

sudo apt install -y proot
sudo mkdir -pv /sw
sudo cp -dr /sioworkers/* /sw
sudo chown -R oioioi:oioioi /sw
pip install poster3==0.8.1
pip install /sw

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"
/sio2/oioioi/wait-for-it.sh -t 0  "web:8000"

mkdir -pv /sio2/deployment/logs/database

echo "LOG: Launching worker at `hostname`"
export FILETRACKER_URL="http://web:9999"
exec python3 $(which twistd) --nodaemon --pidfile=/home/oioioi/worker.pid \
        -l /sio2/deployment/logs/worker`hostname`.log worker \
        --can-run-cpu-exec \
        -n worker`hostname` -c 2 web \
        > /sio2/deployment/logs/twistd_worker.out \
        2> /sio2/deployment/logs/twistd_worker.err
