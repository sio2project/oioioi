from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, ProblemInstance


class TestContestMonitoringViews(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_submission_another_user_for_statistics',
        'test_extra_rounds',
        'test_extra_problem',
        'test_permissions',
        'test_messages',
    ]

    def setUp(self):
        self.request = RequestFactory().request()
        self.request.user = User.objects.get(username='test_user')
        self.request.contest = Contest.objects.get()
        self.request.timestamp = datetime.now().replace(tzinfo=timezone.utc)

    def test_permissions_info(self):
        contest = Contest.objects.get()
        url = reverse('monitoring', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertRegex(str(response.content), r"Admin</td>... *<td>1")
            self.assertRegex(str(response.content), r"Basic Admin</td>... *<td>1")
            self.assertRegex(str(response.content), r"Observer</td>... *<td>1")
            self.assertRegex(str(response.content), r"Personal Data</td>... *<td>1")
            self.assertRegex(str(response.content), r"Participant</td>... *<td>0")
            f = open("monitoring_page.html", "w")
            f.write(str(response.content))
            f.close()

    def test_round_times(self):
        contest = Contest.objects.get()
        url = reverse('monitoring', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2015, 7, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertRegex(str(response.content), r"Past round(</td>.{0,50}<td>.{0,50}){2}Started")
            self.assertRegex(str(response.content), r"Past round(</td>.{0,50}<td>.{0,50}){4}Finished")

