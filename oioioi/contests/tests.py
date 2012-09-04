from django.test import TestCase
from django.test.utils import override_settings
from django.template import Template, RequestContext
from django.http import HttpResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from oioioi.base.tests import check_not_accessible, fake_time
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        ScoreFieldTestModel, Submission
from oioioi.contests.scores import IntegerScore
from oioioi.contests.controllers import ContestController, \
        RegistrationController
from oioioi.problems.models import Problem, ProblemStatement
from oioioi.programs.controllers import ProgrammingContestController
from datetime import datetime

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

    @override_settings(DEFAULT_CONTEST='c2')
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

    @override_settings(DEFAULT_CONTEST='c2', ONLY_DEFAULT_CONTEST=True)
    def test_only_default_contest(self):
        self.assertEqual(self.client.get('/c/c1/id').status_code, 404)

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

class PrivateRegistrationController(RegistrationController):
    def anonymous_can_enter_contest(self):
        return False
    def filter_participants(self, queryset):
        return queryset.none()

class PrivateContestController(ContestController):
    def registration_controller(self):
        return PrivateRegistrationController(self.contest)

class TestContestViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_contest_visibility(self):
        invisible_contest = Contest(id='invisible', name='Invisible Contest',
            controller_name='oioioi.contests.tests.PrivateContestController')
        invisible_contest.save()
        response = self.client.get(reverse('select_contest'))
        self.assertIn('contests/select_contest.html',
                [t.name for t in response.templates])
        self.assertEqual(len(response.context['contests']), 1)
        self.client.login(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 1)
        self.client.login(username='test_admin')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertIn('Invisible Contest', response.content)

    def test_submission_view(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get()
        self.client.login(username='test_user')
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.get(reverse('submission', kwargs=kwargs))
        def count_templates(name):
            return len([t for t in response.templates if t.name == name])
        self.assertEqual(count_templates('programs/submission_header.html'), 1)
        self.assertEqual(count_templates('programs/report.html'), 2)
        for t in ['0', '1ocen', '1a', '1b', '2', '3']:
            self.assertIn('<td>%s</td>' % (t,), response.content)
        self.assertEqual(response.content.count('34/34'), 1)
        self.assertEqual(response.content.count('0/33'), 2)
        self.assertEqual(response.content.count('0/0'), 2)
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_OK">OK</td>'), 5)  # One in the header
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_RE">Runtime error</td>'), 1)
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_WA">Wrong answer</td>'), 1)

    def test_submissions_permissions(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get()
        check_not_accessible(self, 'submission', kwargs={
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id})

        contest.controller_name = \
                'oioioi.contests.tests.PrivateContestController'
        contest.save()
        problem_instance = ProblemInstance.objects.get()
        problem = problem_instance.problem
        self.client.login(username='test_user')
        check_not_accessible(self, 'problems_list',
                kwargs={'contest_id': contest.id})
        check_not_accessible(self, 'problem_statement',
                kwargs={'contest_id': contest.id,
                    'problem_instance': problem_instance.short_name})
        check_not_accessible(self, 'my_submissions',
                kwargs={'contest_id': contest.id})
        check_not_accessible(self, 'contest_files',
                kwargs={'contest_id': contest.id})

class TestManyRounds(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission', 'test_extra_rounds']

    def test_problems_visibility(self):
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            self.client.login(username='test_admin')
            response = self.client.get(url)
            for problem_name in ['zad1', 'zad2', 'zad3', 'zad4']:
                self.assertIn(problem_name, response.content)
            self.assertIn('contests/problems_list.html',
                    [t.name for t in response.templates])
            self.assertEqual(len(response.context['problem_instances']), 4)
            self.assertTrue(response.context['show_rounds'])
            self.client.login(username='test_user')
            response = self.client.get(url)
            self.assertNotIn('zad2', response.content)
            self.assertEqual(len(response.context['problem_instances']), 3)

    def test_submissions_visibility(self):
        contest = Contest.objects.get()
        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            for problem_name in ['zad1', 'zad2', 'zad3', 'zad4']:
                self.assertIn(problem_name, response.content)
            self.assertIn('contests/my_submissions.html',
                    [t.name for t in response.templates])
            self.assertEqual(response.content.count('<td>34</td>'), 2)
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('<td>34</td>'), 4)

class TestMultilingualStatements(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_extra_statements']

    def test_multilingual_statements(self):
        pi = ProblemInstance.objects.get()
        url = reverse('problem_statement', kwargs={
            'contest_id': pi.contest.id,
            'problem_instance': pi.short_name})
        response = self.client.get(url)
        self.assertEqual('en-us-txt', response.content)
        self.client.cookies['lang'] = 'en-us'
        response = self.client.get(url)
        self.assertEqual('en-us-txt', response.content)
        self.client.cookies['lang'] = 'pl'
        response = self.client.get(url)
        self.assertEqual('pl-pdf', response.content)
        ProblemStatement.objects.filter(language='pl').delete()
        response = self.client.get(url)
        self.assertIn('%PDF', response.content)
        ProblemStatement.objects.get(language__isnull=True).delete()
        response = self.client.get(url)
        self.assertEqual('en-us-txt', response.content)


def failing_handler(env):
    raise RuntimeError('EXPECTED FAILURE')

class BrokenContestController(ProgrammingContestController):
    def fill_evaluation_environ(self, environ, submission):
        super(BrokenContestController, self).fill_evaluation_environ(environ,
                submission)
        environ['recipe'] = [
                ('failing_handler', 'oioioi.contests.tests.failing_handler'),
            ]

class TestRejudgeAndFailure(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission']

    def test_rejudge_and_failure(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.contests.tests.BrokenContestController'
        contest.save()

        submission = Submission.objects.get()
        self.client.login(username='test_admin')
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.get(reverse('rejudge_submission',
            kwargs=kwargs))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertIn('failure report', response.content)
        self.assertIn('EXPECTED FAILURE', response.content)

        self.client.login(username='test_user')
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertNotIn('failure report', response.content)
        self.assertNotIn('EXPECTED FAILURE', response.content)
