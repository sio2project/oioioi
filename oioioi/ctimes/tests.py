from datetime import datetime
import json
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import utc
from oioioi.base.tests import fake_time
from oioioi.contests.models import Round, Contest, RoundTimeExtension


class TestCtimes(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        Round.objects.all().delete()
        contest = Contest.objects.get()
        rounds = [
            Round(name='round1',
                  contest=contest,
                  start_date=datetime(2013, 10, 11, 8, 0, tzinfo=utc),
                  end_date=datetime(2013, 12, 5, 9, 0, tzinfo=utc)),
            Round(name='round2',
                  contest=contest,
                  start_date=datetime(2013, 10, 22, 10, 0, tzinfo=utc),
                  end_date=datetime(2013, 11, 5, 11, 0, tzinfo=utc))
        ]
        Round.objects.bulk_create(rounds)
        self.client.login(username='test_user')

    def test_ctimes_order(self):
        url = reverse('ctimes')
        round1_result = {
            'status': 'OK',
            'start': '2013-10-11 08:00:00',
            'start_sec': 1381478400,
            'end': '2013-12-05 09:00:00',
            'end_sec': 1386234000,
        }
        round2_result = {
            'status': 'OK',
            'start': '2013-10-22 10:00:00',
            'start_sec': 1382436000,
            'end': '2013-11-05 11:00:00',
            'end_sec': 1383649200,
        }
        with fake_time(datetime(2013, 10, 1, 21, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, round2_result)
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, round1_result)
        with fake_time(datetime(2013, 10, 22, 9, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, round1_result)
        with fake_time(datetime(2013, 12, 11, 5, 0, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response['status'], 'NO_ROUND')
        Contest.objects.all().delete()
        with fake_time(datetime(2013, 12, 11, 5, 0, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response['status'], 'NO_CONTEST')
        self.client.logout()
        with fake_time(datetime(2013, 12, 11, 5, 0, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

    def test_ctimes_format(self):
        url = reverse('ctimes')
        date_regexp = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'
        with fake_time(datetime(2013, 10, 1, 21, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertRegexpMatches(response['start'], date_regexp)
            self.assertRegexpMatches(response['end'], date_regexp)

    def test_ctimes_with_roundextension(self):
        url = reverse('ctimes')
        round = Round.objects.get(name='round1')
        user = User.objects.get(username='test_user')
        RoundTimeExtension.objects.create(round=round, user=user, extra_time=5)
        round_result = {
            'status': 'OK',
            'start': '2013-10-11 08:00:00',
            'start_sec': 1381478400,
            'end': '2013-12-05 09:05:00',
            'end_sec': 1386234300,
        }
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, round_result)
