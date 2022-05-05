#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec web python3 manage.py runserver 0.0.0.0:8000