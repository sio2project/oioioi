#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

function migrate() {
	OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec web python3 manage.py makemigrations

	OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec web python3 manage.py migrate
}

function createsuperuser() {
	DJANGO_SUPERUSER_PASSWORD=admin OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml exec web python3 manage.py createsuperuser --noinput --username oioioi --email oioioi@oioioi.oi
}

function main() {
	migrate
	createsuperuser
}

main