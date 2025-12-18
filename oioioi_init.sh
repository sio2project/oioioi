#!/bin/bash
set -e
set -x

/sio2/oioioi/wait-for-it.sh -t 60 "${DATABASE_HOST:-db}:${DATABASE_PORT:-5432}"

if [ "$1" == "--dev" ]; then
    echo "Checking frontend dependencies..."

    if ! (cd ../oioioi && npm list --depth=0 > /dev/null 2>&1); then
        echo "Dependencies mismatch or missing. Running npm install..."
        (cd ../oioioi && npm install)
    else
        echo "Dependencies are up to date."
    fi

    echo "Building frontend assets..."
    (cd ../oioioi && npm run build)

    ./manage.py migrate 2>&1 | tee /sio2/deployment/logs/migrate.log
    ./manage.py loaddata ../oioioi/extra/dbdata/default_admin.json

    # Upload sandboxes to filetracker (s3dedup) on first run
    SANDBOX_MARKER="/sio2/deployment/media/.sandboxes_uploaded"
    if [ ! -f "$SANDBOX_MARKER" ]; then
        echo "Uploading sandboxes to filetracker (this may take ~30 seconds)..."
        # Extract filetracker host from FILETRACKER_URL (format: http://host:port/path)
        FT_HOST=$(echo $FILETRACKER_URL | sed 's|http://||' | sed 's|/.*||')
        /sio2/oioioi/wait-for-it.sh -t 120 "$FT_HOST" && \
            ./manage.py upload_sandboxes_to_filetracker -d /sio2/sandboxes && \
            touch "$SANDBOX_MARKER" && \
            echo "Sandboxes uploaded successfully"
    else
        echo "Sandboxes already uploaded, skipping..."
    fi
fi

echo "Init Finished"

exec ./manage.py supervisor --logfile=/sio2/deployment/logs/supervisor.log
