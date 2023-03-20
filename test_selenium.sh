#!/bin/bash

docker_compose_fun() {
  OIOIOI_UID=$(id -u) docker-compose -p oioioi-selenium -f docker-compose-dev.yml -f docker-compose-selenium.yml "$@"
}

cd "`dirname "$0"`"

# Clear the latest build data
docker_compose_fun down --remove-orphans

# Let's hope we don't ruin anything :).
echo "Running docker tests on `date` with $*"

# Always rebuild web and worker container.
docker_compose_fun build web worker || exit 1

# Start docker images and wait for them.
docker_compose_fun up -d || exit 1

for ((i = 0; i < 240; i++)); do
  curl "127.0.0.1:8001" >/dev/null 2>&1 && break
  sleep 2
done
if ((i == 240)); then
  echo "timeout!"
  docker_compose_fun down
  exit 1
fi

# Run tests.
echo "Starting tests"
pytest oioioi_selenium "$@"
result=$?

# Save container's logs.
docker_compose_fun logs --no-color >test_log.txt

# Cleanup.
docker_compose_fun down --remove-orphans

# Create archive with screenshots.
cd ./oioioi_selenium/ && \
  find . -name "*.png" | tar -zcvf ../test_screenshots.tar.gz -T - && cd ..
find ./oioioi_selenium -name "*.png" -delete

exit $result
