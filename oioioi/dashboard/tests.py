from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.base.tests.tests import TestPublicMessage
from oioioi.contests.models import Contest
from oioioi.dashboard.models import DashboardMessage
from oioioi.programs.controllers import ProgrammingContestController


class PublicMessageContestController(ProgrammingContestController):
    dashboard_message = 'Test public message'


class TestDashboardMessage(TestPublicMessage):
    model = DashboardMessage
    button_viewname = 'contest_dashboard'
    edit_viewname = 'dashboard_message_edit'
    viewname = 'contest_dashboard'
    controller_name = 'oioioi.dashboard.tests.PublicMessageContestController'


class TestMessagesSection(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_messages',
    ]

    @override_settings(NUM_DASHBOARD_MESSAGES=6)
    def test_show_more_button_visible(self):
        self.assertTrue(self.client.login(username='test_user'))
        contest = Contest.objects.get()
        url = reverse('contest_dashboard', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Show more')

    @override_settings(NUM_DASHBOARD_MESSAGES=7)
    def test_show_more_button_not_visible(self):
        self.assertTrue(self.client.login(username='test_user'))
        contest = Contest.objects.get()
        url = reverse('contest_dashboard', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Show more')

    def test_show_all_button_visible(self):
        self.assertTrue(self.client.login(username='test_user'))
        contest = Contest.objects.get()
        url = reverse('contest_dashboard', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Show all')
