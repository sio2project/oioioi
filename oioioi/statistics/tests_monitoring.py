from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.statistics.views import get_permissions_info, get_rounds_info, get_attachments_info


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
        'test_second_user_messages',
        'test_contest_attachment',
    ]

    def setUp(self):
        self.request = RequestFactory().request()
        self.request.user = User.objects.get(username='test_user')
        self.request.contest = Contest.objects.get()
        self.request.timestamp = datetime(2014, 8, 5, tzinfo=timezone.utc)

    def test_permissions_info(self):
        contest = Contest.objects.get()
        url = reverse('monitoring', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_admin'))

        with fake_time(datetime(2014, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertRegex(str(response.content), r"Admin</td>... *<td>1")
            self.assertRegex(str(response.content), r"Basic Admin</td>... *<td>1")
            self.assertRegex(str(response.content), r"Observer</td>... *<td>1")
            self.assertRegex(str(response.content), r"Personal Data</td>... *<td>1")
            self.assertRegex(str(response.content), r"Participant</td>... *<td>0")

    def test_round_info(self):
        with fake_time(datetime(2015, 7, 5, tzinfo=timezone.utc)):
            self.assertTrue(self.client.login(username='test_admin'))
            rounds_info = get_rounds_info(self.request)
            for ri in rounds_info:
                if ri['name'] == 'Past round':
                    self.assertTrue(ri['start_relative'] == 'Started')
                    self.assertTrue(ri['end_relative'] == 'Finished')
                if ri['name'] == 'Future round':
                    self.assertTrue(ri['start_relative'] == '360 days, 20:27:58')

    def test_questions_info(self):
        contest = Contest.objects.get()
        url = reverse('monitoring', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertRegex(str(response.content), r"Unanswered questions</td>... *<td>2")
            self.assertRegex(str(response.content), r"Oldest unanswered question</td>... *<td>2012-09-07 13:14:24")
            self.assertRegex(str(response.content), r"Submissions with system errors</td>... *<td>2")


    def test_attachments_info(self):
        self.assertTrue(self.client.login(username='test_admin'))
        attachments_info = get_attachments_info(self.request)
        for ai in attachments_info:
            if ai.description == 'published attachment':
                self.assertTrue(ai.pub_date_relative == 'Published')
            if ai.description == 'unpublished attachment':
                self.assertTrue(ai.pub_date_relative != 'Published')

