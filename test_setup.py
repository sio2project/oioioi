#!/usr/bin/env python
"""Vagrant/docker build validation

Check whether oioioi is up by creating a contest, adding a problem, sending
a solution and checking whether it's processed correctly.

You should run this script every once in a while when changes are introduced
to the code.

The script assumes that there is no contest (this is a clean oioioi
installation).
"""
from __future__ import absolute_import

import argparse
import time

import requests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--oioioi_address', default='http://localhost:8000/')
    parser.add_argument('--username', default='admin')
    parser.add_argument('--password', default='adminadmin')
    args = parser.parse_args()
    OIOIOI = args.oioioi_address
    USERNAME = args.username
    PASSWORD = args.password

    LOGIN = OIOIOI + 'login/'
    CREATE_CONTEST = OIOIOI + 'admin/contests/contest/add/'
    CONTEST = OIOIOI + 'c/test/dashboard/'
    ADD_PROBLEM = OIOIOI + 'c/test/problems/add?key=upload'
    PROBLEM_INSTANCES = OIOIOI + 'c/test/admin/contests/probleminstance/'
    SUBMISSIONS = OIOIOI + 'c/test/submissions/'
    SUBMIT = OIOIOI + 'c/test/submit/'

    PACKAGE_NAME = 'test_simple_package'
    PROBLEM_PACKAGE = 'oioioi/sinolpack/files/' + PACKAGE_NAME + '.zip'
    SAMPLE_SOLUTION = 'oioioi/sinolpack/files/sum-correct.cpp'

    EXPECTED_STATUS = 'INI_ERR'

    s = requests.Session()

    # Check whether oioioi is up
    r = s.get(OIOIOI)
    assert r.status_code == 200

    # log in as pre-created superuser
    params = {
        'auth-username': USERNAME,
        'auth-password': PASSWORD,
        'csrfmiddlewaretoken': s.cookies['csrftoken'],
        'login_view-current_step': 'auth',
    }

    r = s.post(LOGIN, data=params)
    assert r.url == OIOIOI

    # create a new contest
    r = s.get(CREATE_CONTEST)
    params = {
        'controller_name': 'oioioi.programs.controllers.ProgrammingContestController',
        'name': 'test',
        'id': 'test',
        'start_date_0': '2018-11-20',
        'start_date_1': '20:00:00',
        'csrfmiddlewaretoken': s.cookies['csrftoken'],
        'round_set-TOTAL_FORMS': '0',
        'round_set-INITIAL_FORMS': '0',
        'round_set-MIN_NUM_FORMS': '0',
        'round_set-MAX_NUM_FORMS': '1000',
        'c_attachments-TOTAL_FORMS': '0',
        'c_attachments-INITIAL_FORMS': '0',
        'c_attachments-MIN_NUM_FORMS': '0',
        'c_attachments-MAX_NUM_FORMS': '1000',
        'contestlink_set-TOTAL_FORMS': '0',
        'contestlink_set-INITIAL_FORMS': '0',
        'contestlink_set-MIN_NUM_FORMS': '0',
        'contestlink_set-MAX_NUM_FORMS': '1000',
        'messagenotifierconfig_set-TOTAL_FORMS': '0',
        'messagenotifierconfig_set-INITIAL_FORMS': '0',
        'messagenotifierconfig_set-MIN_NUM_FORMS': '0',
        'messagenotifierconfig_set-MAX_NUM_FORMS': '1000',
        'programs_config-TOTAL_FORMS': '1',
        'programs_config-INITIAL_FORMS': '0',
        'programs_config-MIN_NUM_FORMS': '0',
        'programs_config-MAX_NUM_FORMS': '1',
        'programs_config-0-id': '',
        'programs_config-0-contest': '',
        'programs_config-0-execution_mode': 'AUTO',
        'problemstatementconfig-TOTAL_FORMS': '1',
        'problemstatementconfig-INITIAL_FORMS': '0',
        'problemstatementconfig-MIN_NUM_FORMS': '0',
        'problemstatementconfig-MAX_NUM_FORMS': '1',
        'problemstatementconfig-0-id': '',
        'problemstatementconfig-0-contest': '',
        'problemstatementconfig-0-visible': 'AUTO',
        '_save': 'Save',
    }
    r = s.post(CREATE_CONTEST, data=params)
    assert r.url == CONTEST

    # add problem
    r = s.get(ADD_PROBLEM)
    params = {
        'contest_id': 'test',
        'csrfmiddlewaretoken': s.cookies['csrftoken'],
        'visibility': 'FR',
    }
    with open(PROBLEM_PACKAGE, 'rb') as f:
        s.post(ADD_PROBLEM, data=params, files={'package_file': f})

    timeout = 30
    r = s.get(PROBLEM_INSTANCES)
    while r.text.find(PACKAGE_NAME) == -1:
        assert timeout != 0
        time.sleep(1)
        timeout -= 1
        r = s.get(PROBLEM_INSTANCES)

    # send a solution
    r = s.get(SUBMIT)
    needle = 'id_problem_instance_id'
    pos = r.text.find(needle)
    assert pos != -1
    needle = 'option value="'
    pos = r.text.find(needle, pos)
    assert pos != -1
    pos += len(needle)
    endpos = r.text.find('"', pos)
    assert endpos != -1
    probleminstanceid = r.text[pos:endpos]

    params = {
        'csrfmiddlewaretoken': s.cookies['csrftoken'],
        'problem_instance_id': probleminstanceid,
        'code': '',
        'user': USERNAME,
        'kind': 'NORMAL',
    }
    with open(SAMPLE_SOLUTION, 'r') as f:
        r = s.post(SUBMIT, data=params, files={'file': f})
    assert r.url == SUBMISSIONS

    # check whether workers are running and check the solution
    timeout = 30
    while r.text.find(EXPECTED_STATUS) == -1:
        assert r.text.find('Pending') != -1
        assert timeout != 0
        time.sleep(1)
        timeout -= 1
        r = s.get(SUBMISSIONS)


if __name__ == '__main__':
    main()
