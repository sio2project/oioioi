#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

mkdir -p /sio2/logs/{supervisor,runserver,database}

sed -i -e "s/DEBUG = False/DEBUG = True/g" settings.py

echo "LOG: Migrating databases"
./manage.py migrate 2>&1 | tee /sio2/logs/database/migrate.log

echo "LOG: loading test data"
./manage.py loaddata ../oioioi/oioioi_selenium/data.json

echo "LOG: Launching rabbitmq"
sudo /etc/init.d/rabbitmq-server start

echo "LOG: Removing old pidfiles"
cd /sio2/deployment
rm -f pidfiles/*

echo "LOG: Launching OIOIOI"
cd /sio2/deployment

./manage.py supervisor --logfile=/sio2/logs/supervisor.log --daemonize

./manage.py runserver 0.0.0.0:8000 \
       > /sio2/logs/runserver/out.log # \
       # 2> /sio2/logs/runserver/err.log
