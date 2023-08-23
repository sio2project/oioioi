#!/bin/sh

cmd="$1"
[ -z "$cmd" ] && cmd="all"

export OIOIOI_UID=$(id -u)

# the image has to be rebuilt for file changes to be visible
docker_run_built="docker run --rm --entrypoint=/entrypoint_checks.sh -t sio2project/oioioi-dev "

# can be used without rebuilding the image
docker_compose_alias="docker-compose -f docker-compose-dev.yml "
docker_compose_exec="${docker_compose_alias} exec web /sio2/oioioi/entrypoint_checks.sh "

# choose the way of running static on docker
docker_run="$docker_compose_exec"

# we need to manually filter out migrations because if isort is called with filename as argument
# it will ignore skip/ignore options from config file and check the file anyways;
# the ignore from config file is only respected when isort is called with directory name as argument
GIT_PY_MODIFIED="$({
  git diff --name-only --diff-filter AM HEAD^ HEAD
  git diff --cached --name-only
} | grep -E '.*\.py$' | grep -v 'extra/' | grep -v 'migrations')"

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
    all)
        for toolname in "isort" "black" "pylint" "pep8"; do
          $docker_run $toolname $GIT_PY_MODIFIED
          echo
        done;
    ;;
    *)
    echo "invalid tool name"
;;
esac
