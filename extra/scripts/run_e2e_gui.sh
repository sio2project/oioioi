#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

pushd oioioi_cypress
	yarn
	CYPRESS_baseUrl=http://localhost:8000 yarn cy:open
popd