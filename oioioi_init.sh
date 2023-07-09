#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

sed -i "s/DEBUG = True/DEBUG = False/;s/^COMPRESS_OFFLINE.*$/COMPRESS_OFFLINE = False/" /sio2/deployment/settings.py
export OIOIOI_SERVER_MODE="uwsgi-http"

./manage.py migrate &
./manage.py collectstatic --noinput &

wait

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
