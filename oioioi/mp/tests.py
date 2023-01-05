import re
from oioioi.base.tests import TestCase
from oioioi.contests.models import UserResultForProblem
from oioioi.mp.score import FloatScore


class TestFloatScore(TestCase):
    def test_float_score(self):
        self.assertEqual(FloatScore(100) * 0.5, FloatScore(50))
        self.assertEqual(FloatScore(50) + FloatScore(50), FloatScore(100))
        self.assertLess(FloatScore(50), FloatScore(50.5))
        self.assertLess(FloatScore(99) * 0.5, FloatScore(50))
        self.assertEqual(FloatScore(45) * 0.6, 0.6 * FloatScore(45))


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
