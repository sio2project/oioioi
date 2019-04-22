import re
from datetime import datetime  # pylint: disable=E0611

from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from oioioi.base.tests import TestCase, fake_timezone_now
from oioioi.contests.models import Contest

# The following tests use full-contest fixture, which may be changed this way:
# 1. Create new database, do migrate
# 2. ./manage.py loaddata acm_test_full_contest.json
# 3. Login as 'test_admin' with password 'a'
# 4. Modify something (use Time Admin and User Switching)
# 5. ./manage.py dumpdata --format json --indent 2 --all --exclude contenttypes
#    --exclude django --exclude auth.permission
#    --exclude sessions --exclude admin > some_file
# 6. Copy ``some_file`` to acm/fixtures/acm_test_full_contest.json


class TestACMRanking(TestCase):
    fixtures = ['acm_test_full_contest']

    @staticmethod
    def remove_whitespaces(content):
        return re.sub(r'\s*', b'', content)

    def assertActiveTaskIn(self, task, content):
        self.assertIn(task + b'</a></th>', self.remove_whitespaces(content))

    def assertActiveTaskNotIn(self, task, content):
        self.assertNotIn(task + b'</a></th>', self.remove_whitespaces(content))

    def assertInactiveTaskIn(self, task, content):
        self.assertIn(task + b'</th>', self.remove_whitespaces(content))

    def assertInactiveTaskNotIn(self, task, content):
        self.assertNotIn(task + b'</th>', self.remove_whitespaces(content))

    def test_fixture(self):
        self.assertTrue(Contest.objects.exists())
        self.assertEqual(Contest.objects.get().controller_name,
                'oioioi.acm.controllers.ACMContestController')

    def test_ranking_view(self):
        contest = Contest.objects.get()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})
        csv_url = reverse('ranking_csv', kwargs={'contest_id': contest.id,
                                                 'key': 'c'})

        self.assertTrue(self.client.login(username='test_user'))

        # trial round begins at 11:00, ends at 16:00, results are available
        # at 19:00
        with fake_timezone_now(datetime(2013, 12, 13, 10, 59, tzinfo=utc)):
            response = self.client.get(url)
            for task in [b'trial', b'A', b'sum', b'test']:
                self.assertActiveTaskNotIn(task, response.content)

        with fake_timezone_now(datetime(2013, 12, 13, 11, 30, tzinfo=utc)):
            response = self.client.get(url)
            self.assertActiveTaskIn(b'trial', response.content)
            for task in [b'A', b'sum', b'test']:
                self.assertActiveTaskNotIn(task, response.content)

        with fake_timezone_now(datetime(2013, 12, 13, 17, 0, tzinfo=utc)):
            response = self.client.get(url)
            self.assertInactiveTaskIn(b'trial', response.content)
            for task in [b'A', b'sum', b'test']:
                self.assertInactiveTaskNotIn(task, response.content)

        # round 1 starts at 20:40, ends at 01:40, results are available at
        # 09:00
        with fake_timezone_now(datetime(2013, 12, 14, 20, 39, tzinfo=utc)):
            response = self.client.get(url)
            self.assertInactiveTaskIn(b'trial', response.content)
            for task in [b'A', b'sum', b'test']:
                self.assertInactiveTaskNotIn(task, response.content)

        with fake_timezone_now(datetime(2013, 12, 14, 20, 40, tzinfo=utc)):
            response = self.client.get(url)
            content = response.content.decode('utf-8')
            self.assertActiveTaskNotIn('trial', content)
            for task in ['A', 'sum', 'test']:
                self.assertActiveTaskIn(task, content)
            self.assertNotContains(response, 'The ranking is frozen.')

        with fake_timezone_now(datetime(2013, 12, 15, 1, 0, tzinfo=utc)):
            response = self.client.get(url)
            content = response.content.decode('utf-8')
            self.assertActiveTaskNotIn('trial', content)
            for task in ['A', 'sum', 'test']:
                self.assertActiveTaskIn(task, content)
            self.assertContains(response, 'The ranking is frozen.')

        with fake_timezone_now(datetime(2013, 12, 15, 7, 0, tzinfo=utc)):
            response = self.client.get(url)
            content = response.content.decode('utf-8')
            self.assertInactiveTaskNotIn('trial', content)
            for task in ['A', 'sum', 'test']:
                self.assertInactiveTaskIn(task, content)
            self.assertContains(response, 'The ranking is frozen.')

        with fake_timezone_now(datetime(2013, 12, 15, 9, 0, tzinfo=utc)):
            response = self.client.get(url)
            content = response.content.decode('utf-8')
            self.assertInactiveTaskNotIn('trial', content)
            for task in ['A', 'sum', 'test']:
                self.assertInactiveTaskIn(task, content)
            self.assertNotContains(response, 'The ranking is frozen.')

        with fake_timezone_now(datetime(2013, 12, 15, 0, 40, tzinfo=utc)):
            response = self.client.get(url)
            self.assertContains(response, 'data-username="test_user"', count=2)

        self.assertTrue(self.client.login(username='test_admin'))

        with fake_timezone_now(datetime(2013, 12, 15, 0, 40, tzinfo=utc)):
            response = self.client.get(csv_url)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, '\n', count=4)

            response = self.client.get(url)
            self.assertContains(response, 'data-result_url', count=8)

    def test_model_solution_submission_view(self):
        contest = Contest.objects.get()
        url = reverse('submission',
                      kwargs={'contest_id': contest.id,
                              'submission_id': 1})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0:02')

    def test_safe_exec_mode(self):
        contest = Contest.objects.get()
        self.assertEqual(contest.controller.get_safe_exec_mode(), 'cpu')
