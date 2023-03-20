#!/bin/bash
set -e

. /sio2/venv/bin/activate

if [ ! -z ${DATABASE_HOST+x} ] && [ ! -z ${DATABASE_PORT+x} ]; then
    /sio2/oioioi/scripts/wait-for-it.sh -t 60 "${DATABASE_HOST}:${DATABASE_PORT}"
fi

exec "$@"
