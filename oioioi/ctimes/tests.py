from datetime import datetime
import json
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Round, Contest, RoundTimeExtension


class TestCtimes(TestCase):
    fixtures = ['test_users', 'test_two_empty_contests']

    def setUp(self):
        contest1 = Contest.objects.get(id='c1')
        contest2 = Contest.objects.get(id='c2')
        rounds = [
            Round(name='round1',
                  contest=contest1,
                  start_date=datetime(2013, 10, 11, 8, 0, tzinfo=utc),
                  end_date=datetime(2013, 12, 5, 9, 0, tzinfo=utc)),
            Round(name='round2',
                  contest=contest1,
                  start_date=datetime(2013, 10, 22, 10, 0, tzinfo=utc),
                  end_date=datetime(2013, 11, 5, 11, 0, tzinfo=utc)),
            Round(name='round1p',
                  contest=contest2,
                  start_date=datetime(2014, 1, 2, 3, 10, tzinfo=utc),
                  end_date=None),
        ]
        self.round1_result = {
            'status': 'OK',
            'start': '2013-10-11 08:00:00',
            'start_sec': 1381478400,
            'end': '2013-12-05 09:00:00',
            'end_sec': 1386234000,
        }
        self.round2_result = {
            'status': 'OK',
            'start': '2013-10-22 10:00:00',
            'start_sec': 1382436000,
            'end': '2013-11-05 11:00:00',
            'end_sec': 1383649200,
        }
        self.round1p_result = {
            'status': 'OK',
            'start': '2014-01-02 03:10:00',
            'start_sec': 1388632200,
            'end': None,
            'end_sec': None,
        }
        Round.objects.bulk_create(rounds)
        self.client.login(username='test_user')

    def test_ctimes_order(self):
        url = reverse('ctimes', kwargs={'contest_id': 'c1'})
        self.client.get(url)
        with fake_time(datetime(2013, 10, 1, 21, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, self.round2_result)
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, self.round1_result)
        with fake_time(datetime(2013, 10, 22, 9, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, self.round1_result)
        with fake_time(datetime(2013, 12, 11, 5, 0, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response['status'], 'NO_ROUND')
        Contest.objects.all().delete()
        self.client.get('/')  # removes current contest
        url = reverse('ctimes')
        with fake_time(datetime(2013, 12, 11, 5, 0, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response['status'], 'NO_CONTEST')

    def test_ctimes_format(self):
        url = reverse('ctimes', kwargs={'contest_id': 'c1'})
        date_regexp = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$'
        with fake_time(datetime(2013, 10, 1, 21, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            print response
            self.assertRegexpMatches(response['start'], date_regexp)
            self.assertRegexpMatches(response['end'], date_regexp)

    def test_ctimes_with_roundextension(self):
        url = reverse('ctimes', kwargs={'contest_id': 'c1'})
        rnd = Round.objects.get(name='round1')
        user = User.objects.get(username='test_user')
        RoundTimeExtension.objects.create(round=rnd, user=user, extra_time=5)
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, {
                'status': 'OK',
                'start': '2013-10-11 08:00:00',
                'start_sec': 1381478400,
                'end': '2013-12-05 09:05:00',
                'end_sec': 1386234300,
            })

    def test_ctimes_anonymous(self):
        url = reverse('ctimes', kwargs={'contest_id': 'c2'})
        self.client.logout()
        with fake_time(datetime(2014, 01, 02, 4, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, self.round1p_result)

    def test_ctimes_no_contest_id(self):
        url = reverse('ctimes')
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url, follow=True).content)
            self.assertEqual(response, self.round1p_result)

    def test_ctimes_no_end(self):
        url = reverse('ctimes', kwargs={'contest_id': 'c2'})
        with fake_time(datetime(2013, 10, 11, 7, 56, tzinfo=utc)):
            response = json.loads(self.client.get(url).content)
            self.assertEqual(response, self.round1p_result)

    def test_cross_origin(self):
        url = reverse('ctimes', kwargs={'contest_id': 'c2'})
        response = self.client.get(url)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
