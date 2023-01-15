#!/bin/bash
set -e
set -x

./manage.py migrate 2>&1 | tee /sio2/deployment/logs/migrate.log

# load the fixture at the first start of the container and only in a development environment
if [ ${DEBUG} = "True" ]; then
    ./manage.py loaddata ../oioioi/oioioi/admin_admin_fixture.json
fi

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
