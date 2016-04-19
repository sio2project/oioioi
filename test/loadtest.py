#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import argparse
import sys
import os
import re
try:
    import locust  # pylint: disable=unused-import
except ImportError:
    print "Please install locust (pip install locustio) and rerun the test"
    sys.exit()
from locust import HttpLocust, TaskSet, task
from locust.stats import RequestStats
from BeautifulSoup import BeautifulSoup


# Monkey patch that prevents reseting locust's stats
# when all Locusts get hatched
def abort_reset(*arg, **kwargs):
    print "Request stats reset aborted"
RequestStats.reset_all = abort_reset


class RegularUserBehaviour(TaskSet):
    def __init__(self, *args, **kwargs):
        super(RegularUserBehaviour, self).__init__(*args, **kwargs)
        self.submission_link = None
        self.username = os.environ['USERNAME']
        self.password = os.environ['PASSWORD']
        self.contest_name = os.environ['CONTEST']
        self.problem_name = os.environ['PROBLEM']
        self.submission_file = os.environ['SUBMISSION_FILE']

    def on_start(self):
        self.login()

    def login(self):
        response = self.client.get("/login/")
        csrftoken = response.cookies['csrftoken']
        req_body = {
            'username': self.username,
            'password': self.password,
            'csrfmiddlewaretoken': csrftoken,
        }
        response = self.client.post("/login/", req_body,
                headers={'Referer': self.client.base_url + '/login/'})
        page = BeautifulSoup(response.content)
        username = page.find('strong', id='username').getText()
        if username != self.username:
            print 'ERROR: coldn\'t log in'
            assert False

    @task(weight=7)
    def index(self):
        self.client.get('/')

    @task(weight=20)
    def contest_dashboard(self):
        self.client.get('/c/%s/dashboard/' % self.contest_name)

    @task(weight=4)
    def contest_problem_list(self):
        self.client.get('/c/%s/p/' % self.contest_name)

    @task(weight=3)
    def problem_description(self):
        self.client.get('/c/%s/p/%s/' % (self.contest_name, self.problem_name))

    @task(weight=1)
    def send_submission(self):
        # Get csrf token and problem instance id
        path = '/c/%s/submit/' % self.contest_name
        response = self.client.get(path)
        csrftoken = response.cookies['csrftoken']
        submit_page = BeautifulSoup(response.content)
        problems = (submit_page.find('select', id='id_problem_instance_id')
                               .findAll('option'))
        for problem in problems:
            if problem.getText().find('({})'.format(self.problem_name)):
                problem_instance_id = problem['value']
                break
        if not problem_instance_id:
            print 'ERROR: couldn\'t submit solution for problem ' + \
                    self.problem_name
            return

        def submit():
            submission_file = open(self.submission_file, 'r')
            req_body = {
                'csrfmiddlewaretoken': csrftoken,
                'problem_instance_id': problem_instance_id,
            }
            try:
                response = self.client.post(path, req_body,
                        files={'file': submission_file},
                        headers={'Referer': self.client.base_url + path})
            finally:
                submission_file.close()
            return response

        # Submit solution
        response = submit()
        repeated_send_msg = 'Ponownie wysłałeś ten sam plik dla tego problemu'
        # Bots submit the same file multiple times, and OIOIOI requires
        # submitting solution second time to confirm that user really wants
        # to do this.
        if response.content.find(repeated_send_msg):
            response = submit()
        if response.content.find('Przekroczono limit zgłoszeń do zadania'):
            print 'ERROR: submission limit exceeded'
            return

        submission_page = BeautifulSoup(response.content)
        submission_table = submission_page.find('table',
                {'class': re.compile(r'.*\bsubmissions_list\b.*')})
        if not submission_table:
            print 'ERROR: couldn\'t get submission table from response:\n' + \
                    response.content
            return
        submissions = submission_table.find('tbody').findAll('tr')
        self.submission_link = submissions[0].find('a')['href']

    @task(weight=10)
    def check_submission_result(self):
        if not self.submission_link:
            return
        self.client.get(self.submission_link)

    @task(weight=8)
    def ranking(self):
        self.client.get('/c/%s/ranking/' % self.contest_name)


class RegularUser(HttpLocust):
    task_set = RegularUserBehaviour
    min_wait = 20 * 1e3             # 10s
    max_wait = 3 * 60 * 1e3         # 3min


def main():
    parser = argparse.ArgumentParser(description="OIOIOI load testing script")
    parser.add_argument('-u', '--username', required='True',
            help="Username that will be used by bots")
    parser.add_argument('-p', '--password', required='True',
            help="Password that will be used by bots")
    parser.add_argument('-c', '--contest', required='True',
            help="Contest used during the test (should be accesible "
                "for the specified user) - please provide the name as it is "
                "displayed in the url")
    parser.add_argument('-pr', '--problem', required='True',
            help="Problem used for submit (should be in the "
                "specified contest) - please provide the short name")
    parser.add_argument('-s', '--submission', required='True',
            help="File used for submissions")
    args, unknown_args = parser.parse_known_args()

    env = dict(os.environ)
    env.update({
        'USERNAME': args.username,
        'PASSWORD': args.password,
        'CONTEST': args.contest,
        'PROBLEM': args.problem,
        'SUBMISSION_FILE': args.submission,
    })
    p = subprocess.Popen(['locust', '-f', 'loadtest.py'] + unknown_args,
            env=env)
    p.wait()

if __name__ == '__main__':
    main()
