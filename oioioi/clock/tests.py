import calendar
import time
from datetime import datetime, timezone  # pylint: disable=E0611

from dateutil.parser import parse as parse_date
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import Contest, Round, RoundTimeExtension


class TestClock(TestCase):
    fixtures = ['test_contest', 'test_users']

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_clock(self):
        response = self.client.get(reverse('get_status')).json()
        response_time = response['time']
        now = time.time()
        self.assertLessEqual(response_time, now)
        self.assertGreater(response_time, now - 10)

    def test_countdown(self):
        contest = Contest.objects.get()
        now = time.time()
        r1_start = datetime.fromtimestamp(now - 5)
        r1_end = datetime.fromtimestamp(now + 10)
        r2_start = datetime.fromtimestamp(now - 10)
        r2_end = datetime.fromtimestamp(now + 5)
        r1 = Round(contest=contest, start_date=r1_start, end_date=r1_end)
        r2 = Round(contest=contest, start_date=r2_start, end_date=r2_end)
        r1.save()
        r2.save()

        response = self.client.get(
            reverse('get_status', kwargs={'contest_id': contest.id})
        ).json()
        round_start_date = response['round_start_date']
        round_end_date = response['round_end_date']
        self.assertEqual(round_start_date, time.mktime(r2_start.timetuple()))
        self.assertEqual(round_end_date, time.mktime(r2_end.timetuple()))

    def test_countdown_with_extended_rounds(self):
        contest = Contest.objects.get()
        now = time.time()
        r1_start = datetime.fromtimestamp(now - 5)
        r1_end = datetime.fromtimestamp(now + 10)
        r1 = Round(contest=contest, start_date=r1_start, end_date=r1_end)
        r1.save()
        user = User.objects.get(username='test_user')
        RoundTimeExtension(user=user, round=r1, extra_time=10).save()

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(
            reverse('get_status', kwargs={'contest_id': contest.id})
        ).json()
        round_start_date = response['round_start_date']
        round_end_date = response['round_end_date']
        self.assertEqual(round_start_date, time.mktime(r1_start.timetuple()))
        self.assertEqual(round_end_date, time.mktime(r1_end.timetuple()) + 600)

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_admin_time(self):
        self.assertTrue(self.client.login(username='test_admin'))
        session = self.client.session
        session['admin_time'] = datetime(2012, 12, 12, tzinfo=timezone.utc).isoformat()
        session.save()
        response = self.client.get(reverse('get_status')).json()
        self.assertTrue(response['is_admin_time_set'])
        self.assertEqual(
            response['time'],
            calendar.timegm(parse_date(session['admin_time']).timetuple()),
        )
