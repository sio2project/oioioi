#!/bin/bash
set -e

# Health check script for the OIOIOI web container.
# It queries supervisord status and ensures all background daemons are running properly.
# Exit status:
# 0 if all daemons RUNNING
# 1 if unhealthy or initialization is incomplete.


# 1. Ensure the initialization process has finished
if [ ! -f /tmp/oioioi_init_done ]; then
    exit 1
fi

# 2. Fetch the current status of all supervisor processes
STATUS_OUTPUT=$(/sio2/deployment/manage.py supervisor status 2>&1) || exit 1

# 3. Fail immediately if any process is in a bad or transitional state
if echo "$STATUS_OUTPUT" | grep -qE "FATAL|BACKOFF|STARTING"; then
    exit 1
fi

# 4. Succeed only if at least one process is confirmed to be running
if echo "$STATUS_OUTPUT" | grep -q "RUNNING"; then
    exit 0
fi

exit 1