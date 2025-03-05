#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

if [ "$1" == "--dev" ]; then
    ./manage.py migrate 2>&1 | tee /sio2/deployment/logs/migrate.log
    ./manage.py loaddata ../oioioi/extra/dbdata/default_admin.json
fi

echo "Init Finished"

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log