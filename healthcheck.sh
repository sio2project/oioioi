#!/bin/bash
set -e

if [ ! -f /tmp/oioioi_init_done ]; then
    exit 1
fi

/sio2/.venv/bin/supervisorctl -c /tmp/supervisord.conf status
