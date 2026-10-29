#!/bin/bash
set -e
set -o pipefail
set -x

# Marker checked by the docker-compose healthcheck; removed so a restarted container is not reported healthy too early.
INIT_DONE_MARKER=/tmp/oioioi_init_done
rm -f "$INIT_DONE_MARKER"

if [ "$1" == "--dev" ]; then
    echo "Checking frontend dependencies..."

    if ! (cd ../oioioi && pnpm list --depth=0 > /dev/null 2>&1); then
        echo "Dependencies mismatch or missing. Running pnpm install..."
        (cd ../oioioi && pnpm install)
    else
        echo "Dependencies are up to date."
    fi

    echo "Building frontend assets..."
    (cd ../oioioi && pnpm run build)

    echo "Applying migrations..."
    ./manage.py migrate 2>&1 | tee /sio2/deployment/logs/migrate.log
    echo "Migrations applied"
    ./manage.py loaddata ../oioioi/extra/dbdata/default_admin.json

    # Upload sandboxes to filetracker (s3dedup) on first run
    SANDBOX_MARKER="/sio2/deployment/media/.sandboxes_uploaded"
    if [ ! -f "$SANDBOX_MARKER" ]; then
        echo "Uploading sandboxes to filetracker (this may take ~30 seconds)..."
        if ! ./manage.py upload_sandboxes_to_filetracker -d /sio2/sandboxes; then
            echo "Failed to upload sandboxes to filetracker" >&2
            exit 1
        fi
        touch "$SANDBOX_MARKER"
        echo "Sandboxes uploaded successfully"
    else
        echo "Sandboxes already uploaded, skipping..."
    fi
fi

echo "Init Finished"
touch "$INIT_DONE_MARKER"

umask 077
if ! ./manage.py supervisor getconfig > /tmp/supervisord.conf; then
    echo "Failed to generate Supervisor configuration" >&2
    exit 1
fi

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log


