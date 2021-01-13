#!/bin/sh

set -o pipefail

cmd="$1"
args="${@:2}"

cd /sio2/oioioi

case "$cmd" in
    black)
        echo "black"
        [ -z "$args" ] && python3 -m black --check .
        [ "$args" ] && python3 -m black --check $args
    ;;
    isort)
        echo "isort"
        [ -z "$args" ] && python3 -m isort --check-only .
        [ "$args" ] && python3 -m isort --check-only $args
    ;;
    pylint)
      echo "pylint"
      for f in $args; do
        OUT=$(python2 -m pylint --rcfile=.pylintrc -r n -f text --msg-template='{line}:{msg_id} {msg}' $f 2>/dev/null)
        OUT=$(echo -n "$OUT" | grep '^[0-9][0-9]*:')
        [ "$OUT" ] && printf "\n$f\n$OUT\n"
      done;
    ;;
    pep8)
    echo "pep8"
    for f in $args; do
      OUT=$(python2 -m pep8 --config=.pep8rc $f)
      [ "$OUT" ] && printf "\n$f\n$OUT\n"
    done;
    ;;
esac
