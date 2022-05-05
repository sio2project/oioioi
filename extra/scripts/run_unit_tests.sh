#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec "web" ../oioioi/test3.sh