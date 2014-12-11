from datetime import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from oioioi.base.tests import fake_time
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

    def assertActiveTaskIn(self, task, content):
        self.assertIn(task + '</a></th>', content)

    def assertActiveTaskNotIn(self, task, content):
        self.assertNotIn(task + '</a></th>', content)

    def assertInactiveTaskIn(self, task, content):
        self.assertIn(task + '</th>', content)

    def assertInactiveTaskNotIn(self, task, content):
        self.assertNotIn(task + '</th>', content)

    def test_fixture(self):
        self.assertTrue(Contest.objects.exists())
        self.assertEqual(Contest.objects.get().controller_name,
                'oioioi.acm.controllers.ACMContestController')

    def test_ranking_view(self):
        contest = Contest.objects.get()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        self.client.login(username='test_user')

        # trial round begins at 11:00, ends at 16:00, results are available
        # at 19:00
        with fake_time(datetime(2013, 12, 13, 10, 59, tzinfo=utc)):
            response = self.client.get(url)
            for task in ['trial', 'A', 'sum', 'test']:
                self.assertActiveTaskNotIn(task, response.content)

        with fake_time(datetime(2013, 12, 13, 11, 30, tzinfo=utc)):
            response = self.client.get(url)
            self.assertActiveTaskIn('trial', response.content)
            for task in ['A', 'sum', 'test']:
                self.assertActiveTaskNotIn(task, response.content)

        with fake_time(datetime(2013, 12, 13, 17, 0, tzinfo=utc)):
            response = self.client.get(url)
            self.assertInactiveTaskIn('trial', response.content)
            for task in ['A', 'sum', 'test']:
                self.assertInactiveTaskNotIn(task, response.content)

        # round 1 starts at 20:40, ends at 01:40, results are available at
        # 09:00
        with fake_time(datetime(2013, 12, 14, 20, 39, tzinfo=utc)):
            response = self.client.get(url)
            self.assertInactiveTaskIn('trial', response.content)
            for task in ['A', 'sum', 'test']:
                self.assertInactiveTaskNotIn(task, response.content)

        with fake_time(datetime(2013, 12, 14, 20, 40, tzinfo=utc)):
            response = self.client.get(url)
            self.assertActiveTaskNotIn('trial', response.content)
            for task in ['A', 'sum', 'test']:
                self.assertActiveTaskIn(task, response.content)
            self.assertNotIn('The ranking is frozen.', response.content)

        with fake_time(datetime(2013, 12, 15, 1, 0, tzinfo=utc)):
            response = self.client.get(url)
            self.assertActiveTaskNotIn('trial', response.content)
            for task in ['A', 'sum', 'test']:
                self.assertActiveTaskIn(task, response.content)
            self.assertIn('The ranking is frozen.', response.content)

        with fake_time(datetime(2013, 12, 15, 7, 0, tzinfo=utc)):
            response = self.client.get(url)
            self.assertInactiveTaskNotIn('trial', response.content)
            for task in ['A', 'sum', 'test']:
                self.assertInactiveTaskIn(task, response.content)
            self.assertIn('The ranking is frozen.', response.content)

        with fake_time(datetime(2013, 12, 15, 9, 0, tzinfo=utc)):
            response = self.client.get(url)
            self.assertInactiveTaskNotIn('trial', response.content)
            for task in ['A', 'sum', 'test']:
                self.assertInactiveTaskIn(task, response.content)
            self.assertNotIn('The ranking is frozen.', response.content)

        with fake_time(datetime(2013, 12, 15, 0, 40, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('result_url'), 2)

        self.client.login(username='test_admin')

        with fake_time(datetime(2013, 12, 15, 0, 40, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('result_url'), 8)

    def test_model_solution_submission_view(self):
        contest = Contest.objects.get()
        url = reverse('submission',
                      kwargs={'contest_id': contest.id,
                              'submission_id': 1})

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.client.login(username='test_admin')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('0:02', response.content)
