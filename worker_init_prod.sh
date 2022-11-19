#!/bin/bash
set -e
set -x

sudo apt install -y proot

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"
/sio2/oioioi/wait-for-it.sh -t 0  "web:80"

mkdir -pv /sio2/logs/{supervisor,runserver,database}

echo "LOG: Launching worker at `hostname`"
export FILETRACKER_URL="http://web:9999"
rm -f /home/oioioi/worker.pid

twistd --nodaemon --pidfile=/home/oioioi/worker.pid \
        -l /sio2/logs/worker`hostname`.log worker \
        -n worker`hostname` -c 2 web \
        > /sio2/logs/twistd_worker.out #\
        #2> /sio2/logs/twistd_worker.err
