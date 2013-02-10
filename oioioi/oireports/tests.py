from StringIO import StringIO
from datetime import datetime

import slate
from django.contrib.auth.models import User
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from oioioi.base.tests import fake_time
from oioioi.contests.models import Contest
from oioioi.oireports.views import CONTEST_REPORT_KEY
from oioioi.participants.models import Participant


class TestReportViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def setUp(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='ACTIVE')
        p.save()
        user = User.objects.get(username='test_user2')
        p = Participant(contest=contest, user=user, status='ACTIVE')
        p.save()

    def test_pdf_report_view(self):
        contest = Contest.objects.get()
        url = reverse('pdfreport', kwargs={'contest_id': contest.id})
        post_vars = {
            'round_key': CONTEST_REPORT_KEY,
            'region_key': CONTEST_REPORT_KEY,
            'testgroup[zad1][0]': '',
            'testgroup[zad1][1]': '',
            'testgroup[zad1][2]': '',
            'testgroup[zad1][3]': '',
        }

        # Let's check if report is not available for regular user.
        self.client.login(username='test_user')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.post(url, post_vars)
            self.assertEqual(response.status_code, 403)

        self.client.login(username='test_admin')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.post(url, post_vars)
            pages = slate.PDF(StringIO(response.content))
            self.assertIn("test_user", pages[0])
            self.assertIn("Wynik:34", pages[0])
            self.assertIn("ZAD1", pages[0])
            self.assertIn("1bRuntimeerror0.00s/0.10sprogramexited", pages[0])
            self.assertNotIn("test_user2", pages.text())

    def test_xml_view(self):
        contest = Contest.objects.get()
        url = reverse('xmlreport', kwargs={'contest_id': contest.id})
        post_vars = {
            'round_key': CONTEST_REPORT_KEY,
            'region_key': CONTEST_REPORT_KEY,
            'testgroup[zad1][0]': '',
            'testgroup[zad1][1]': '',
            'testgroup[zad1][2]': '',
            'testgroup[zad1][3]': '',
        }

        # Let's check if report is not available for regular user.
        self.client.login(username='test_user')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.post(url, post_vars)
            self.assertEqual(response.status_code, 403)

        self.client.login(username='test_admin')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.post(url, post_vars)
            # We are using str, because response is a stream
            content = str(response.content)
            self.assertIn("<user>Test User (test_user)", content)
            self.assertIn("<result>34</result>", content)
            self.assertIn("<taskid>zad1</taskid>", content)
            self.assertIn("<code>%23include", content)
            self.assertIn("<testcomment>program exited with", content)
            self.assertNotIn("test_user2", content)
