from datetime import datetime, timezone  # pylint: disable=E0611

from io import BytesIO

from django.contrib.auth.models import User
from django.urls import reverse
from oioioi.base.tests import TestCase, fake_time
from oioioi.base.utils.pdf import extract_text_from_pdf
from oioioi.contests.models import Contest
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.oireports.views import CONTEST_REPORT_KEY
from oioioi.participants.models import Participant


class TestReportViews(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_rounds_with_different_end_dates',
    ]

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
        url = reverse('oireports', kwargs={'contest_id': contest.id})
        post_vars = {
            'report_round': CONTEST_REPORT_KEY,
            'report_region': CONTEST_REPORT_KEY,
            'testgroup[zad1]': ['0', '1', '2', '3'],
            'form_type': 'pdf_report',
            'single_report_user': '',
        }

        # Let's check if report is not available for regular user.
        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.post(url, post_vars)
            self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.post(url, post_vars)

            pages = extract_text_from_pdf(BytesIO(self.streamingContent(response)))
            self.assertIn(b"test_user", pages[0])
            self.assertIn(b"Wynik:34", pages[0].replace(b' ', b''))
            self.assertIn(b"ZAD1", pages[0])
            self.assertIn(
                b"1bRuntimeerror0.00s/0.10sprogramexited", pages[0].replace(b' ', b'')
            )
            self.assertTrue(all(b"test_user2" not in page for page in pages))

    def test_xml_view(self):
        contest = Contest.objects.get()
        url = reverse('oireports', kwargs={'contest_id': contest.id})
        post_vars = {
            'report_round': CONTEST_REPORT_KEY,
            'report_region': CONTEST_REPORT_KEY,
            'testgroup[zad1]': ['0', '1', '2', '3'],
            'form_type': 'xml_report',
            'single_report_user': '',
        }

        # Let's check if report is not available for regular user.
        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.post(url, post_vars)
            self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.post(url, post_vars)
            content = self.streamingContent(response).decode('utf-8')
            self.assertIn("<user>Test User (test_user)", content)
            self.assertIn("<result>34</result>", content)
            self.assertIn("<taskid>zad1</taskid>", content)
            self.assertIn("<code>%23include", content)
            self.assertIn("<testcomment>program exited with", content)
            self.assertNotIn("test_user2", content)

    def test_single_report(self):
        contest = Contest.objects.get()
        url = reverse('oireports', kwargs={'contest_id': contest.id})
        post_vars = {
            'report_round': CONTEST_REPORT_KEY,
            'report_region': CONTEST_REPORT_KEY,
            'testgroup[zad1]': ['0', '1', '2', '3'],
            'form_type': 'xml_report',
            'is_single_report': 'on',
            'single_report_user': 'test_user2',
        }

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.post(url, post_vars)
            content = self.streamingContent(response).decode('utf-8')
            self.assertNotIn('test_user2', content)
            self.assertIn('Strange, there is no one', content)

    def test_default_selected_round(self):
        contest = Contest.objects.get()
        url = reverse('oireports', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2016, 11, 6, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertContains(response, 'selected>Past round')
