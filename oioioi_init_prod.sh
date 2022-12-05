#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

echo "LOG: Migrating databases"
./manage.py migrate
./manage.py collectstatic --noinput

echo "LOG: Removing old pidfiles"
rm -f pidfiles/*

echo "LOG: Launching OIOIOI"
./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
