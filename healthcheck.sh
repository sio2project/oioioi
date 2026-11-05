#!/bin/bash
set -uo pipefail

[ -f /tmp/oioioi_init_done ] || exit 1

status=$(/sio2/.venv/bin/supervisorctl -c /tmp/supervisord.conf status 2>&1)
echo "$status"
# Healthy only when every program is RUNNING. STARTING/BACKOFF/FATAL/EXITED fail,
# and so does an unreachable supervisord: its error line has no RUNNING column.
[ -n "$status" ] && ! awk '$2 != "RUNNING" { bad = 1 } END { exit !bad }' <<< "$status"с
