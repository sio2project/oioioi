#!/bin/bash

cd "`dirname "$0"`"

# Let's hope we don't ruin anything :).
echo "Running docker tests on `date` with $0 $@"

# Pass current user ID.
export OIOIOI_UID="$UID"

# Always rebuild web and worker container.
docker-compose -f docker-compose-selenium.yml build test-web test-worker || exit 1

# Start docker images and wait for them.
docker-compose -f docker-compose-selenium.yml up -d || exit 1
for ((i = 0; i < 60; i++)); do
    curl "127.0.0.1:8001" >> /dev/null 2>&1 && break
    sleep 5
done
if ((i == 60)); then
    echo "timeout!"
    docker-compose down
    exit 1
fi

# Run tests.
nosetests -w ./oioioi_selenium --with-html "$@"
result=$?

# Save container's logs.
docker-compose -f docker-compose-selenium.yml logs --no-color > test_log.txt

# Cleanup.
docker-compose -f docker-compose-selenium.yml down

# Create archive with screenshots.
cd ./oioioi_selenium/ && \
    find . -name "*.png" | tar -cvf ../test_screenshots.tar.gz -T - && cd ..
find ./oioioi_selenium -name "*.png" -delete

exit $result
