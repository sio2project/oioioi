#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

mkdir -pv /sio2/logs/{supervisor,runserver,database}

sed -i -e "s/DEBUG = True/DEBUG = False/g" settings.py

echo "LOG: Migrating databases"
./manage.py migrate
./manage.py migrate auth
./manage.py collectstatic --noinput

echo "LOG: Removing old pidfiles"
rm -f pidfiles/*

echo "LOG: Launching OIOIOI"
./manage.py supervisor \
       > /sio2/logs/supervisor.log \
       2> /sio2/logs/supervisor-err.log
