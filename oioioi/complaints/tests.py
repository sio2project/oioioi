from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.complaints.models import ComplaintsConfig
from oioioi.contests.models import Contest
from oioioi.participants.models import Participant


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class TestMakingComplaint(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_making_complaint(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()
        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='ACTIVE')
        p.save()

        with fake_time(datetime(2012, 8, 11, tzinfo=timezone.utc)):
            self.assertTrue(self.client.login(username='test_user'))
            response = self.client.post(
                reverse('add_complaint', kwargs={'contest_id': contest.id}),
                {'complaint': "I am innocent! It is your fault!"},
                follow=True,
            )
            self.assertEqual(response.status_code, 403)

        cconfig = ComplaintsConfig(
            contest=contest,
            enabled=True,
            start_date=datetime(2012, 8, 10, tzinfo=timezone.utc),
            end_date=datetime(2012, 8, 12, tzinfo=timezone.utc),
        )
        cconfig.save()

        with fake_time(datetime(2012, 8, 9, tzinfo=timezone.utc)):
            response = self.client.get(
                reverse('add_complaint', kwargs={'contest_id': contest.id})
            )
            self.assertEqual(response.status_code, 403)

        with fake_time(datetime(2012, 8, 13, tzinfo=timezone.utc)):
            response = self.client.get(
                reverse('add_complaint', kwargs={'contest_id': contest.id})
            )
            self.assertEqual(response.status_code, 403)

        with fake_time(datetime(2012, 8, 11, tzinfo=timezone.utc)):
            response = self.client.post(
                reverse('add_complaint', kwargs={'contest_id': contest.id}),
                {'complaint': "I am innocent! It is your fault!"},
                follow=True,
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "has been sent")

        jurym = mail.outbox[0].message()
        userm = mail.outbox[1].message()
        del mail.outbox[:]

        # Header class doesn't offer 'in' operator
        expected = "[oioioi-complaints] Complaint: Test User (test_user)"
        self.assertEqual(expected, jurym['Subject'])
        self.assertEqual(expected, userm['Subject'])

        self.assertEqual("dummy@example.com", jurym['To'])
        self.assertEqual("test_user@example.com", userm['To'])
        self.assertEqual(jurym['Message-ID'], userm['References'])
        self.assertEqual(userm['Message-ID'], jurym['References'])

        self.assertIn("your fault!", jurym.as_string())
        self.assertIn("your fault!", userm.as_string())
