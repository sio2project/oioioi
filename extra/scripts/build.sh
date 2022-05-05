#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

DOCKER_BUILDKIT=1 OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml build --progress=plain
