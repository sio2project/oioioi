#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

sed -i "s/^SERVER.*$/SERVER = 'uwsgi'/;s/^COMPRESS_OFFLINE.*$/COMPRESS_OFFLINE = True/" /sio2/deployment/settings.py

echo "LOG: Migrating databases"
./manage.py migrate &
echo "LOG: Collecting and compressing static files"
(./manage.py collectstatic --noinput && ./manage.py compress > /dev/null) &

wait

echo "LOG: Removing old pidfiles"
rm -f pidfiles/*

echo "LOG: Launching nginx"
sudo /etc/init.d/nginx start

echo "LOG: Launching OIOIOI"
exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
