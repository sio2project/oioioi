#!/bin/bash

# https://intoli.com/blog/exit-on-errors-in-bash-scripts/
set -e

# Run this script with -g to run CyPress with GUI
#   or without to run tests in terminal mode. 
# cy:run    runs tests in terminal mode
# cy:open   opens interactive gui

echo -e "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo -e "     Remember to flush the database      "
echo -e "    and create superuser admin, admin.   "
echo -e "Some tests may relay on an empty database"
echo -e "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

gui='run'

while getopts 'g' flag; do
    case "${flag}" in
        g) gui='open' ;;
    esac
done

pushd oioioi_cypress
    # Resolve dependencies
    pnpm install

    # Wait for a server. Poll one request at a time: by default wait-on sends
    # a new request every 250 ms without waiting for the previous one, which
    # piles up on the slow dev server until it runs out of DB connections.
    pnpm exec wait-on http://localhost:8000 --simultaneous 1 --interval 1000 --httpTimeout 10000 --timeout 120000

    # Run tests
    CYPRESS_baseUrl=http://localhost:8000 pnpm run cy:${gui}
popd
