#!/bin/bash

cd "`dirname "$0"`"

# Clear the latest build data
docker-compose down --remove-orphans

# Let's hope we don't ruin anything :).
echo "Running docker tests on `date` with $0 $@"

# Pass current user ID.
export OIOIOI_UID="$UID"

# Always rebuild web and worker container.
docker-compose -f docker-compose-selenium.yml build web worker || exit 1

# Start docker images and wait for them.
docker-compose -f docker-compose-selenium.yml up -d || exit 1
for ((i = 0; i < 240; i++)); do
    curl "127.0.0.1:8001" >> /dev/null 2>&1 && break
    sleep 2
done
if ((i == 240)); then
    echo "timeout!"
    docker-compose down --remove-orphans
    exit 1
fi

# Run tests.
echo "Starting tests"
pytest oioioi_selenium "$@"
result=$?

# Save container's logs.
docker-compose -f docker-compose-selenium.yml logs --no-color > test_log.txt

# Cleanup.
docker-compose -f docker-compose-selenium.yml down --remove-orphans

# Create archive with screenshots.
cd ./oioioi_selenium/ && \
    find . -name "*.png" | tar -zcvf ../test_screenshots.tar.gz -T - && cd ..
find ./oioioi_selenium -name "*.png" -delete

exit $result
