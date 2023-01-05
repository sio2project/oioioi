import re
from datetime import datetime  # pylint: disable=E0611

from django.contrib.admin.utils import quote
from django.urls import reverse
from django.utils.timezone import utc
from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest
from oioioi.mp.score import FloatScore


class TestFloatScore(TestCase):
    def test_float_score(self):
        self.assertEqual(FloatScore(100) * 0.5, FloatScore(50))
        self.assertEqual(FloatScore(50) + FloatScore(50), FloatScore(100))
        self.assertLess(FloatScore(50), FloatScore(50.5))
        self.assertLess(FloatScore(99) * 0.5, FloatScore(50))
        self.assertEqual(FloatScore(45) * 0.6, 0.6 * FloatScore(45))


class TestMPRanking(TestCase):
    fixtures = ['test_mp_users', 'test_mp_contest']

    def _ranking_url(self, key='c'):
        contest = Contest.objects.get()
        return reverse('ranking', kwargs={'contest_id': contest.id, 'key': key})

    def test_no_zero_scores_in_ranking(self):
        self.assertTrue(self.client.login(username='test_user1'))
        with fake_time(datetime(2013, 1, 1, 0, 0, tzinfo=utc)):
            response = self.client.get(self._ranking_url())
            # Test User1 should be present in the ranking.
            print(response.content)
            self.assertTrue(re.search(b'<td[^>]*>Test User1</td>', response.content))
            # Test User4 scored 0 points.
            self.assertIsNone(re.search(b'<td[^>]*>Test User4</td>', response.content))

    def test_SubmissionScoreMultiplier_and_round_ordering(self):
        self.assertTrue(self.client.login(username='test_user1'))
        with fake_time(datetime(2013, 1, 1, 0, 0, tzinfo=utc)):
            response = self.client.get(self._ranking_url())
            # Test User1 scored 100.0 in both tasks.
            self.assertTrue(re.search(
                b'''<td[^>]*>Test User1</td>
                    <td[^>]*>200.0</td>
                    <td[^>]*><span[^>]*>100.0</span></td>
                    <td[^>]*><span[^>]*>100.0</span></td>''',
                response.content)
            )
            # test_user2 scored 100.0 in both tasks,
            # but sent the first one when the round was over - got 50.0.
            self.assertTrue(re.search(
                b'''<td[^>]*>test_user2</td>
                    <td[^>]*>150.0</td>
                    <td[^>]*><span[^>]*>100.0</span></td>
                    <td[^>]*><span[^>]*>50.0</span></td>''',
                response.content)
            )
            # Test User3 scored 100.0 in both tasks,
            # but sent both when the round was over - got 50.0 from each.
            self.assertTrue(re.search(
                b'''<td[^>]*>Test User3</td>
                    <td[^>]*>100.0</td>
                    <td[^>]*><span[^>]*>50.0</span></td>
                    <td[^>]*><span[^>]*>50.0</span></td>''',
                response.content)
            )
