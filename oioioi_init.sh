#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

./manage.py migrate 2>&1 | tee /sio2/logs/migrate.log

./manage.py loaddata ../oioioi/oioioi_selenium/data.json

sudo /etc/init.d/rabbitmq-server start

cd /sio2/deployment

./manage.py supervisor --logfile=/sio2/logs/supervisor.log --daemonize

./manage.py runserver 0.0.0.0:8000 \
       > /sio2/logs/runserver/out.log \
       2> /sio2/logs/runserver/err.log
