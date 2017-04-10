#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

sudo chown -R oioioi:oioioi /sio2

mkdir -pv /sio2/logs/supervisor
mkdir -pv /sio2/logs/runserver
mkdir -pv /sio2/logs/database

echo "LOG: Migrating databases"
./manage.py migrate auth \
       >/sio2/logs/database/migrate_auth.out \
       2>/sio2/logs/database/migrate_auth.err
./manage.py migrate \
       >/sio2/logs/database/migrate.out \
       2>/sio2/logs/database/migrate.err

echo "LOG: Launching rabbitmq"
sudo /etc/init.d/rabbitmq-server start

echo "LOG: Launching OIOIOI"
cd /sio2/deployment

# We must add local bin to path because we do not use virtualenv
./manage.py supervisor \
       > /sio2/logs/supervisor/out.log \
       2> /sio2/logs/supervisor/err.log &

sleep 10

./manage.py supervisor start all

./manage.py runserver 0.0.0.0:8000 \
       > /sio2/logs/runserver/out.log \
       2> /sio2/logs/runserver/err.log





