#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

./manage.py migrate 2>&1 | tee /sio2/deployment/logs/migrate.log

if [[ -v CREATE_SUPERUSER ]]; then
  ./manage.py loaddata ../oioioi/oioioi_selenium/data.json;
fi