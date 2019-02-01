import json

from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.status.registry import status_registry


def _coding_status(request, response):
    response['coding_status'] = 'testing an app'
    return response


class TestContestStatus(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        status_registry.register(_coding_status)

    def tearDown(self):
        status_registry.unregister(_coding_status)

    def test_generating_status(self):
        contest = Contest.objects.get()
        url = reverse('get_status', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)

        self.assertContains(response, url)
        self.assertContains(response, contest.id)
        self.assertContains(response, 'test_user')
        self.assertContains(response, 'testing an app')
        data = json.loads(response.content)
        self.assertEquals(data['is_superuser'], False)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)

        self.assertContains(response, 'test_admin')
        self.assertContains(response, 'testing an app')
        data = json.loads(response.content)
        self.assertEquals(data['is_superuser'], True)

    def test_initial(self):
        contest = Contest.objects.get()
        url = reverse('contest_dashboard',
            kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)

        self.assertContains(response, url)
        self.assertContains(response, contest.id)
        self.assertContains(response, 'test_user')
        self.assertContains(response, 'testing an app')
        self.assertContains(response, 'initialStatus')


class TestNoContestStatus(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        status_registry.register(_coding_status)

    def tearDown(self):
        status_registry.unregister(_coding_status)

    def test_generating_status(self):
        url = reverse('get_status')

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)

        self.assertContains(response, url)
        self.assertNotContains(response, 'contest_id')
        self.assertContains(response, 'test_user')
        self.assertContains(response, 'testing an app')
