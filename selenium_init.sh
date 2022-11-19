#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

./manage.py migrate 2>&1 | tee /sio2/deployment/logs/migrate.log

./manage.py loaddata ../oioioi/oioioi_selenium/data.json

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
