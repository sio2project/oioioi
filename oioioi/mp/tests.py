from datetime import datetime
import re

from django.urls import reverse
from django.utils.timezone import utc

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, UserResultForProblem
from oioioi.mp.score import FloatScore


class TestFloatScore(TestCase):
    def test_float_score(self):
        self.assertEqual(FloatScore(100) * 0.5, FloatScore(50))
        self.assertEqual(FloatScore(50) + FloatScore(50), FloatScore(100))
        self.assertLess(FloatScore(50), FloatScore(50.5))
        self.assertLess(FloatScore(99) * 0.5, FloatScore(50))
        self.assertEqual(FloatScore(45) * 0.6, 0.6 * FloatScore(45))


class TestMPRanking(TestCase):
    fixtures = ['test_mp_users', 'test_mp_contest', 'test_mp_rankings']

    def _ranking_url(self, key='c'):
        contest = Contest.objects.get(name='contest1')
        return reverse('ranking', kwargs={'contest_id': contest.id, 'key': key})
        
    def _check_order(self, response, expected):
        prev_pos = 0
        for round_name in expected:
            pattern = round_name
            pattern_match = re.search(pattern, response.content)

            self.assertTrue(pattern_match)

            pos = pattern_match.start()
            self.assertGreater(
                pos, prev_pos, msg=('Round %s has incorrect position' % (round_name,))
            )
            prev_pos = pos

    def test_rounds_order(self):
        self.assertTrue(self.client.login(username='test_user1'))
        with fake_time(datetime(2023, 1, 6, 0, 0, tzinfo=utc)):
            response = self.client.get(self._ranking_url())
            self._check_order(response, [b'Round 2', b'Round 1'])

    def test_columns_order(self):
        self.assertTrue(self.client.login(username='test_user1'))
        with fake_time(datetime(2023, 1, 6, 0, 0, tzinfo=utc)):
            response = self.client.get(self._ranking_url())
            self._check_order(response, [
                b'<th>User</th>',
                b'<th[^>]*>Sum</th>',
                b'<th[^>]*>\s*(<a[^>]*>)*\s*squ1\s*(</a>)*\s*</th>',
                b'<th[^>]*>\s*(<a[^>]*>)*\s*squ\s*(</a>)*\s*</th>'
            ])

    def test_no_zero_scores_in_ranking(self):
        self.assertTrue(self.client.login(username='test_user1'))
        with fake_time(datetime(2023, 1, 6, 0, 0, tzinfo=utc)):
            response = self.client.get(self._ranking_url())
            # Test User should be present in the ranking.
            self.assertTrue(re.search(b'<td[^>]*>Test User1</td>', response.content))
            # Test User 4 scored 0 points - should not be present in the ranking.
            self.assertFalse(re.search(b'<td[^>]*>Test User4', response.content))


class TestSubmissionScoreMultiplier(TestCase):
    def _create_result(user, pi):
        res = UserResultForProblem()
        res.user = user
        res.problem_instance = pi
        return res

    def test_results_scores(self):
        for urfp in UserResultForProblem.objects.all():
            res = self._create_result(urfp.user, urfp.problem_instance)
            self.assertEqual(res.score, urfp.score)
