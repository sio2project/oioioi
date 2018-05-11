#!/bin/bash

cd "`dirname "$0"`"

pytest oioioi/ -v --cov=oioioi --html=test_report/new_index.html -n2 --runslow
# This holds the exit status of the last executed command
# Be careful when inserting new commands in between
# (you might want to && them together with the rest)
exit_status=${?};
if [ "$exit_status" != "0" ]; then
    echo;
    echo "=========";
    echo ">>> ERROR: There is a problem with testing."
    if [ "${1}" != "-s" ]; then
        echo ">>>  MORE: Try \`./test.sh -s.\` for details."
    fi
    echo ">>>      : If test_report.html has appeared"
    echo ">>>      : you might find something interesting there."
    echo "=========";
    echo;
fi
exit $exit_status
