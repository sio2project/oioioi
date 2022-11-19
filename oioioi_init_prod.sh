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

echo "LOG: Launching rabbitmq"
sudo /etc/init.d/rabbitmq-server start

echo "LOG: Launching nxinx"
sudo /etc/init.d/nginx start

echo "LOG: Removing old pidfiles"
cd /sio2/deployment
rm -f pidfiles/*

echo "LOG: Launching OIOIOI"
# We must add local bin to path because we do not use virtualenv
./manage.py supervisor \
       > /sio2/logs/supervisor/out.log \
       2> /sio2/logs/supervisor/err.log
