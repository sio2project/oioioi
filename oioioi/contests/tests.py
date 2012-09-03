from django.test import TestCase
from django.test.client import Client
from django.test.utils import override_settings
from django.template import Template, RequestContext
from django.http import HttpResponse
from django.core.exceptions import ValidationError, PermissionDenied
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        ScoreFieldTestModel
from oioioi.contests.scores import IntegerScore
from oioioi.contests.controllers import ContestController
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.problems.models import Problem
from datetime import datetime

class DummyController(ProgrammingContestController):
    pass

class TestModels(TestCase):
    def test_fields_autogeneration(self):
        contest = Contest()
        contest.save()
        self.assertEqual(contest.id, 'c1')
        round = Round(contest=contest)
        round.save()
        self.assertEqual(round.name, 'Round 1')
        round = Round(contest=contest)
        round.save()
        self.assertEqual(round.name, 'Round 2')
        problem = Problem()
        problem.save()
        pi = ProblemInstance(round=round, problem=problem)
        pi.save()
        self.assertEqual(pi.contest, contest)

class TestScores(TestCase):
    def test_integer_score(self):
        s1 = IntegerScore(1)
        s2 = IntegerScore(2)
        self.assertLess(s1, s2)
        self.assertGreater(s2, s1)
        self.assertEqual(s1, IntegerScore(1))
        self.assertEqual((s1 + s2).value, 3)
        self.assertEqual(unicode(s1), '1')
        self.assertEqual(IntegerScore._from_repr(s1._to_repr()), s1)

    def test_score_field(self):
        instance = ScoreFieldTestModel(score=IntegerScore(42))
        instance.save()
        del instance

        instance = ScoreFieldTestModel.objects.get()
        self.assertTrue(isinstance(instance.score, IntegerScore))
        self.assertEqual(instance.score.value, 42)

        instance.score = "int:12"
        self.assertEqual(instance.score.value, 12)

        with self.assertRaises(ValidationError):
            instance.score = "1"
        with self.assertRaises(ValidationError):
            instance.score = "foo:1"

        instance.score = None
        instance.save()
        del instance

        instance = ScoreFieldTestModel.objects.get()
        self.assertIsNone(instance.score)


def print_contest_id_view(request, contest_id=None):
    return HttpResponse(str(request.contest.id))

def render_contest_id_view(request):
    t = Template('{{ contest.id }}')
    print RequestContext(request)
    return HttpResponse(t.render(RequestContext(request)))

class TestCurrentContest(TestCase):
    urls = 'oioioi.contests.test_urls'
    fixtures = ['test_two_empty_contests']

    def setUp(self):
        self.client = Client()

    def test_current_contest_session(self):
        self.assertEqual(self.client.get('/c/c1/id').content, 'c1')
        self.assertEqual(self.client.get('/contest_id').content, 'c1')
        self.assertEqual(self.client.get('/c/c2/id').content, 'c2')
        self.assertEqual(self.client.get('/contest_id').content, 'c2')

    def test_current_contest_most_recent(self):
        self.assertEqual(self.client.get('/contest_id').content, 'c2')

    @override_settings(DEFAULT_CONTEST='c1')
    def test_current_contest_from_settings(self):
        self.assertEqual(self.client.get('/contest_id').content, 'c1')

    def test_current_contest_processor(self):
        #self.assertEqual(self.client.get('/contest_id').content, 'c2')
        self.assertEqual(self.client.get('/render_contest_id').content, 'c2')

class TestContestController(TestCase):
    def test_order_rounds_by_focus(self):
        r1 = Round(start_date=datetime(2012, 1, 1,  8,  0),
                   end_date=  datetime(2012, 1, 1, 10,  0))
        r2 = Round(start_date=datetime(2012, 1, 1,  9, 59),
                   end_date=  datetime(2012, 1, 1, 11, 00))
        r3 = Round(start_date=datetime(2012, 1, 2,  8,  0),
                   end_date=  datetime(2012, 1, 2, 10,  0))
        rounds = [r1, r2, r3]
        controller = ContestController(None)

        class FakeRequest(object):
            def __init__(self, timestamp):
                self.timestamp = timestamp

        for date, expected_order in (
                (datetime(2011, 1, 1), [r1, r2, r3]),
                (datetime(2012, 1, 1, 7, 0), [r1, r2, r3]),
                (datetime(2012, 1, 1, 7, 55), [r1, r2, r3]),
                (datetime(2012, 1, 1, 9, 40), [r1, r2, r3]),
                (datetime(2012, 1, 1, 9, 45), [r2, r1, r3]),
                (datetime(2012, 1, 1, 9, 59, 29), [r2, r1, r3]),
                (datetime(2012, 1, 1, 9, 59, 31), [r1, r2, r3]),
                (datetime(2012, 1, 1, 10, 0, 1), [r2, r3, r1]),
                (datetime(2012, 1, 1, 11, 0, 1), [r2, r3, r1]),
                (datetime(2012, 1, 2, 2, 0, 1), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 7, 55), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 9, 0), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 11, 0), [r3, r2, r1])):
            self.assertEqual(controller.order_rounds_by_focus(
                FakeRequest(date), rounds), expected_order)
