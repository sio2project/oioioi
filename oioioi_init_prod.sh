#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

sed -i "s/^SERVER.*$/SERVER = 'uwsgi'/;s/^COMPRESS_OFFLINE.*$/COMPRESS_OFFLINE = True/" /sio2/deployment/settings.py

./manage.py migrate &
(./manage.py collectstatic --noinput && ./manage.py compress > /dev/null) &

wait

sudo /etc/init.d/nginx start

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
