# pylint: disable=abstract-method
from datetime import datetime
from functools import partial
from django.core import mail
from collections import defaultdict

from django.test import RequestFactory
from django.test.utils import override_settings
from django.template import Template, RequestContext
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse, NoReverseMatch
from django.core.files.base import ContentFile
from django.utils.timezone import utc, LocalTimezone
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.admin.util import quote
from nose.tools import nottest

from oioioi.base.tests import TestCase, check_not_accessible, fake_time, \
    TestsUtilsMixin
from oioioi.contests.models import Contest, Round, ProblemInstance, \
        UserResultForContest, Submission, ContestAttachment, \
        RoundTimeExtension, ContestPermission, UserResultForProblem, \
        ContestView, ContestLink, ProblemStatementConfig
from oioioi.contests.scores import IntegerScore
from oioioi.contests.date_registration import date_registry
from oioioi.contests.utils import is_contest_admin, is_contest_observer, \
        can_enter_contest, rounds_times, can_see_personal_data
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.tests import SubmitFileMixin
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.models import Problem, ProblemStatement, ProblemAttachment
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.programs.models import Test
from oioioi.base.notification import NotificationHandler


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
        problem = Problem(short_name='A')
        problem.save()
        pi = ProblemInstance(round=round, problem=problem)
        pi.save()
        self.assertEqual(pi.contest, contest)
        self.assertEqual(pi.short_name, 'a')


class TestScores(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission']

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
        contest = Contest.objects.get()
        user = User.objects.get(username='test_admin')

        instance = UserResultForContest(user=user, contest=contest,
                score=IntegerScore(42))
        instance.save()
        del instance

        instance = UserResultForContest.objects.get(user=user)
        self.assertTrue(isinstance(instance.score, IntegerScore))
        self.assertEqual(instance.score.value, 42)

        instance.score = 'int:0000000000000000012'
        self.assertEqual(instance.score.value, 12)

        with self.assertRaises(ValidationError):
            instance.score = "1"
        with self.assertRaises(ValidationError):
            instance.score = "foo:1"

        instance.score = None
        instance.save()
        del instance

        instance = UserResultForContest.objects.get(user=user)
        self.assertIsNone(instance.score)

    def test_db_order(self):
        # Importing module-wide seems to break sinolpack tests.
        from oioioi.programs.models import TestReport
        scores = [tr.score for tr in
                  TestReport.objects.order_by('score').all()]
        self.assertEqual(scores, sorted(scores))


def print_contest_id_view(request):
    id = request.contest.id if request.contest else None
    return HttpResponse(str(id))


def render_contest_id_view(request):
    t = Template('{{ contest.id }}')
    print RequestContext(request)
    return HttpResponse(t.render(RequestContext(request)))


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestUrls(TestCase):
    fixtures = ['test_contest']
    urls = 'oioioi.contests.tests.test_urls'

    def test_make_patterns(self):
        # The 'urlpatterns' variable in test_urls is created using
        # 'make_patterns'. We test if it contains patterns coming from
        # different sources by trying to reverse them.
        try:
            # local contest pattern
            reverse(render_contest_id_view, kwargs={'contest_id': 'c'})
            # local neutral pattern
            reverse('print_contest_id')
            # local noncontest pattern
            reverse('noncontest_print_contest_id')
            # global contest pattern
            reverse('default_contest_view', kwargs={'contest_id': 'c'})
            # global neutral patterns
            reverse('select_contest')
            # global noncontest pattern
            reverse('move_node')
        except NoReverseMatch, e:
            self.fail(str(e))

    def test_reverse(self):
        contest = Contest.objects.get()
        contest_prefix = '/c/{}/'.format(contest.id)

        # neutral non-admin
        url = reverse('select_contest')
        self.assertFalse(url.startswith(contest_prefix))
        url = reverse('select_contest', kwargs={'contest_id': contest.id})
        self.assertTrue(url.startswith(contest_prefix))

        # neutral admin
        url = reverse('oioioiadmin:contests_contest_add')
        self.assertFalse(url.startswith(contest_prefix))
        url = reverse('oioioiadmin:contests_contest_add',
                kwargs={'contest_id': contest.id})
        self.assertTrue(url.startswith(contest_prefix))

        # contest-only non-admin
        with self.assertRaises(NoReverseMatch):
            reverse('default_contest_view')
        url = reverse('default_contest_view',
                kwargs={'contest_id': contest.id})
        self.assertTrue(url.startswith(contest_prefix))

        # contest-only admin
        with self.assertRaises(NoReverseMatch):
            reverse('oioioiadmin:contests_probleminstance_changelist')
        url = reverse('oioioiadmin:contests_probleminstance_changelist',
                kwargs={'contest_id': contest.id})
        self.assertTrue(url.startswith(contest_prefix))

        # imported view
        from oioioi.contests.views import select_contest_view
        url = reverse(select_contest_view)
        self.assertFalse(url.startswith(contest_prefix))
        url = reverse(select_contest_view, kwargs={'contest_id': contest.id})
        self.assertTrue(url.startswith(contest_prefix))

        self.client.get(contest_prefix)  # contest active

        # neutral non-admin
        url = reverse('select_contest')
        self.assertTrue(url.startswith(contest_prefix))

        # neutral admin
        url = reverse('oioioiadmin:contests_contest_add')
        self.assertTrue(url.startswith(contest_prefix))

        # contest-only non-admin
        url = reverse('default_contest_view')
        self.assertTrue(url.startswith(contest_prefix))

        # contest-only admin
        url = reverse('oioioiadmin:contests_probleminstance_changelist')
        self.assertTrue(url.startswith(contest_prefix))

        # noncontest-only
        url = reverse('noncontest_print_contest_id')
        self.assertFalse(url.startswith(contest_prefix))


class TestCurrentContest(TestCase):
    fixtures = ['test_users', 'test_two_empty_contests']
    urls = 'oioioi.contests.tests.test_urls'

    def _test_redirecting_contest_mode(self):
        # assuming contest mode contest_if_possible or contest_only
        url = reverse('print_contest_id')
        url_c1 = reverse('print_contest_id', kwargs={'contest_id': 'c1'})
        url_c2 = reverse('print_contest_id', kwargs={'contest_id': 'c2'})

        response = self.client.get(url)
        # 'c2' - most recently created contest
        self.assertRedirects(response, url_c2, fetch_redirect_response=False)

        with self.settings(DEFAULT_CONTEST='c1'):
            response = self.client.get(url)
            self.assertRedirects(response, url_c1)

            response = self.client.get(url, follow=True)
            self.assertEquals(response.content, 'c1')

        response = self.client.get(url)
        # 'c1' - most recently visited contest
        self.assertRedirects(response, url_c1)

        response = self.client.get(url, follow=True)
        self.assertEquals(response.content, 'c1')

        response = self.client.get(url_c2)
        self.assertEquals(response.content, 'c2')

        Contest.objects.get(id='c2').delete()

        response = self.client.get(url_c2)
        self.assertEquals(response.status_code, 404)

        response = self.client.get(url)
        self.assertRedirects(response, url_c1)

        response = self.client.get(url, follow=True)
        self.assertEquals(response.content, 'c1')

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_neutral_contest_mode(self):
        url = reverse('print_contest_id')
        response = self.client.get(url)
        self.assertEquals(response.content, 'None')

        url = reverse('print_contest_id', kwargs={'contest_id': 'c1'})
        response = self.client.get(url)
        self.assertEquals(response.content, 'c1')

        url = reverse(render_contest_id_view)
        response = self.client.get(url)
        self.assertEquals(response.content, 'c1')

        url = reverse('print_contest_id', kwargs={'contest_id': 'c2'})
        response = self.client.get(url)
        self.assertEquals(response.content, 'c2')

        url = reverse('noncontest_print_contest_id')
        response = self.client.get(url)
        self.assertEquals(response.content, 'None')

    @override_settings(CONTEST_MODE=ContestMode.contest_if_possible)
    def test_contest_if_possible_contest_mode(self):
        self._test_redirecting_contest_mode()

        url = reverse('noncontest_print_contest_id')
        response = self.client.get(url)
        self.assertEquals(response.content, "None")

    @override_settings(CONTEST_MODE=ContestMode.contest_only)
    def test_contest_only_contest_mode(self):
        self._test_redirecting_contest_mode()

        url = reverse('noncontest_print_contest_id')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 403)

        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 403)

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content, "None")

    @override_settings(CONTEST_MODE=ContestMode.contest_if_possible)
    def test_namespaced_redirect(self):
        url = reverse('namespace:print_contest_id')
        url_c2 = reverse('namespace:print_contest_id',
                kwargs={'contest_id': 'c2'})

        response = self.client.get(url)
        # 'c2' - most recently created contest
        self.assertRedirects(response, url_c2)


class TestContestController(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_extra_rounds']

    def test_order_rounds_by_focus(self):
        contest = Contest.objects.get()
        r1 = Round.objects.get(pk=1)
        r2 = Round.objects.get(pk=2)
        r3 = Round.objects.get(pk=3)

        r1.start_date = datetime(2012, 1, 1, 8, 0, tzinfo=utc)
        r1.end_date = datetime(2012, 1, 1, 10, 0, tzinfo=utc)
        r1.save()

        r2.start_date = datetime(2012, 1, 1, 9, 59, tzinfo=utc)
        r2.end_date = datetime(2012, 1, 1, 11, 00, tzinfo=utc)
        r2.save()

        r3.start_date = datetime(2012, 1, 2, 8, 0, tzinfo=utc)
        r3.end_date = datetime(2012, 1, 2, 10, 0, tzinfo=utc)
        r3.save()

        rounds = [r1, r2, r3]

        class FakeRequest(object):
            def __init__(self, timestamp, contest):
                self.timestamp = timestamp
                self.user = AnonymousUser()
                self.contest = contest

        for date, expected_order in (
                (datetime(2011, 1, 1, tzinfo=utc), [r1, r2, r3]),
                (datetime(2012, 1, 1, 7, 0, tzinfo=utc), [r1, r2, r3]),
                (datetime(2012, 1, 1, 7, 55, tzinfo=utc), [r1, r2, r3]),
                (datetime(2012, 1, 1, 9, 40, tzinfo=utc), [r1, r2, r3]),
                (datetime(2012, 1, 1, 9, 55, tzinfo=utc), [r2, r1, r3]),
                (datetime(2012, 1, 1, 9, 59, 29, tzinfo=utc), [r2, r1, r3]),
                (datetime(2012, 1, 1, 9, 59, 31, tzinfo=utc), [r1, r2, r3]),
                (datetime(2012, 1, 1, 10, 0, 1, tzinfo=utc), [r2, r1, r3]),
                (datetime(2012, 1, 1, 11, 0, 1, tzinfo=utc), [r2, r1, r3]),
                (datetime(2012, 1, 1, 12, 0, 1, tzinfo=utc), [r2, r1, r3]),
                (datetime(2012, 1, 2, 2, 0, 1, tzinfo=utc), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 7, 55, tzinfo=utc), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 9, 0, tzinfo=utc), [r3, r2, r1]),
                (datetime(2012, 1, 2, 2, 11, 0, tzinfo=utc), [r3, r2, r1])):
            self.assertEqual(contest.controller.order_rounds_by_focus(
                FakeRequest(date, contest), rounds), expected_order)


class TestContestViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission']

    def test_recent_contests_list(self):
        contest = Contest.objects.get()
        invisible_contest = Contest(id='invisible', name='Invisible Contest',
            controller_name='oioioi.contests.tests.PrivateContestController')
        invisible_contest.save()

        self.client.login(username='test_admin')
        self.client.get('/c/%s/dashboard/' % contest.id)
        self.client.get('/c/%s/dashboard/' % invisible_contest.id)
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertContains(response, 'Test contest')
        self.assertContains(response, 'Invisible Contest')
        self.client.logout()

        self.client.login(username='test_admin')
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertIn('dropdown open', response.content)
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertNotIn('dropdown open', response.content)

        contests = [cv.contest for cv in ContestView.objects.all()]
        self.assertEqual(contests, [contest, invisible_contest])

        self.client.get('/c/%s/dashboard/' % invisible_contest.id)
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        contests = [cv.contest for cv in ContestView.objects.all()]
        self.assertEqual(contests, [invisible_contest, contest])

    @override_settings(CONTEST_MODE=ContestMode.neutral)
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
        submission = Submission.objects.get(pk=1)
        self.client.login(username='test_user')
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.get(reverse('submission', kwargs=kwargs))

        def count_templates(name):
            return len([t for t in response.templates if t.name == name])
        self.assertEqual(count_templates('programs/submission_header.html'), 1)
        self.assertEqual(count_templates('programs/report.html'), 2)
        for t in ['0', '1ocen', '1a', '1b', '2', '3']:
            self.assertIn('<td>%s' % (t,), response.content)
        self.assertEqual(response.content.count('34/34'), 1)
        self.assertEqual(response.content.count('0/33'), 2)
        self.assertEqual(response.content.count('0/0'), 2)
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_OK">OK</td>'), 5)  # One in the header
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_RE">Runtime error</td>'), 1)
        self.assertEqual(response.content.count(
            '<td class="subm_status subm_WA">Wrong answer</td>'), 1)
        self.assertIn('program exited with code 1', response.content)

    def test_submissions_permissions(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get(pk=1)
        check_not_accessible(self, 'submission', kwargs={
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id})

        contest.controller_name = \
                'oioioi.contests.tests.PrivateContestController'
        contest.save()
        problem_instance = ProblemInstance.objects.get()
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


class TestManyRounds(TestsUtilsMixin, TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_extra_rounds',
            'test_permissions']

    def test_problems_visibility(self):
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            for user in ['test_admin', 'test_contest_admin']:
                self.client.login(username=user)
                response = self.client.get(url)
                self.assertAllIn(['zad1', 'zad2', 'zad3', 'zad4'],
                        response.content)
                self.assertIn('contests/problems_list.html',
                        [t.name for t in response.templates])
                self.assertEqual(len(response.context['problem_instances']), 4)
                self.assertTrue(response.context['show_rounds'])

            for user in ['test_user', 'test_observer']:
                self.client.login(username=user)
                response = self.client.get(url)
                self.assertAllIn(['zad1', 'zad3', 'zad4'], response.content)
                self.assertNotIn('zad2', response.content)
                self.assertEqual(len(response.context['problem_instances']), 3)

    def test_submissions_visibility(self):
        contest = Contest.objects.get()
        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertAllIn(['zad1', 'zad3', 'zad4'], response.content)
            self.assertNoneIn(['zad2', ], response.content)

            self.assertIn('contests/my_submissions.html',
                    [t.name for t in response.templates])
            self.assertEqual(response.content.count('>34</td>'), 2)

        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('>34</td>'), 4)

        with fake_time(datetime(2012, 7, 31, 20, tzinfo=utc)):
            response = self.client.get(url)
            self.assertNotIn('>34</td>', response.content)
            self.assertNotIn('Score', response.content)

        with fake_time(datetime(2012, 7, 31, 21, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('>34</td>'), 1)

        with fake_time(datetime(2012, 7, 31, 22, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('>34</td>'), 2)

        round4 = Round.objects.get(pk=4)
        user = User.objects.get(username='test_user')
        ext = RoundTimeExtension(user=user, round=round4, extra_time=60)
        ext.save()

        with fake_time(datetime(2012, 7, 31, 22, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('>34</td>'), 1)

        round4.end_date = datetime(2012, 8, 10, 0, 0, tzinfo=utc)
        round4.results_date = datetime(2012, 8, 10, 0, 10, tzinfo=utc)
        round4.save()

        ext.extra_time = 0
        ext.save()

        with fake_time(datetime(2012, 8, 10, 0, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('>34</td>'), 1)

        ext.extra_time = 20
        ext.save()

        with fake_time(datetime(2012, 8, 10, 0, 15, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('>34</td>'), 1)

        with fake_time(datetime(2012, 8, 10, 0, 21, tzinfo=utc)):
            response = self.client.get(url)
            self.assertEqual(response.content.count('>34</td>'), 2)

    def test_mixin_past_rounds_hidden_during_prep_time(self):
        contest = Contest.objects.get()
        contest.controller_name = \
            'oioioi.contests.tests.PastRoundsHiddenContestController'
        contest.save()

        user = User.objects.get(username='test_user')

        r1 = Round.objects.get(pk=1)
        r1.end_date = datetime(2012, 7, 30, 21, 40, tzinfo=utc)
        r1.save()

        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2012, 7, 31, 21, 01, tzinfo=utc)):
            # r3, r4 are active
            self.client.login(username=user)
            response = self.client.get(url)
            self.assertAllIn(['zad3', 'zad4'], response.content)
            self.assertEqual(len(response.context['problem_instances']), 2)

        with fake_time(datetime(2015, 7, 31, 20, 01, tzinfo=utc)):
            # r1,r3,r4 are past, preparation time for r2
            self.client.login(username=user)
            response = self.client.get(url)
            self.assertEqual(len(response.context['problem_instances']), 0)

        with fake_time(datetime(2015, 7, 31, 20, 28, tzinfo=utc)):
            # r2 is active
            self.client.login(username=user)
            response = self.client.get(url)
            self.assertAllIn(['zad2'], response.content)
            self.assertEqual(len(response.context['problem_instances']), 1)

        r2 = Round.objects.get(pk=2)
        r2.start_date = datetime(2012, 7, 31, 21, 40, tzinfo=utc)
        r2.save()

        with fake_time(datetime(2012, 7, 31, 21, 29, tzinfo=utc)):
            # r1,r3,r4 are past, break = (21.27, 21.40) -- first half
            self.client.login(username=user)
            response = self.client.get(url)
            self.assertAllIn(['zad1', 'zad3', 'zad4'], response.content)
            self.assertEqual(len(response.context['problem_instances']), 3)

        with fake_time(datetime(2012, 7, 31, 21, 35, tzinfo=utc)):
            # r1,r3,r3 are past, break = (21.27, 21.40) -- second half
            self.client.login(username=user)
            response = self.client.get(url)
            print response.context['problem_instances']
            self.assertEqual(len(response.context['problem_instances']), 0)

        with fake_time(datetime(2012, 7, 31, 21, 41, tzinfo=utc)):
            # r2 is active
            self.client.login(username=user)
            response = self.client.get(url)
            self.assertAllIn(['zad2'], response.content)
            print response.context['problem_instances']
            self.assertEqual(len(response.context['problem_instances']), 1)

        self.client.login(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 1)


class TestMultilingualStatements(TestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_extra_statements']

    def test_multilingual_statements(self):
        pi = ProblemInstance.objects.get()
        url = reverse('problem_statement', kwargs={
            'contest_id': pi.contest.id,
            'problem_instance': pi.short_name})
        response = self.client.get(url)
        self.assertStreamingEqual(response, 'en-txt')
        self.client.cookies['lang'] = 'en'
        response = self.client.get(url)
        self.assertStreamingEqual(response, 'en-txt')
        self.client.cookies['lang'] = 'pl'
        response = self.client.get(url)
        self.assertStreamingEqual(response, 'pl-pdf')
        ProblemStatement.objects.filter(language='pl').delete()
        response = self.client.get(url)
        self.assertTrue(response.streaming)
        content = self.streamingContent(response)
        self.assertIn('%PDF', content)
        ProblemStatement.objects.get(language__isnull=True).delete()
        response = self.client.get(url)
        self.assertStreamingEqual(response, 'en-txt')


class ContestWithoutStatementsController(ProgrammingContestController):
    def default_can_see_statement(self, request, problem_instance):
        return False


class TestStatementsVisibility(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    def test_controller(self):
        contest = Contest.objects.get()
        self.client.login(username='test_user')
        response = self.client.get(reverse('problems_list',
                kwargs={'contest_id': contest.id}))
        self.assertContains(response, 'zad1')
        self.assertContains(response, u'Sum\u017cyce')

        pi = ProblemInstance.objects.get()
        url = reverse('problem_statement',
                kwargs={'contest_id': contest.id,
                        'problem_instance': pi.short_name})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        contest.controller_name = \
               'oioioi.contests.tests.tests.ContestWithoutStatementsController'
        contest.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_statements_config(self):
        contest = Contest.objects.get()
        psc = ProblemStatementConfig(contest=contest)
        psc.save()

        self.assertEqual(psc.visible, 'AUTO')

        pi = ProblemInstance.objects.get()
        url = reverse('problem_statement',
                kwargs={'contest_id': contest.id,
                        'problem_instance': pi.short_name})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        psc.visible = 'NO'
        psc.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        contest.controller_name = \
               'oioioi.contests.tests.tests.ContestWithoutStatementsController'
        contest.save()

        psc.visible = 'AUTO'
        psc.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        psc.visible = 'YES'
        psc.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


def failing_handler(env):
    raise RuntimeError('EXPECTED FAILURE')


class BrokenContestController(ProgrammingContestController):
    def fill_evaluation_environ(self, environ, submission):
        super(BrokenContestController, self).fill_evaluation_environ(environ,
                submission)
        environ['recipe'] = [
                (
                    'failing_handler',
                    'oioioi.contests.tests.tests.failing_handler'
                ),
            ]


class TestRejudgeAndFailure(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission']

    def test_rejudge_request(self):
        contest = Contest.objects.get()
        kwargs = {'contest_id': contest.id, 'submission_id': 1}
        rejudge_url = reverse('rejudge_submission', kwargs=kwargs)
        self.client.login(username='test_admin')
        response = self.client.get(rejudge_url)
        self.assertEqual(405, response.status_code)
        self.assertNotIn('My submissions', response.content)
        self.assertIn('OIOIOI', response.content)
        self.assertIn('method is not allowed', response.content)
        self.assertIn('Log out', response.content)

    def test_rejudge_and_failure(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.contests.tests.tests.BrokenContestController'
        contest.save()

        submission = Submission.objects.get(pk=1)
        self.client.login(username='test_admin')
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.post(reverse('rejudge_submission',
                kwargs=kwargs))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertIn('failure report', response.content)
        self.assertIn('EXPECTED FAILURE', response.content)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('System Error evaluating submission #',
                      mail.outbox[0].subject)
        self.assertIn('Traceback (most recent call last)', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['admin@example.com'])

        self.client.login(username='test_user')
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertNotIn('failure report', response.content)
        self.assertNotIn('EXPECTED FAILURE', response.content)


class TestRejudgeTypesView(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_submission',
                'test_extra_problem', 'test_another_submission']

    def test_view(self):
        self.client.login(username='test_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest

        post_data = {'action': 'rejudge_action',
                     '_selected_action': ['1', '2']}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data)
        self.assertIn('You have selected 2 submission(s) from 1 problem(s)',
                      response.content)
        self.assertIn('Rejudge submissions on judged tests only',
                      response.content)
        self.assertIn('Tests:', response.content)

        problem_instance = ProblemInstance.objects.get(id=2)
        submission = Submission()
        submission.problem_instance = problem_instance
        submission.save()

        post_data['_selected_action'] = ['1', '2', '3']
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data)
        self.assertIn('You have selected 3 submission(s) from 2 problem(s)',
                      response.content)
        self.assertNotIn('Rejudge submissions on judged tests only',
                         response.content)
        self.assertNotIn('Tests:', response.content)


class TestContestAdmin(TestCase):
    fixtures = ['test_users']

    def test_simple_contest_create_and_change(self):
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {
                'name': 'cname',
                'id': 'cid',
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name':
                    'oioioi.programs.controllers.ProgrammingContestController',
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('was added successfully', response.content)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'cid')
        self.assertEqual(contest.name, 'cname')
        self.assertEqual(contest.round_set.count(), 1)
        round = contest.round_set.get()
        self.assertEqual(round.start_date,
                datetime(2012, 2, 3, 4, 5, 6, tzinfo=LocalTimezone()))
        self.assertEqual(round.end_date,
                datetime(2012, 2, 4, 5, 6, 7, tzinfo=LocalTimezone()))
        self.assertEqual(round.results_date,
                datetime(2012, 2, 5, 6, 7, 8, tzinfo=LocalTimezone()))

        url = reverse('oioioiadmin:contests_contest_change',
                args=(quote('cid'),)) + '?simple=true'
        response = self.client.get(url)
        self.assertIn('2012-02-05', response.content)
        self.assertIn('06:07:08', response.content)

        post_data = {
                'name': 'cname1',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-04',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'cid')
        self.assertEqual(contest.name, 'cname1')
        self.assertEqual(contest.round_set.count(), 1)
        round = contest.round_set.get()
        self.assertEqual(round.start_date,
                datetime(2013, 2, 3, 14, 5, 6, tzinfo=LocalTimezone()))
        self.assertEqual(round.end_date,
                datetime(2013, 2, 4, 15, 6, 7, tzinfo=LocalTimezone()))
        self.assertEqual(round.results_date,
                datetime(2013, 2, 5, 16, 7, 8, tzinfo=LocalTimezone()))

        url = reverse('oioioiadmin:contests_contest_change',
                args=(quote('cid'),)) + '?simple=true'
        response = self.client.get(url)
        post_data = {
                'name': 'cname1',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-01',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Start date should be before end date.",
                response.content)

    def test_admin_permissions(self):
        url = reverse('oioioiadmin:contests_contest_changelist')

        self.client.login(username='test_user')
        check_not_accessible(self, url)

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # without set request.contest
        with self.assertRaises(NoReverseMatch):
            reverse('oioioiadmin:contests_probleminstance_changelist')

        c_id = 'test_contest'
        c = Contest.objects.create(id=c_id,
            controller_name='oioioi.programs.controllers.'
            'ProgrammingContestController',
            name='Test contest')
        contest_prefix = '/c/{}/'.format(c_id)

        url = reverse('oioioiadmin:contests_probleminstance_changelist',
                kwargs={'contest_id': c_id})
        self.assertTrue(url.startswith(contest_prefix))
        url = url[len(contest_prefix) - 1:]

        self.client.login(username='test_user')
        check_not_accessible(self, url)

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # with request.contest
        self.client.get(contest_prefix)
        url = reverse('oioioiadmin:contests_probleminstance_changelist')

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.client.login(username='test_user')
        check_not_accessible(self, url)

        user = User.objects.get(username='test_user')
        ContestPermission(user=user, contest=c,
                          permission='contests.contest_admin').save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestAttachments(TestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    def test_attachments(self):
        contest = Contest.objects.get()
        problem = Problem.objects.get()
        ca = ContestAttachment(contest=contest,
                description='contest-attachment',
                content=ContentFile('content-of-conatt', name='conatt.txt'))
        ca.save()
        pa = ProblemAttachment(problem=problem,
                description='problem-attachment',
                content=ContentFile('content-of-probatt', name='probatt.txt'))
        pa.save()
        round = Round.objects.get(pk=1)
        ra = ContestAttachment(contest=contest, description='round-attachment',
                content=ContentFile('content-of-roundatt',
                    name='roundatt.txt'),
                round=round)
        ra.save()

        self.client.login(username='test_user')
        response = self.client.get(reverse('contest_files',
            kwargs={'contest_id': contest.id}))
        self.assertEqual(response.status_code, 200)
        for part in ['contest-attachment', 'conatt.txt', 'problem-attachment',
                     'probatt.txt', 'round-attachment', 'roundatt.txt']:
            self.assertIn(part, response.content)
        response = self.client.get(reverse('contest_attachment',
            kwargs={'contest_id': contest.id, 'attachment_id': ca.id}))
        self.assertStreamingEqual(response, 'content-of-conatt')
        response = self.client.get(reverse('problem_attachment',
            kwargs={'contest_id': contest.id, 'attachment_id': pa.id}))
        self.assertStreamingEqual(response, 'content-of-probatt')
        response = self.client.get(reverse('contest_attachment',
            kwargs={'contest_id': contest.id, 'attachment_id': ra.id}))
        self.assertStreamingEqual(response, 'content-of-roundatt')

        with fake_time(datetime(2011, 7, 10, tzinfo=utc)):
            response = self.client.get(reverse('contest_files',
                kwargs={'contest_id': contest.id}))
            self.assertEqual(response.status_code, 200)
            for part in ['contest-attachment', 'conatt.txt']:
                self.assertIn(part, response.content)
            for part in ['problem-attachment', 'probatt.txt',
                         'round-attachment', 'roundatt.txt']:
                self.assertNotIn(part, response.content)
            response = self.client.get(reverse('contest_attachment',
                kwargs={'contest_id': contest.id, 'attachment_id': ca.id}))
            self.assertStreamingEqual(response, 'content-of-conatt')
            check_not_accessible(self, 'problem_attachment',
                 kwargs={'contest_id': contest.id, 'attachment_id': pa.id})
            check_not_accessible(self, 'contest_attachment',
                 kwargs={'contest_id': contest.id, 'attachment_id': ra.id})


class TestSubmission(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_submission',
                'test_extra_problem']

    def setUp(self):
        self.client.login(username='test_user')

    def test_submission_completed_notification(self):
        msg_count = defaultdict(int)

        @classmethod
        def fake_send_notification(cls, user, notification_type,
                    notification_message, notificaion_message_arguments):
            if user.pk == 1002:
                msg_count['user_1002_notifications'] += 1
            if user.pk == 1001:
                msg_count['user_1001_notifications'] += 1

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification

        submission = Submission.objects.get(pk=1)
        controller = submission.problem_instance.contest.controller
        controller.submission_judged(submission)
        controller.submission_judged(submission,
                rejudged=True)

        # Check if a notification for user 1001 was send
        # And user 1002 doesn't received a notification
        self.assertEqual(msg_count['user_1001_notifications'], 1)
        self.assertEqual(msg_count['user_1002_notifications'], 0)

        NotificationHandler.send_notification = send_notification_backup

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_repeated_submission_fail(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance)
        response = self.submit_file(contest, problem_instance)
        self.assertEqual(200, response.status_code)
        self.assertIn('Please resubmit', response.content)

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_repeated_submission_different_problems(self):
        contest = Contest.objects.get()
        problem_instance1 = ProblemInstance.objects.get(pk=1)
        problem_instance2 = ProblemInstance.objects.get(pk=2)
        response = self.submit_file(contest, problem_instance1)
        response = self.submit_file(contest, problem_instance2)
        self._assertSubmitted(contest, response)

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_repeated_submission_success(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance)
        response = self.submit_file(contest, problem_instance)
        response = self.submit_file(contest, problem_instance)
        self._assertSubmitted(contest, response)

    def test_simple_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=utc)
        round.save()

        with fake_time(datetime(2012, 7, 10, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Sorry, there are no problems', response.content)

        with fake_time(datetime(2012, 7, 31, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 10, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 11, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Sorry, there are no problems', response.content)

    def test_huge_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance,
                                    file_size=102405)
        self.assertIn('File size limit exceeded.', response.content)

    def test_size_limit_accuracy(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance,
                                    file_size=102400)
        self._assertSubmitted(contest, response)

    def test_submissions_limitation(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        problem_instance.submissions_limit = 2
        problem_instance.save()
        response = self.submit_file(contest, problem_instance)
        self._assertSubmitted(contest, response)
        response = self.submit_file(contest, problem_instance)
        self.assertEqual(200, response.status_code)
        self.assertIn('Submission limit for the problem', response.content)

    def _assertUnsupportedExtension(self, contest, problem_instance, name,
                                    ext):
        response = self.submit_file(contest, problem_instance,
                file_name='%s.%s' % (name, ext))
        self.assertIn('Unknown or not supported file extension.',
                        response.content)

    def test_extension_checking(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        self._assertUnsupportedExtension(contest, problem_instance, 'xxx', '')
        self._assertUnsupportedExtension(contest, problem_instance, 'xxx', 'e')
        self._assertUnsupportedExtension(contest, problem_instance,
                'xxx', 'cppp')
        response = self.submit_file(contest, problem_instance,
                file_name='a.tar.cpp')
        self._assertSubmitted(contest, response)

    def test_code_pasting(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_code(contest, problem_instance, 'some code')
        self._assertSubmitted(contest, response)
        response = self.submit_code(contest, problem_instance, 'some code', '')
        self.assertIn('You have to choose programming language.',
                response.content)
        response = self.submit_code(contest, problem_instance, '')
        self.assertIn('You have to either choose file or paste code.',
                response.content)
        response = self.submit_code(contest, problem_instance, 'some code',
                send_file=True)
        self.assertIn('You have to either choose file or paste code.',
                response.content)

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_pasting_unicode_code(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_code(contest, problem_instance, unichr(12345),
                user='test_user')
        self._assertSubmitted(contest, response)

    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c']})
    def test_limiting_extensions(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        self._assertUnsupportedExtension(contest, problem_instance,
                'xxx', 'cpp')
        response = self.submit_file(contest, problem_instance, file_name='a.c')
        self._assertSubmitted(contest, response)


class TestRoundExtension(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_extra_rounds']

    def test_round_extension(self):
        contest = Contest.objects.get()
        round1 = Round.objects.get(pk=1)
        round2 = Round.objects.get(pk=2)
        problem_instance1 = ProblemInstance.objects.get(pk=1)
        problem_instance2 = ProblemInstance.objects.get(pk=2)
        self.assertTrue(problem_instance1.round == round1)
        self.assertTrue(problem_instance2.round == round2)
        round1.start_date = datetime(2012, 7, 31, tzinfo=utc)
        round1.end_date = datetime(2012, 8, 5, tzinfo=utc)
        round1.save()
        round2.start_date = datetime(2012, 8, 10, tzinfo=utc)
        round2.end_date = datetime(2012, 8, 12, tzinfo=utc)
        round2.save()

        user = User.objects.get(username='test_user')
        ext = RoundTimeExtension(user=user, round=round1, extra_time=10)
        ext.save()

        with fake_time(datetime(2012, 8, 5, 0, 5, tzinfo=utc)):
            self.client.login(username='test_user2')
            response = self.submit_file(contest, problem_instance1)
            self.assertEqual(200, response.status_code)
            self.assertIn('Sorry, there are no problems', response.content)
            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance1)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 5, 0, 11, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance1)
            self.assertEqual(200, response.status_code)
            self.assertIn('Sorry, there are no problems', response.content)

        with fake_time(datetime(2012, 8, 12, 0, 5, tzinfo=utc)):
            response = self.submit_file(contest, problem_instance2)
            self.assertEqual(200, response.status_code)
            self.assertIn('Sorry, there are no problems', response.content)

    def test_round_extension_admin(self):
        self.client.login(username='test_admin')

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_roundtimeextension_add')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {
                'user': '1001',
                'round': '1',
                'extra_time': '31415926'
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('was added successfully', response.content)
        self.assertEqual(RoundTimeExtension.objects.count(), 1)
        rext = RoundTimeExtension.objects.get()
        self.assertEqual(rext.round, Round.objects.get(pk=1))
        self.assertEqual(rext.user, User.objects.get(pk=1001))
        self.assertEqual(rext.extra_time, 31415926)

        url = reverse('oioioiadmin:contests_roundtimeextension_change',
                args=('1',))
        response = self.client.get(url)
        self.assertIn('31415926', response.content)
        post_data = {
                'user': '1001',
                'round': '1',
                'extra_time': '27182818'
            }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoundTimeExtension.objects.count(), 1)
        rext = RoundTimeExtension.objects.get()
        self.assertEqual(rext.extra_time, 27182818)


class TestPermissions(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submissions', 'test_permissions']

    def get_fake_request_factory(self, contest=None):
        factory = RequestFactory()

        def with_timestamp(user, timestamp):
            request = factory.request()
            request.contest = contest
            request.user = user
            request.timestamp = timestamp
            return request

        return with_timestamp

    def setUp(self):
        self.contest = Contest.objects.get()
        self.contest.controller_name = \
            'oioioi.contests.tests.PrivateContestController'
        self.contest.save()
        self.ccontr = self.contest.controller
        self.round = Round.objects.get()
        self.round.start_date = datetime(2012, 7, 31, tzinfo=utc)
        self.round.end_date = datetime(2012, 8, 5, tzinfo=utc)
        self.round.save()

        self.during = datetime(2012, 8, 1, tzinfo=utc)

        self.observer = User.objects.get(username='test_observer')
        self.cadmin = User.objects.get(username='test_contest_admin')
        self.factory = self.get_fake_request_factory(self.contest)

    def test_utils(self):
        ofactory = partial(self.factory, self.observer)
        cfactory = partial(self.factory, self.cadmin)
        ufactory = partial(self.factory,
                           User.objects.get(username='test_user'))
        self.assertFalse(can_enter_contest(ufactory(self.during)))
        self.assertTrue(is_contest_admin(cfactory(self.during)))
        self.assertTrue(can_enter_contest(cfactory(self.during)))
        self.assertTrue(is_contest_observer(ofactory(self.during)))
        self.assertTrue(can_enter_contest(ofactory(self.during)))

    def test_privilege_manipulation(self):
        self.assertTrue(self.observer.has_perm('contests.contest_observer',
            self.contest))
        self.assertFalse(self.observer.has_perm('contests.contest_admin',
            self.contest))

        self.assertFalse(self.cadmin.has_perm('contests.contest_observer',
            self.contest))
        self.assertTrue(self.cadmin.has_perm('contests.contest_admin',
            self.contest))

        test_user = User.objects.get(username='test_user')

        self.assertFalse(test_user.has_perm('contests.contest_observer',
            self.contest))
        self.assertFalse(test_user.has_perm('contests.contest_admin',
            self.contest))

        del test_user._contest_perms_cache
        ContestPermission(user=test_user, contest=self.contest,
            permission='contests.contest_observer').save()
        self.assertTrue(test_user.has_perm('contests.contest_observer',
            self.contest))

        del test_user._contest_perms_cache
        ContestPermission(user=test_user, contest=self.contest,
            permission='contests.contest_admin').save()
        self.assertTrue(test_user.has_perm('contests.contest_observer',
            self.contest))

    def test_menu(self):
        self.client.login(username='test_contest_admin')
        response = self.client.get(reverse('default_contest_view',
            kwargs={'contest_id': self.contest.id}), follow=True)
        self.assertNotIn('System Administration', response.content)
        self.assertIn('Contest Administration', response.content)
        self.assertNotIn('Observer Menu', response.content)

        self.client.login(username='test_observer')
        response = self.client.get(reverse('problems_list',
            kwargs={'contest_id': self.contest.id}), follow=True)
        self.assertIn('Observer Menu', response.content)


class TestSubmissionChangeKind(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_multiple_submissions']

    def setUp(self):
        self.client.login(username='test_admin')

    def change_kind(self, submission, kind):
        contest = Contest.objects.get()
        url1 = reverse('change_submission_kind',
                       kwargs={'contest_id': contest.id,
                               'submission_id': submission.id,
                               'kind': kind})
        response = self.client.post(url1, follow=True)
        self.assertContains(response, 'has been changed.')
        return response

    def test_kind_change(self):
        pi = ProblemInstance.objects.get()
        contest = Contest.objects.get()
        s1 = Submission.objects.get(id=4)  # 100 points
        s2 = Submission.objects.get(id=5)  # 90 points

        self.change_kind(s1, 'NORMAL')
        self.change_kind(s2, 'NORMAL')

        urp = UserResultForProblem.objects.get(user__username='test_user',
                problem_instance=pi)
        self.assertEqual(urp.score, 90)

        self.change_kind(s2, 'IGNORED')
        urp = UserResultForProblem.objects.get(user__username='test_user',
                                               problem_instance=pi)
        urc = UserResultForContest.objects.get(user__username='test_user',
                                               contest=contest)
        self.assertEqual(urp.score, 100)
        self.assertEqual(urc.score, 100)

        self.change_kind(s2, 'NORMAL')

        urp = UserResultForProblem.objects.get(user__username='test_user',
                problem_instance=pi)
        self.assertEqual(urp.score, 90)

        self.change_kind(s2, 'IGNORED_HIDDEN')
        urp = UserResultForProblem.objects.get(user__username='test_user',
                                               problem_instance=pi)
        urc = UserResultForContest.objects.get(user__username='test_user',
                                               contest=contest)
        self.assertEqual(urp.score, 100)
        self.assertEqual(urc.score, 100)


class TestDeleteSelectedSubmissions(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_submission',
                'test_another_submission', 'test_permissions']

    def test_delete_one_submission(self):
        self.client.login(username='test_contest_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest

        post_data = {'action': 'delete_selected',
                     '_selected_action': ['1']}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data)

        # Test confirmation dialog
        self.assertIn(
            'Are you sure you want to delete the selected submission?',
            response.content)
        self.assertIn(
            'All of the following objects and their related items ' +
            'will be deleted:',
            response.content)
        self.assertIn('Submission(', response.content)
        self.assertIn('NORMAL, OK)', response.content)
        self.assertIn('Score report', response.content)
        self.assertIn('Compilation report', response.content)
        self.assertIn('Program submission: Submission(1, ', response.content)

        # Delete it and check if there is one submission remaining
        post_data = {'action': 'delete_selected',
                     '_selected_action': ['1'],
                     'post': 'yes'}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data,
            follow=True)

        self.assertIn('Successfully deleted 1 submission.', response.content)
        self.assertIn('1 total', response.content)

    def test_delete_many_submissions(self):
        self.client.login(username='test_contest_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest

        post_data = {'action': 'delete_selected',
                     '_selected_action': ['1', '2']}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data)

        # Test confirmation dialog
        self.assertIn(
            'Are you sure you want to delete the selected submissions?',
            response.content)
        self.assertIn(
            'All of the following objects and their related items ' +
            'will be deleted:',
            response.content)
        self.assertIn('Submission(', response.content)
        self.assertIn('NORMAL, OK)', response.content)
        self.assertIn('Score report', response.content)
        self.assertIn('Compilation report', response.content)
        self.assertIn('Program submission: Submission(1, ', response.content)

        # Delete them and check if there are no submissions remaining
        post_data = {'action': 'delete_selected',
                     '_selected_action': ['1', '2'],
                     'post': 'yes'}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data,
            follow=True)

        self.assertIn('Successfully deleted 2 submissions.', response.content)
        self.assertIn('0 total', response.content)


class TestSubmitSelectOneProblem(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    def test_problems_list(self):
        self.client.login(username='test_user2')
        contest = Contest.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertEqual(len(form.fields['problem_instance_id'].choices), 1)


class TestSubmitSelectManyProblems(TestCase):
    fixtures = ['test_users', 'test_extra_problem', 'test_contest',
             'test_full_package', 'test_problem_instance']

    def test_problems_list(self):
        self.client.login(username='test_user2')
        contest = Contest.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        form = response.context['form']
        # +1 because of blank field
        self.assertEqual(len(form.fields['problem_instance_id'].choices), 3)


class TestDateRegistry(TestCase):
    fixtures = ['test_contest']

    def test_registry_content(self):
        contest = Contest.objects.get()
        registry_length = len(date_registry.tolist(contest.id))
        rounds_count = Round.objects.filter(contest=contest.id).count()

        self.assertEqual(registry_length, 4 * rounds_count)


class ContestWithPublicResultsController(ProgrammingContestController):
    def separate_public_results(self):
        return True


class TestPublicResults(TestCase):
    fixtures = ['test_users', 'test_contest']

    def _change_controller(self, public_results=False):
        contest = Contest.objects.get()
        if public_results:
            contest.controller_name = \
              'oioioi.contests.tests.tests.ContestWithPublicResultsController'
        else:
            contest.controller_name = \
                    'oioioi.programs.controllers.ProgrammingContestController'
        contest.save()

    def test_round_inline(self):
        self.client.login(username='test_admin')

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_contest_change',
                args=(quote('c'),))

        response = self.client.get(url)
        self.assertNotContains(response, 'Public results date')

        self._change_controller(public_results=True)

        response = self.client.get(url)
        self.assertContains(response, 'Public results date')

    def _check_public_results(self, expected):
        before_results = datetime(2012, 6, 20, 8, 0, tzinfo=utc)
        after_results_before_public = datetime(2012, 8, 20, 8, 0, tzinfo=utc)
        after_public = datetime(2012, 10, 20, 8, 0, tzinfo=utc)
        dates = [before_results, after_results_before_public, after_public]

        request = RequestFactory().request()
        request.contest = Contest.objects.get(id='c')
        request.user = User.objects.get(username='test_admin')
        round = Round.objects.get()

        rtime = rounds_times(request)[round]
        for date, exp in zip(dates, expected):
            self.assertEquals(rtime.public_results_visible(date), exp)

    def test_public_results_visible(self):
        # Default controller implementation, there is only one results date
        self._check_public_results([False, True, True])

        self._change_controller(public_results=True)
        # public_results_date == None, so public results will never be visible
        self._check_public_results([False, False, False])

        round = Round.objects.get()
        round.public_results_date = datetime(2012, 9, 20, 8, 0, tzinfo=utc)
        round.save()
        self._check_public_results([False, False, True])


class TestContestLinks(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_menu(self):
        self.client.login(username='test_user2')
        contest = Contest.objects.get()

        ContestLink(contest=contest, description='Test Menu Item 1',
                    url='/test_menu_link1', order=10).save()
        ContestLink(contest=contest, description='Test Menu Item 2',
                    url='/test_menu_link2').save()

        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Test Menu Item 1', response.content)
        self.assertIn('Test Menu Item 2', response.content)
        self.assertIn('/test_menu_link1', response.content)
        self.assertIn('/test_menu_link2', response.content)
        self.assertLess(response.content.index('Test Menu Item 1'),
                        response.content.index('Test Menu Item 2'))
        self.assertLess(response.content.index('/test_menu_link1'),
                        response.content.index('/test_menu_link2'))


class TestPersonalDataUser(TestCase):
    fixtures = ['test_contest', 'test_permissions']

    def testUser(self):
        self.client.login(username='test_personal_data_user')
        self.assertTrue(can_see_personal_data)


class TestUserInfo(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission']

    def test_user_info_page(self):
        contest = Contest.objects.get()
        user = User.objects.get(pk=1001)
        url = reverse('user_info', kwargs={'contest_id': contest.id,
                                           'user_id': user.id})

        self.client.login(username='test_user')
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(url, follow=True)
            self.assertIn('403', response.content)

        self.client.login(username='test_admin')
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(url, follow=True)
            self.assertIn('title>Test User - User info', response.content)
            self.assertIn("User's submissions", response.content)
            self.assertNotIn("<h4>User's round time extensions:</h4>",
                             response.content)

        round = Round.objects.get()
        ext = RoundTimeExtension(user=user, round=round, extra_time=20)
        ext.save()

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertIn("<h4>User's round time extensions:</h4>",
                      response.content)
        self.assertIn("Extra time: 20", response.content)


class TestProblemInstanceView(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_permissions',
                'test_problem_site']

    def test_admin_change_view(self):
        self.client.login(username='test_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest

        problem_instance = Problem.objects.all()[0]
        url = reverse('oioioiadmin:contests_probleminstance_change',
                args=(problem_instance.id,))
        response = self.client.get(url)
        elements_to_find = ['0', '1a', '1b', '1ocen', '2', 'Example', 'Normal']
        for element in elements_to_find:
            self.assertIn(element, response.content)

    @nottest
    def separate_main_problem_instance(self):
        # in fixtures there is only one ProblemInstance
        # unfortunately it's already attached to contest and it's
        # problem's main_problem_instance
        pi = ProblemInstance.objects.get()
        pi.id = None
        pi.pk = None
        pi.contest = None
        pi.round = None
        pi.save()

        problem = Problem.objects.get()
        problem.main_problem_instance = pi
        problem.save()

        old_instance = ProblemInstance.objects.get(contest__isnull=False)
        for t in old_instance.test_set.all():
            t.id = None
            t.pk = None
            t.problem_instance = pi
            t.save()

    def test_resetting_limits(self):
        self.separate_main_problem_instance()
        self.client.login(username='test_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest

        problem_instance = ProblemInstance.objects \
                           .filter(contest__isnull=False)[0]
        url = reverse('reset_tests_limits_for_probleminstance',
                args=(problem_instance.id,))
        for t in problem_instance.test_set.all():
            t.delete()

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, data={'submit': True},
                                    follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Tests limits resetted successfully", response.content)
        self.assertEqual(problem_instance.test_set.count(),
             problem_instance.problem.main_problem_instance.test_set.count())
        self.assertNotEqual(problem_instance.test_set.count(), 0)


class TestReattachingProblems(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_extra_contests',
            'test_full_package', 'test_problem_instance', 'test_permissions',
            'test_problem_site']

    def test_reattaching_problem(self):
        pi_id = ProblemInstance.objects.get().id
        self.client.login(username='test_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('reattach_problem_contest_list', args=(pi_id, 'full'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Choose contest to attach problem", response.content)
        self.assertEqual(response.content.count('<td><a'),
                         Contest.objects.count())

        url = reverse('reattach_problem_confirm', args=(pi_id, 'c2'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Extra test contest 2", response.content)
        self.assertContains(response, u'Sum\u017cyce')
        self.assertIn("Attach", response.content)

        response = self.client.post(url, data={'submit': True}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'c2')
        self.assertEqual(ProblemInstance.objects.count(), 2)
        self.assertIn(' added successfully.', response.content)
        self.assertContains(response, u'Sum\u017cyce')
        self.assertTrue(ProblemInstance.objects.filter(contest__id='c2')
                        .exists())

        for test in Problem.objects.get().main_problem_instance.test_set.all():
            test.delete()
        self.assertTrue(Test.objects.count() > 0)

    def test_permissions(self):
        pi_id = ProblemInstance.objects.get().id
        self.client.login(username='test_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest
        urls = [reverse('reattach_problem_contest_list', args=(pi_id,)),
                reverse('reattach_problem_confirm', args=(pi_id, 'c1'))]
        for url in urls:
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)

        self.client.login(username='test_user')
        self.client.get('/c/c/')  # 'c' becomes the current contest
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)


class TestModifyContest(TestCase):
    fixtures = ['test_users']

    # Verifies that contest's type remains intact when its data (start date,
    # end date, name etc.) changes.
    # For more info see SIO-1711 on Jira.
    def test_modify_contest(self):
        controller_name = \
                    'oioioi.programs.controllers.ProgrammingContestController'

        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {
                'name': 'Yet Another Contest',
                'id': 'yac',
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': controller_name
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('was added successfully', response.content)
        contest = Contest.objects.get()
        self.assertEqual(controller_name, contest.controller_name)
        ContestPermission(user=User.objects.get(pk=1001), contest=contest,
            permission='contests.contest_admin').save()

        self.client.login(username='test_user')
        url = reverse('oioioiadmin:contests_contest_change',
                args=(quote('yac'),)) + '?simple=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {
                'name': 'New Name',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-04',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'yac')
        self.assertEqual(controller_name, contest.controller_name)
