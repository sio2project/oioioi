#!/bin/sh

cmd="$1"

# the image has to be rebuilt for file changes to be visible
docker_run_built="docker run --rm --entrypoint=/entrypoint_checks.sh -t sio2project/oioioi-dev "

# can be used without rebuilding the image
docker_compose_alias="OIOIOI_UID=$(id -u) docker-compose -f docker-compose-dev.yml -f extra/docker/docker-compose-dev-noserver.yml "
docker_compose_exec="${docker_compose_alias} exec web /sio2/oioioi/entrypoint_checks.sh "

# choose the way of running static on docker
docker_run="$docker_compose_exec"

GIT_PY_MODIFIED="$({ git diff --name-only --diff-filter AM HEAD^ HEAD ; git diff --cached --name-only ; } | cat | grep -E '.*\.py$' | grep -v 'extra/')"

case "$cmd" in
    black)
        $docker_run black
    ;;
    isort)
        $docker_run isort
    ;;
    # pylint and pep8 take a much longer time to run so they are always only run
    # on the modified files instead of running them on the entire codebase
    pylint)
        $docker_run pylint $GIT_PY_MODIFIED
    ;;
    pep8)
        $docker_run pep8 $GIT_PY_MODIFIED
    ;;
    static)
        ISORT_OUT=$($docker_run isort $GIT_PY_MODIFIED)
        printf "$ISORT_OUT\n\n"
        BLACK_OUT=$($docker_run black $GIT_PY_MODIFIED)
        printf "$BLACK_OUT\n\n"
        PYLINT_OUT=$($docker_run pylint $GIT_PY_MODIFIED)
        printf "$PYLINT_OUT\n\n"
        PEP8_OUT=$($docker_run pep8 $GIT_PY_MODIFIED)
        printf "$PEP8_OUT\n"
    ;;
esac

