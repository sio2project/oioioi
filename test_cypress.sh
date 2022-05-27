#!/bin/bash

# https://intoli.com/blog/exit-on-errors-in-bash-scripts/
set -e

# cy:run    runs tests in terminal mode
# cy:open   opens interactive gui

echo -e "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo -e "    Remember to flush the database      "
echo -e "   and create superuser admin, admin.   "
echo -e "Some tests may relay on a empty database"
echo -e "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

gui='run'

while getopts 'g' flag; do
    case "${flag}" in
        g) gui='open' ;;
    esac
done

pushd oioioi_cypress
    # Resolve dependencies
	yarn
    # Wait for a server. If not ready after 10s end program else run tests.
    npx wait-on http://localhost:8000 --timeout 10000 &&\
    CYPRESS_baseUrl=http://localhost:8000 yarn cy:${gui}
popd