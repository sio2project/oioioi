from django.test import TestCase
from django.core.urlresolvers import reverse
from oioioi.contests.models import Contest, Round
from datetime import datetime
import json
import time

class TestClock(TestCase):
    fixtures = ['test_contest']

    def test_clock(self):
        response = self.client.get(reverse('oioioi.clock.views.get_times_view'))
        response = json.loads(response.content)
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

        response = self.client.get(reverse('oioioi.clock.views.get_times_view'))
        response = json.loads(response.content)
        round_start_date = response['round_start_date']
        round_end_date = response['round_end_date']
        self.assertEqual(round_start_date, time.mktime(r2_start.timetuple()))
        self.assertEqual(round_end_date, time.mktime(r2_end.timetuple()))
