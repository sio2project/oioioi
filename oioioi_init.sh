#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "db:5432"

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
