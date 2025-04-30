# pylint: disable=abstract-method
from __future__ import print_function

import bs4
import os
import re
from datetime import datetime, timedelta, timezone  # pylint: disable=E0611

import pytest
import pytz

from django.conf import settings
from django.contrib.admin.utils import quote
from django.contrib.auth.models import AnonymousUser, User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.http import HttpResponse
from django.template import RequestContext, Template
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import NoReverseMatch, reverse
from oioioi.base.permissions import is_superuser
from oioioi.base.tests import TestCase, TestsUtilsMixin, check_not_accessible, fake_time
from oioioi.base.tests.tests import TestPublicMessage
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.date_registration import date_registry
from oioioi.contests.models import (
    Contest,
    ContestAttachment,
    ContestLink,
    ContestPermission,
    ContestView,
    ProblemInstance,
    ProblemStatementConfig,
    RankingVisibilityConfig,
    RegistrationAvailabilityConfig,
    Round,
    RoundTimeExtension,
    Submission,
    UserResultForContest,
    UserResultForProblem,
    FilesMessage,
    SubmissionsMessage,
    SubmitMessage,
    SubmissionMessage,
)
from oioioi.contests.scores import IntegerScore, ScoreValue
from oioioi.contests.tests import make_empty_contest_formset
from oioioi.contests.utils import (
    administered_contests,
    all_non_trial_public_results_visible,
    all_public_results_visible,
    can_enter_contest,
    can_see_personal_data,
    is_contest_owner,
    is_contest_admin,
    is_contest_basicadmin,
    is_contest_observer,
    rounds_times,
)
from oioioi.dashboard.contest_dashboard import unregister_contest_dashboard_view
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.models import (
    Problem,
    ProblemAttachment,
    ProblemPackage,
    ProblemStatement,
)
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.programs.models import ModelProgramSubmission, Test, ProgramsConfig
from oioioi.programs.tests import SubmitFileMixin
from oioioi.participants.models import TermsAcceptedPhrase
from oioioi.simpleui.views import (
    contest_dashboard_redirect as simpleui_contest_dashboard,
)
from oioioi.teachers.views import (
    contest_dashboard_redirect as teachers_contest_dashboard,
)
from oioioi.testspackages.models import TestsPackage
from rest_framework.test import APITestCase


class TestModels(TestCase):
    def test_fields_autogeneration(self):
        contest = Contest()
        contest.save()
        self.assertEqual(contest.id, 'c1')
        self.assertEqual(contest.judging_priority, settings.DEFAULT_CONTEST_PRIORITY)
        self.assertEqual(contest.judging_weight, settings.DEFAULT_CONTEST_WEIGHT)
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
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_integer_score(self):
        s1 = IntegerScore(1)
        s2 = IntegerScore(2)
        self.assertLess(s1, s2)
        self.assertGreater(s2, s1)
        self.assertEqual(s1, IntegerScore(1))
        self.assertEqual((s1 + s2).value, 3)
        self.assertEqual(str(s1), '1')
        self.assertEqual(IntegerScore._from_repr(s1._to_repr()), s1)

    def test_score_field(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_admin')

        instance = UserResultForContest(
            user=user, contest=contest, score=IntegerScore(42)
        )
        instance.save()
        del instance

        instance = UserResultForContest.objects.get(user=user)
        self.assertTrue(isinstance(instance.score, IntegerScore))
        self.assertEqual(instance.score.value, 42)

        instance.score = IntegerScore(12)
        instance.save()
        instance = UserResultForContest.objects.get(user=user)
        self.assertEqual(instance.score.value, 12)

        with self.assertRaises(ValidationError):
            instance.score = ScoreValue.deserialize('1')
        with self.assertRaises(ValidationError):
            instance.score = ScoreValue.deserialize('foo:1')

        instance.score = None
        instance.save()
        del instance

        instance = UserResultForContest.objects.get(user=user)
        self.assertIsNone(instance.score)

    def test_db_order(self):
        # Importing module-wide seems to break sinolpack tests.
        from oioioi.programs.models import TestReport

        scores = [tr.score for tr in TestReport.objects.order_by('score').all()]
        self.assertEqual(scores, sorted(scores))


def print_contest_id_view(request):
    id = request.contest.id if request.contest else None
    return HttpResponse(str(id))


def render_contest_id_view(request):
    t = Template('{{ contest.id }}')
    return HttpResponse(t.render(RequestContext(request)))


class TestSubmissionListOrder(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
        'test_submissions_CE',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.url = reverse(
            'oioioiadmin:contests_submission_changelist', kwargs={'contest_id': 'c'}
        )
        super().setUp()

    def test_default_order(self):
        response = self.client.get(self.url)

        self.check_id_order_in_response(response, [4, 3])
        self.check_id_order_in_response(response, [3, 2])
        self.check_id_order_in_response(response, [2, 1])

    def check_id_order_in_response(self, response, ids):
        self.check_order_in_response(
            response,
            ['/submission/%d/change' % x for x in ids],
            'Submission with id %d should be displayed before submission with id %d'
            % tuple(ids),
        )

    @pytest.mark.skip(reason="TODO: Repair the ordering platform-wide.")
    def test_score_order(self):

        # 7 is the number of score column.
        # Order by score ascending, null score should be below OK.
        response = self.client.get(self.url + "?o=-7")

        self.check_ce_order_in_response(
            response,
            True,
            'Submission with CE should be displayed at ' 'the bottom with this order.',
        )

        # Order by score descending, null score should be above OK.
        response = self.client.get(self.url + "?o=7")

        self.check_ce_order_in_response(
            response,
            False,
            'Submission with CE ' 'should be displayed first with this order',
        )

    def check_ce_order_in_response(self, response, is_descending, error_msg):
        if is_descending:
            order = ['OK', 'CE']
        else:
            order = ['CE', 'OK']

        self.check_order_in_response(response, order, error_msg)

    def check_order_in_response(self, response, order, error_msg):
        # Cut off part of the response that is above submission table because
        # it can provide irrelevant noise.
        content = response.content.decode('utf-8')
        table_content = content[content.index('results') :]
        (test_first, test_second) = order

        self.assertIn(
            test_first,
            table_content,
            'Fixtures should contain submission with %s' % test_first,
        )
        self.assertIn(
            test_second,
            table_content,
            'Fixtures should contain submission with %s' % test_second,
        )

        test_first_index = table_content.index(test_first)
        test_second_index = table_content.index(test_second)

        self.assertTrue(test_first_index < test_second_index, error_msg)



# TODO: expand this TestCase
@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestSubmissionListFilters(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
        'test_submissions_CE',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.url = reverse(
            'noncontest:oioioiadmin:contests_submission_changelist',
        )
        self.curl = reverse(
            'oioioiadmin:contests_submission_changelist',
            kwargs={'contest_id': 'c'},
        )
        super().setUp()

    def get_package(self, name):
        return os.path.join(os.path.dirname(__file__), '../../sinolpack/files', name)

    def test_all_filters(self):
        args = {
            'has_active_system_error': 'yes',
            'kind': 'NORMAL',
            'status__exact': 'INI_OK',
            'revealed': '1',
            'lang': 'Pascal',
        }
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '4 submissions')
        response = self.client.get(self.url, args)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0 submissions')
        args['round'] = 'Round 1'
        response = self.client.get(self.curl, args)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0 submissions')

    def test_search(self):
        self.url = reverse(
            'noncontest:oioioiadmin:contests_submission_changelist',
        )
        filename = self.get_package('test_simple_package_translations.zip')
        call_command('addproblem', filename)
        response = self.client.get(self.url)
        self.assertContains(response, '5 submissions')
        response = self.client.get(self.url, {'pi': 'Sumżyce'})
        self.assertContains(response, '4 submissions')
        response = self.client.get(self.url, {'pi': 'Sumżyce', 'q': 'Sumżyce'})
        self.assertContains(response, '4 submissions')
        response = self.client.get(self.url, {'pi': 'Sumżyce', 'q': 'Zadanie'})
        self.assertContains(response, '0 submissions')
        response = self.client.get(self.url, {'pi': 'Zadanie z tłumaczeniami'})
        self.assertContains(response, '1 submission')
        response = self.client.get(self.url, {'pi': 'Zadanie z tłumaczeniami', 'q': 'Zadanie'})
        self.assertContains(response, '1 submission')
        response = self.client.get(self.url, {'pi': 'Zadanie z tłumaczeniami', 'q': 'Sumżyce'})
        self.assertContains(response, '0 submissions')


@override_settings(
    CONTEST_MODE=ContestMode.neutral, ROOT_URLCONF='oioioi.contests.tests.test_urls'
)
class TestUrls(TestCase):
    fixtures = ['test_contest']

    def test_make_patterns(self):
        # The 'urlpatterns' variable in test_urls is created using
        # 'make_patterns'. We test if it contains patterns coming from
        # different sources by trying to reverse them.
        try:
            # local contest pattern
            reverse('render_contest_id', kwargs={'contest_id': 'c'})
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
        except NoReverseMatch as e:
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
        url = reverse(
            'oioioiadmin:contests_contest_add', kwargs={'contest_id': contest.id}
        )
        self.assertTrue(url.startswith(contest_prefix))

        # contest-only non-admin
        with self.assertRaises(NoReverseMatch):
            reverse('default_contest_view')
        url = reverse('default_contest_view', kwargs={'contest_id': contest.id})
        self.assertTrue(url.startswith(contest_prefix))

        # contest-only admin
        with self.assertRaises(NoReverseMatch):
            reverse('oioioiadmin:contests_probleminstance_changelist')
        url = reverse(
            'oioioiadmin:contests_probleminstance_changelist',
            kwargs={'contest_id': contest.id},
        )
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


@override_settings(ROOT_URLCONF='oioioi.contests.tests.test_urls')
class TestCurrentContest(TestCase):
    fixtures = ['test_users', 'test_two_empty_contests']

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
            self.assertEqual(response.content.decode('utf-8'), 'c1')

        response = self.client.get(url)
        # 'c1' - most recently visited contest
        self.assertRedirects(response, url_c1)

        response = self.client.get(url, follow=True)
        self.assertEqual(response.content.decode('utf-8'), 'c1')

        response = self.client.get(url_c2)
        self.assertEqual(response.content.decode('utf-8'), 'c2')

        Contest.objects.get(id='c2').delete()

        response = self.client.get(url_c2)
        self.assertEqual(response.status_code, 404)

        response = self.client.get(url)
        self.assertRedirects(response, url_c1)

        response = self.client.get(url, follow=True)
        self.assertEqual(response.content.decode('utf-8'), 'c1')

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_neutral_contest_mode(self):
        url = reverse('print_contest_id')
        response = self.client.get(url)
        self.assertEqual(response.content.decode('utf-8'), 'None')

        url = reverse('print_contest_id', kwargs={'contest_id': 'c1'})
        response = self.client.get(url)
        self.assertEqual(response.content.decode('utf-8'), 'c1')

        url = reverse('render_contest_id')
        response = self.client.get(url)
        self.assertEqual(response.content.decode('utf-8'), 'c1')

        url = reverse('print_contest_id', kwargs={'contest_id': 'c2'})
        response = self.client.get(url)
        self.assertEqual(response.content.decode('utf-8'), 'c2')

        url = reverse('noncontest_print_contest_id')
        response = self.client.get(url)
        self.assertEqual(response.content.decode('utf-8'), 'None')

    @override_settings(CONTEST_MODE=ContestMode.contest_if_possible)
    def test_contest_if_possible_contest_mode(self):
        self._test_redirecting_contest_mode()

        url = reverse('noncontest_print_contest_id')
        response = self.client.get(url)
        self.assertEqual(response.content.decode('utf-8'), 'None')

    @override_settings(CONTEST_MODE=ContestMode.contest_only)
    def test_contest_only_contest_mode(self):
        self._test_redirecting_contest_mode()

        url = reverse('noncontest_print_contest_id')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), 'None')

    @override_settings(CONTEST_MODE=ContestMode.contest_if_possible)
    def test_namespaced_redirect(self):
        url = reverse('namespace:print_contest_id')
        url_c2 = reverse('namespace:print_contest_id', kwargs={'contest_id': 'c2'})

        response = self.client.get(url)
        # 'c2' - most recently created contest
        self.assertRedirects(response, url_c2)


class TestContestController(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_rounds',
    ]

    def test_order_rounds_by_focus(self):
        contest = Contest.objects.get()
        r1 = Round.objects.get(pk=1)
        r2 = Round.objects.get(pk=2)
        r3 = Round.objects.get(pk=3)

        r1.start_date = datetime(2012, 1, 1, 8, 0, tzinfo=timezone.utc)
        r1.end_date = datetime(2012, 1, 1, 10, 0, tzinfo=timezone.utc)
        r1.save()

        r2.start_date = datetime(2012, 1, 1, 9, 59, tzinfo=timezone.utc)
        r2.end_date = datetime(2012, 1, 1, 11, 00, tzinfo=timezone.utc)
        r2.save()

        r3.start_date = datetime(2012, 1, 2, 8, 0, tzinfo=timezone.utc)
        r3.end_date = datetime(2012, 1, 2, 10, 0, tzinfo=timezone.utc)
        r3.save()

        rounds = [r1, r2, r3]

        class FakeRequest(object):
            def __init__(self, timestamp, contest):
                self.timestamp = timestamp
                self.user = AnonymousUser()
                self.contest = contest

        for date, expected_order in (
            (datetime(2011, 1, 1, tzinfo=timezone.utc), [r1, r2, r3]),
            (datetime(2012, 1, 1, 7, 0, tzinfo=timezone.utc), [r1, r2, r3]),
            (datetime(2012, 1, 1, 7, 55, tzinfo=timezone.utc), [r1, r2, r3]),
            (datetime(2012, 1, 1, 9, 40, tzinfo=timezone.utc), [r1, r2, r3]),
            (datetime(2012, 1, 1, 9, 55, tzinfo=timezone.utc), [r2, r1, r3]),
            (datetime(2012, 1, 1, 9, 59, 29, tzinfo=timezone.utc), [r2, r1, r3]),
            (datetime(2012, 1, 1, 9, 59, 31, tzinfo=timezone.utc), [r1, r2, r3]),
            (datetime(2012, 1, 1, 10, 0, 1, tzinfo=timezone.utc), [r2, r1, r3]),
            (datetime(2012, 1, 1, 11, 0, 1, tzinfo=timezone.utc), [r2, r1, r3]),
            (datetime(2012, 1, 1, 12, 0, 1, tzinfo=timezone.utc), [r2, r1, r3]),
            (datetime(2012, 1, 2, 2, 0, 1, tzinfo=timezone.utc), [r3, r2, r1]),
            (datetime(2012, 1, 2, 2, 7, 55, tzinfo=timezone.utc), [r3, r2, r1]),
            (datetime(2012, 1, 2, 2, 9, 0, tzinfo=timezone.utc), [r3, r2, r1]),
            (datetime(2012, 1, 2, 2, 11, 0, tzinfo=timezone.utc), [r3, r2, r1]),
        ):
            self.assertEqual(
                contest.controller.order_rounds_by_focus(
                    FakeRequest(date, contest), rounds
                ),
                expected_order,
            )


class TestContestViews(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_recent_contests_list(self):
        contest = Contest.objects.get()
        invisible_contest = Contest(
            id='invisible',
            name='Invisible Contest',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        invisible_contest.save()

        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/%s/dashboard/' % contest.id)
        self.client.get('/c/%s/dashboard/' % invisible_contest.id)
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertContains(response, 'Test contest')
        self.assertContains(response, 'Invisible Contest')
        self.client.logout()

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertContains(response, 'dropdown open')
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertNotContains(response, 'dropdown open')

        contests = [cv.contest for cv in ContestView.objects.all()]
        self.assertEqual(contests, [contest, invisible_contest])

        self.client.get('/c/%s/dashboard/' % invisible_contest.id)
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        contests = [cv.contest for cv in ContestView.objects.all()]
        self.assertEqual(contests, [invisible_contest, contest])

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_contest_visibility(self):
        invisible_contest = Contest(
            id='invisible',
            name='Invisible Contest',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        invisible_contest.save()
        response = self.client.get(reverse('select_contest'))
        self.assertIn(
            'contests/select_contest.html', [t.name for t in response.templates]
        )
        self.assertEqual(len(response.context['contests']), 1)
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 1)
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertContains(response, 'Invisible Contest')

        contest2 = Contest(
            id='c2',
            name='Contest2',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        contest2.save()
        contest2.creation_date = datetime(2002, 1, 1, tzinfo=timezone.utc)
        contest2.save()
        contest3 = Contest(
            id='c3',
            name='Contest3',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        contest3.save()
        contest3.creation_date = datetime(2004, 1, 1, tzinfo=timezone.utc)
        contest3.save()
        contest4 = Contest(
            id='c4',
            name='Contest4',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        contest4.save()
        contest4.creation_date = datetime(2003, 1, 1, tzinfo=timezone.utc)
        contest4.save()
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 5)
        self.assertEqual(
            list(response.context['contests']),
            list(Contest.objects.order_by('-creation_date').all()),
        )
        self.assertContains(response, 'Contest2', count=1)
        self.assertContains(response, 'Contest3', count=1)
        self.assertContains(response, 'Contest4', count=1)
        content = response.content.decode('utf-8')
        self.assertLess(content.index('Contest3'), content.index('Contest4'))
        self.assertLess(content.index('Contest4'), content.index('Contest2'))

        contest2.creation_date = datetime(2003, 6, 1, tzinfo=timezone.utc)
        contest2.save()
        response = self.client.get(reverse('select_contest'))
        content = response.content.decode('utf-8')
        self.assertLess(content.index('Contest3'), content.index('Contest2'))
        self.assertLess(content.index('Contest2'), content.index('Contest4'))

    def test_submission_view(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get(pk=1)
        self.assertTrue(self.client.login(username='test_user'))
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.get(reverse('submission', kwargs=kwargs))

        def count_templates(name):
            return len([t for t in response.templates if t.name == name])

        self.assertEqual(count_templates('programs/submission_header.html'), 1)
        self.assertEqual(count_templates('programs/report.html'), 2)

        td_pattern_with_class = r'<td[^>]*>\s*%s'

        content = response.content.decode('utf-8')

        # Submit another button
        submit_url = reverse(
            'submit',
            kwargs={
                'contest_id': contest.id,
                'problem_instance_id': submission.problem_instance.id,
            },
        )
        self.assertContains(response, submit_url)

        for t in ['0', '1ocen', '1a', '1b', '2', '3']:
            self.assertTrue(re.search(td_pattern_with_class % (t,), content))

        self.assertContains(response, '34 / 34', count=1)
        self.assertContains(response, '0 / 33', count=2)
        self.assertContains(response, '0 / 0', count=2)

        status_pattern = r'<td class="[^"]*submission--%s">\s*%s\s*</td>'
        header_match = re.findall(status_pattern % ('OK[0-9]+', "OK"), content)
        ok_match = re.findall(status_pattern % ('OK', 'OK'), content)
        re_match = re.findall(status_pattern % ('RE', 'Runtime error'), content)
        wa_match = re.findall(status_pattern % ('WA', 'Wrong answer'), content)

        self.assertEqual(len(header_match), 1)
        self.assertEqual(len(ok_match), 4)
        self.assertEqual(len(re_match), 1)
        self.assertEqual(len(wa_match), 1)
        self.assertContains(response, 'program exited with code 1')

    def test_submissions_permissions(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get(pk=1)
        check_not_accessible(
            self,
            'submission',
            kwargs={
                'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id,
            },
        )

        contest.controller_name = 'oioioi.contests.tests.PrivateContestController'
        contest.save()
        problem_instance = ProblemInstance.objects.get()
        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, 'problems_list', kwargs={'contest_id': contest.id})
        check_not_accessible(
            self,
            'problem_statement',
            kwargs={
                'contest_id': contest.id,
                'problem_instance': problem_instance.short_name,
            },
        )
        check_not_accessible(self, 'my_submissions', kwargs={'contest_id': contest.id})
        check_not_accessible(self, 'contest_files', kwargs={'contest_id': contest.id})


class TestMySubmissions(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission_list',
    ]

    def test_submission_messages(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_user'))
        kwargs = {'contest_id': contest.id}
        response = self.client.get(reverse('my_submissions', kwargs=kwargs))

        status_pattern = r'<td id=".*"\s*class="[^"]*submission--%s[^"]">\s*%s\s*</td>'
        ini_ok = re.findall(
            status_pattern % ('OK[0-9]+', 'Initial tests: OK'),
            response.content.decode('utf-8'),
        )
        ini_err = re.findall(
            status_pattern % ('INI_ERR', 'Initial tests: failed'),
            response.content.decode('utf-8'),
        )

        self.assertEqual(len(ini_ok), 1)
        self.assertEqual(len(ini_err), 1)


class TestManyRounds(TestsUtilsMixin, TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_rounds',
        'test_permissions',
    ]

    @staticmethod
    def remove_ws(response):
        return re.sub(r'\s*', '', response.content.decode('utf-8'))

    def test_problems_visibility(self):
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            for user in ['test_admin', 'test_contest_admin']:
                self.assertTrue(self.client.login(username=user))
                response = self.client.get(url)
                for task in ['zad1', 'zad2', 'zad3', 'zad4']:
                    self.assertContains(response, task)
                self.assertIn(
                    'contests/problems_list.html', [t.name for t in response.templates]
                )
                self.assertEqual(len(response.context['problem_instances']), 4)
                self.assertTrue(response.context['show_rounds'])

            for user in ['test_user', 'test_observer']:
                self.assertTrue(self.client.login(username=user))
                response = self.client.get(url)
                for task in ['zad1', 'zad3', 'zad4']:
                    self.assertContains(response, task)
                self.assertNotContains(response, 'zad2')
                self.assertEqual(len(response.context['problem_instances']), 3)

    def test_submissions_visibility(self):
        contest = Contest.objects.get()
        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            for task in ['zad1', 'zad3', 'zad4']:
                self.assertContains(response, task)
            self.assertNotContains(response, 'zad2')

            self.assertIn(
                'contests/my_submissions.html', [t.name for t in response.templates]
            )

            self.assertEqual(self.remove_ws(response).count('>34<'), 2)

        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(self.remove_ws(response).count('>34<'), 4)

        with fake_time(datetime(2012, 7, 31, 20, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertNotIn('>34<', self.remove_ws(response))
            self.assertNotContains(response, 'Score')

        with fake_time(datetime(2012, 7, 31, 21, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(self.remove_ws(response).count('>34<'), 1)

        with fake_time(datetime(2012, 7, 31, 22, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(self.remove_ws(response).count('>34<'), 2)

        round4 = Round.objects.get(pk=4)
        user = User.objects.get(username='test_user')
        ext = RoundTimeExtension(user=user, round=round4, extra_time=60)
        ext.save()

        with fake_time(datetime(2012, 7, 31, 22, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(self.remove_ws(response).count('>34<'), 1)

        round4.end_date = datetime(2012, 8, 10, 0, 0, tzinfo=timezone.utc)
        round4.results_date = datetime(2012, 8, 10, 0, 10, tzinfo=timezone.utc)
        round4.save()

        ext.extra_time = 0
        ext.save()

        with fake_time(datetime(2012, 8, 10, 0, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(self.remove_ws(response).count('>34<'), 1)

        ext.extra_time = 20
        ext.save()

        with fake_time(datetime(2012, 8, 10, 0, 15, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(self.remove_ws(response).count('>34<'), 1)

        with fake_time(datetime(2012, 8, 10, 0, 21, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(self.remove_ws(response).count('>34<'), 2)

    def test_mixin_past_rounds_hidden_during_prep_time(self):
        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.contests.tests.PastRoundsHiddenContestController'
        )
        contest.save()

        user = User.objects.get(username='test_user')

        r1 = Round.objects.get(pk=1)
        r1.end_date = datetime(2012, 7, 30, 21, 40, tzinfo=timezone.utc)
        r1.save()

        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2012, 7, 31, 21, 1, tzinfo=timezone.utc)):
            # r3, r4 are active
            self.assertTrue(self.client.login(username=user))
            response = self.client.get(url)
            for task in ['zad3', 'zad4']:
                self.assertContains(response, task)
            self.assertEqual(len(response.context['problem_instances']), 2)

        with fake_time(datetime(2015, 7, 31, 20, 1, tzinfo=timezone.utc)):
            # r1,r3,r4 are past, preparation time for r2
            self.assertTrue(self.client.login(username=user))
            response = self.client.get(url)
            self.assertEqual(len(response.context['problem_instances']), 0)

        with fake_time(datetime(2015, 7, 31, 20, 28, tzinfo=timezone.utc)):
            # r2 is active
            self.assertTrue(self.client.login(username=user))
            response = self.client.get(url)
            self.assertContains(response, 'zad2')
            self.assertEqual(len(response.context['problem_instances']), 1)

        r2 = Round.objects.get(pk=2)
        r2.start_date = datetime(2012, 7, 31, 21, 40, tzinfo=timezone.utc)
        r2.save()

        with fake_time(datetime(2012, 7, 31, 21, 29, tzinfo=timezone.utc)):
            # r1,r3,r4 are past, break = (21.27, 21.40) -- first half
            self.assertTrue(self.client.login(username=user))
            response = self.client.get(url)
            for task in ['zad1', 'zad3', 'zad4']:
                self.assertContains(response, task)
            self.assertEqual(len(response.context['problem_instances']), 3)

        with fake_time(datetime(2012, 7, 31, 21, 35, tzinfo=timezone.utc)):
            # r1,r3,r3 are past, break = (21.27, 21.40) -- second half
            self.assertTrue(self.client.login(username=user))
            response = self.client.get(url)
            self.assertEqual(len(response.context['problem_instances']), 0)

        with fake_time(datetime(2012, 7, 31, 21, 41, tzinfo=timezone.utc)):
            # r2 is active
            self.assertTrue(self.client.login(username=user))
            response = self.client.get(url)
            self.assertContains(response, 'zad2')
            self.assertEqual(len(response.context['problem_instances']), 1)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 1)

    def test_round_dates(self):
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2024, 1, 1, tzinfo=timezone.utc)):
            for user in ['test_admin', 'test_contest_admin', 'test_user', 'test_observer']:
                self.assertTrue(self.client.login(username=user))
                response = self.client.get(url)
                self.assertContains(response, "(31 July 2011, 20:27 - )")
                self.assertContains(response, "(31 July 2012, 20:27 - 21:27)")
                self.assertContains(response, "(30 July 2012, 20:27 - 31 July 2012, 21:27)")

    def test_polish_round_dates(self):
        self.client.cookies['lang'] = 'pl'
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2024, 1, 1, tzinfo=timezone.utc)):
            for user in ['test_admin', 'test_contest_admin', 'test_user', 'test_observer']:
                self.assertTrue(self.client.login(username=user))
                response = self.client.get(url)
                self.assertContains(response, "(31 lipca 2011, 20:27 - )")
                self.assertContains(response, "(31 lipca 2012, 20:27 - 21:27)")
                self.assertContains(response, "(30 lipca 2012, 20:27 - 31 lipca 2012, 21:27)")
        self.client.cookies['lang'] = 'en'

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_round_dates_with_other_timezone(self):
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})
        with fake_time(datetime(2024, 1, 1, tzinfo=timezone.utc)):
            for user in ['test_admin', 'test_contest_admin', 'test_user', 'test_observer']:
                self.assertTrue(self.client.login(username=user))
                response = self.client.get(url)
                self.assertContains(response, "(31 July 2011, 22:27 - )")
                self.assertContains(response, "(31 July 2012, 22:27 - 23:27)")
                self.assertContains(response, "(30 July 2012, 22:27 - 31 July 2012, 23:27)")

    def test_rules_visibility(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.ProgrammingContestController'
        contest.save()
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('contest_rules', kwargs={'contest_id': 'c'})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The contest has 4 rounds.")


class TestMultilingualStatements(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_extra_statements',
    ]

    def test_multilingual_statements(self):
        pi = ProblemInstance.objects.get()
        url = reverse(
            'problem_statement',
            kwargs={'contest_id': pi.contest.id, 'problem_instance': pi.short_name},
        )
        response = self.client.get(url)
        self.assertStreamingEqual(response, b'en-txt')
        self.client.cookies['lang'] = 'en'
        response = self.client.get(url)
        self.assertStreamingEqual(response, b'en-txt')
        self.client.cookies['lang'] = 'pl'
        response = self.client.get(url)
        self.assertStreamingEqual(response, b'pl-pdf')
        ProblemStatement.objects.filter(language='pl').delete()
        response = self.client.get(url)
        self.assertTrue(response.streaming)
        content = self.streamingContent(response)
        self.assertIn(b'%PDF', content)
        ProblemStatement.objects.get(language__isnull=True).delete()
        response = self.client.get(url)
        self.assertStreamingEqual(response, b'en-txt')


class ContestWithoutStatementsController(ProgrammingContestController):
    def default_can_see_statement(self, request_or_context, problem_instance):
        return False


# Check all variables propagated to 'my_submissions.html'
class TestMySubmissionsContext(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_config(self):
        self.assertTrue(self.client.login(username='test_user2'))
        contest = Contest.objects.get()
        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertIn('submissions', response.context)
        self.assertIn('header', response.context)

        for s in response.context['submissions']:
            self.assertIn('display_type', s)
            self.assertIn('message', s)
            self.assertIn('submission', s)
            self.assertIn('can_see_status', s)
            self.assertIn('can_see_score', s)
            self.assertIn('can_see_comment')


class TestSubmitButtonInProblemsList(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_with_authorized_user(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(
            reverse('problems_list', kwargs={'contest_id': contest.id})
        )
        self.assertContains(
            response,
            reverse('submit', kwargs={'problem_instance_id': pi.id}),
            status_code=200,
        )

    def test_with_unauthorized_user(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        response = self.client.get(
            reverse('problems_list', kwargs={'contest_id': contest.id})
        )

        self.assertNotContains(
            response,
            reverse('submit', kwargs={'problem_instance_id': pi.id}),
            status_code=200,
        )

    def test_with_no_submissions_left(self):
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        pi.submissions_limit = 1
        pi.save()

        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(
            reverse('problems_list', kwargs={'contest_id': contest.id})
        )
        self.assertContains(
            response,
            reverse('submit', kwargs={'problem_instance_id': pi.id}),
            status_code=200,
        )

    def test_with_ended_round(self):
        round = Round.objects.get()
        round.end_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        round.save()

        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()

        with fake_time(datetime(2020, 1, 2, tzinfo=timezone.utc)):
            self.assertTrue(self.client.login(username='test_user'))
            response = self.client.get(
                reverse('problems_list', kwargs={'contest_id': contest.id})
            )
            self.assertNotContains(
                response,
                reverse('submit', kwargs={'problem_instance_id': pi.id}),
                status_code=200,
            )


class TestStatementsVisibility(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_controller(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(
            reverse('problems_list', kwargs={'contest_id': contest.id})
        )
        self.assertContains(response, 'zad1')
        self.assertContains(response, u'Sum\u017cyce')

        pi = ProblemInstance.objects.get()
        url = reverse(
            'problem_statement',
            kwargs={'contest_id': contest.id, 'problem_instance': pi.short_name},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        contest.controller_name = (
            'oioioi.contests.tests.tests.ContestWithoutStatementsController'
        )
        contest.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_statements_config(self):
        contest = Contest.objects.get()
        psc = ProblemStatementConfig(contest=contest)
        psc.save()

        self.assertEqual(psc.visible, 'AUTO')

        pi = ProblemInstance.objects.get()
        url = reverse(
            'problem_statement',
            kwargs={'contest_id': contest.id, 'problem_instance': pi.short_name},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        psc.visible = 'NO'
        psc.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        contest.controller_name = (
            'oioioi.contests.tests.tests.ContestWithoutStatementsController'
        )
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
        super(BrokenContestController, self).fill_evaluation_environ(
            environ, submission
        )
        environ.setdefault('recipe', []).append(
            ('failing_handler', 'oioioi.contests.tests.tests.failing_handler')
        )


class TestRejudgeAndFailure(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_rejudge_request(self):
        contest = Contest.objects.get()
        kwargs = {'contest_id': contest.id, 'submission_id': 1}
        rejudge_url = reverse('rejudge_submission', kwargs=kwargs)
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(rejudge_url)
        self.assertContains(response, 'OIOIOI', status_code=405)
        self.assertContains(response, 'method is not allowed', status_code=405)
        self.assertContains(response, 'Log out', status_code=405)

    def test_rejudge_and_failure(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.contests.tests.tests.BrokenContestController'
        contest.save()

        submission = Submission.objects.get(pk=1)
        self.assertTrue(self.client.login(username='test_admin'))
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.post(reverse('rejudge_submission', kwargs=kwargs))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertContains(response, 'failure report')
        self.assertContains(response, 'EXPECTED FAILURE')

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('System Error evaluating submission #', mail.outbox[0].subject)
        self.assertIn('Traceback (most recent call last)', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['admin@example.com'])

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertNotContains(response, 'failure report')
        self.assertNotContains(response, 'EXPECTED FAILURE')

    def test_suspicious_rejudge_request(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.contests.tests.tests.BrokenContestController'
        contest.save()

        submission = Submission.objects.get(pk=1)
        self.assertTrue(self.client.login(username='test_admin'))
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        url = reverse('rejudge_submission', kwargs=kwargs) + '?evil=true'

        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)


class TestRejudgeTypesView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_problem',
        'test_another_submission',
    ]

    def test_view(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        post_data = {'action': 'rejudge_action', '_selected_action': ['1', '2']}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'), post_data
        )
        self.assertContains(
            response, 'You have selected 2 submission(s) from 1 problem(s)'
        )
        self.assertContains(response, 'Rejudge submissions on judged tests only')
        self.assertContains(response, 'Tests:')

        problem_instance = ProblemInstance.objects.get(id=2)
        submission = Submission()
        submission.problem_instance = problem_instance
        submission.save()

        post_data['_selected_action'] = ['1', '2', '3']
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'), post_data
        )
        self.assertContains(
            response, 'You have selected 3 submission(s) from 2 problem(s)'
        )
        self.assertNotContains(response, 'Rejudge submissions on judged tests only')
        self.assertNotContains(response, 'Tests:')


class TestContestAdmin(TestCase):
    fixtures = ['test_users']

    def test_simple_contest_create_and_change(self):
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start date")
        self.assertNotContains(response, "Judging priority")
        self.assertNotContains(response, "Judging weight")

        post_data = make_empty_contest_formset()
        post_data.update(
            {
                'name': 'cname',
                'id': 'cid',
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': 'oioioi.programs.controllers.ProgrammingContestController',
                'is_archived': 'False',
            }
        )

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'cid')
        self.assertEqual(contest.name, 'cname')
        self.assertEqual(contest.judging_priority, settings.DEFAULT_CONTEST_PRIORITY)
        self.assertEqual(contest.judging_weight, settings.DEFAULT_CONTEST_WEIGHT)
        self.assertEqual(contest.round_set.count(), 1)
        round = contest.round_set.get()
        self.assertEqual(
            round.start_date,
            datetime(2012, 2, 3, 4, 5, 6, tzinfo=pytz.timezone(settings.TIME_ZONE)),
        )
        self.assertEqual(
            round.end_date,
            datetime(2012, 2, 4, 5, 6, 7, tzinfo=pytz.timezone(settings.TIME_ZONE)),
        )
        self.assertEqual(
            round.results_date,
            datetime(2012, 2, 5, 6, 7, 8, tzinfo=pytz.timezone(settings.TIME_ZONE)),
        )

        url = (
            reverse('oioioiadmin:contests_contest_change', args=(quote('cid'),))
            + '?simple=true'
        )
        response = self.client.get(url, follow=True)

        self.assertContains(response, '2012-02-05')
        self.assertContains(response, '06:07:08')
        self.assertContains(response, contest.controller.description)
        self.assertNotContains(response, "Judging priority")
        self.assertNotContains(response, "Judging weight")

        # pylint: disable=W0511
        # TODO: Fix me
        # After django update this throws form errors
        # pylint: disable=pointless-string-statement
        '''
        url = reverse('oioioiadmin:contests_contest_change',
                      args=(quote('cid'),))
        post_data = make_empty_contest_formset()
        post_data.update({
                'name': 'cname1',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-04',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
        })
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'cid')
        self.assertEqual(contest.name, 'cname1')
        self.assertEqual(contest.round_set.count(), 1)
        round = contest.round_set.get()
        self.assertEqual(round.start_date,
                datetime(2013, 2, 3, 14, 5, 6, tzinfo=pytz.timezone(settings.TIME_ZONE)))
        self.assertEqual(round.end_date,
                datetime(2013, 2, 4, 15, 6, 7, tzinfo=pytz.timezone(settings.TIME_ZONE)))
        self.assertEqual(round.results_date,
                datetime(2013, 2, 5, 16, 7, 8, tzinfo=pytz.timezone(settings.TIME_ZONE)))

        url = reverse('oioioiadmin:contests_contest_change',
                args=(quote('cid'),)) + '?simple=true'

        post_data = make_empty_contest_formset()
        post_data.update({
                'name': 'cname1',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-01',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
        })
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start date should be before end date.")
        '''
        # pylint: enable=pointless-string-statement

    def test_programs_config_creation(self):
        self.assertTrue(self.client.login(username='test_admin'))

        # Test programs config after adding contest
        url = reverse('oioioiadmin:contests_contest_add')

        contest_id = 'cid'
        post_data = make_empty_contest_formset()

        post_data.update(
            {
                'name': 'cname',
                'id': contest_id,
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': 'oioioi.programs.controllers.ProgrammingContestController',
                'is_archived': 'False',
                'judging_priority': '10',
                'judging_weight': '1',
                'programs_config-0-execution_mode': 'sio2jail',
                '_save': 'Save'
            }
        )

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()
        self.assertEqual(ProgramsConfig.objects.count(), 1)
        programs_config = ProgramsConfig.objects.get()
        self.assertEqual(programs_config.contest, contest)
        self.assertEqual(programs_config.execution_mode, 'sio2jail')

        # Test programs config after changing contest
        url = reverse('oioioiadmin:contests_contest_change', 
                      kwargs={'contest_id': contest_id, 'object_id': contest_id})

        post_data.update(
            {
                'name': 'cname2',
                'programs_config-0-id': programs_config.id,
                'programs_config-0-contest': contest_id,
                'programs_config-0-execution_mode': 'cpu',
            }
        )

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        contest = Contest.objects.get()
        self.assertEqual(contest.name, 'cname2')
        self.assertEqual(Contest.objects.count(), 1)
        self.assertEqual(ProgramsConfig.objects.count(), 1)
        programs_config = ProgramsConfig.objects.get()
        self.assertEqual(programs_config.contest, contest)
        self.assertEqual(programs_config.execution_mode, 'cpu')

    def test_terms_accepted_phrase_creation(self):
        self.assertTrue(self.client.login(username='test_admin'))

        # Test phrase after adding contest
        url = reverse('oioioiadmin:contests_contest_add')
        contest_id = 'cid'
        post_data = make_empty_contest_formset()
        post_data.update(
            {
                'name': 'cname',
                'id': contest_id,
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': 'oioioi.oi.controllers.OIContestController',
                'is_archived': 'False',
                'judging_priority': '10',
                'judging_weight': '1',
                '_save': 'Save'
            }
        )

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contest.objects.count(), 1)

        url = reverse('oioioiadmin:contests_contest_change',
                      kwargs={'contest_id': contest_id, 'object_id': contest_id})
        post_data.update(
            {
                'terms_accepted_phrase-0-text': 'TEST PHRASE',
                'terms_accepted_phrase-TOTAL_FORMS': '1',
                'terms_accepted_phrase-INITIAL_FORMS': '0',
                'terms_accepted_phrase-MIN_NUM_FORMS': '0',
                'terms_accepted_phrase-MAX_NUM_FORMS': '1',
                'terms_accepted_phrase-0-id': '',
                'terms_accepted_phrase-0-contest': contest_id
            }
        )

        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contest.objects.count(), 1)
        contest = Contest.objects.get()

        self.assertEqual(TermsAcceptedPhrase.objects.count(), 1)
        terms_accepted_phrase = TermsAcceptedPhrase.objects.get()
        self.assertEqual(terms_accepted_phrase.contest, contest)
        self.assertEqual(terms_accepted_phrase.text, 'TEST PHRASE')


    def test_admin_permissions(self):
        url = reverse('oioioiadmin:contests_contest_changelist')

        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, url)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # without set request.contest
        with self.assertRaises(NoReverseMatch):
            reverse('oioioiadmin:contests_probleminstance_changelist')

        c_id = 'test_contest'
        c = Contest.objects.create(
            id=c_id,
            controller_name='oioioi.programs.controllers.'
            'ProgrammingContestController',
            name='Test contest',
        )
        contest_prefix = '/c/{}/'.format(c_id)

        url = reverse(
            'oioioiadmin:contests_probleminstance_changelist',
            kwargs={'contest_id': c_id},
        )
        self.assertTrue(url.startswith(contest_prefix))
        url = url[len(contest_prefix) - 1 :]

        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, url)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # with request.contest
        self.client.get(contest_prefix)
        url = reverse('oioioiadmin:contests_probleminstance_changelist')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_user'))
        check_not_accessible(self, url)

        user = User.objects.get(username='test_user')
        ContestPermission(
            user=user, contest=c, permission='contests.contest_admin'
        ).save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestAttachments(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_attachments(self):
        # Possible attachments:
        #  - ContestAttachent without round: pub_date == None or not
        #  - ProblemAttachment (has round and no pub_date)
        #  - ContestAttachent with round: pub_date == None or before or after

        # The round starts at 2011.07.31-20:57:58
        def get_time(hour):
            return datetime(2011, 7, 31, hour, 0, 0, tzinfo=timezone.utc)

        # The attachemnts are in (attachment, content, name) tuples.
        contest = Contest.objects.get()
        ca = (
            ContestAttachment.objects.create(
                contest=contest,
                description='contest-attachment-simple',
                content=ContentFile(b'content-of-conatt-simple', name='conatt.txt'),
            ),
            b'content-of-conatt-simple',
            'conatt.txt',
        )
        cb = (
            ContestAttachment.objects.create(
                contest=contest,
                description='contest-attachment-pub-date',
                content=ContentFile(b'content-of-conatt-pub', name='conatt-pub.txt'),
                pub_date=get_time(19),
            ),
            b'content-of-conatt-pub',
            'conatt-pub.txt',
        )
        problem = Problem.objects.get()
        pa = (
            ProblemAttachment.objects.create(
                problem=problem,
                description='problem-attachment',
                content=ContentFile(b'content-of-probatt', name='probatt.txt'),
            ),
            b'content-of-probatt',
            'probatt.txt',
        )
        round = Round.objects.get(pk=1)
        ra = (
            ContestAttachment.objects.create(
                contest=contest,
                description='round-attachment',
                content=ContentFile(b'content-of-roundatt-simple', name='roundatt.txt'),
                round=round,
            ),
            b'content-of-roundatt-simple',
            'roundatt.txt',
        )
        ra[0].save()
        rb = (
            ContestAttachment.objects.create(
                contest=contest,
                description='round-attachment-pub-date-before',
                content=ContentFile(b'content-of-roundatt-before', name='roundatt-before.txt'),
                round=round,
                pub_date=get_time(19),
            ),
            b'content-of-roundatt-before',
            'roundatt-before.txt',
        )
        rc = (
            ContestAttachment.objects.create(
                contest=contest,
                description='round-attachment-pub-date-after',
                content=ContentFile(b'content-of-roundatt-after', name='roundatt-after.txt'),
                round=round,
                pub_date=get_time(22),
            ),
            b'content-of-roundatt-after',
            'roundatt-after.txt',
        )

        def get_attachment_urlpattern_name(att):
            if type(att) is ContestAttachment:
                return 'contest_attachment'
            assert type(att) is ProblemAttachment
            return 'problem_attachment'

        def check(visible, invisible):
            list_url = reverse('contest_files', kwargs={'contest_id': contest.id})
            self.assertTrue(self.client.login(username='test_user'))

            # File list
            response = self.client.get(list_url)
            self.assertEqual(response.status_code, 200)
            for (att, content, name) in visible:
                self.assertContains(response, name)
                self.assertContains(response, att.description)
            for (att, content, name) in invisible:
                self.assertNotContains(response, name)
                self.assertNotContains(response, att.description)
            for f in response.context['files']:
                self.assertEqual(f['admin_only'], False)

            # Actual accessibility
            for (att, content, name) in visible:
                response = self.client.get(
                    reverse(
                        get_attachment_urlpattern_name(att),
                        kwargs={'contest_id': contest.id, 'attachment_id': att.id},
                    )
                )
                self.assertStreamingEqual(response, content)
            for (att, content, name) in invisible:
                check_not_accessible(
                    self,
                    get_attachment_urlpattern_name(att),
                    kwargs={'contest_id': contest.id, 'attachment_id': att.id},
                )

            # File list again, but as an admin
            self.assertTrue(self.client.login(username='test_admin'))
            response = self.client.get(list_url)
            self.assertEqual(response.status_code, 200)
            for (att, content, name) in visible + invisible:
                self.assertContains(response, name)
                self.assertContains(response, att.description)
            invisible_names = set([f[2] for f in invisible])
            for f in response.context['files']:
                self.assertEqual(f['admin_only'], f['name'] in invisible_names)

            # Actual accessibility as an admin
            for (att, content, name) in visible + invisible:
                response = self.client.get(
                    reverse(
                        get_attachment_urlpattern_name(att),
                        kwargs={'contest_id': contest.id, 'attachment_id': att.id},
                    )
                )
                self.assertStreamingEqual(response, content)

        # Now, therefore far later than all of the dates
        check([ca, cb, pa, ra, rb, rc], [])
        # Before all dates
        with fake_time(get_time(18)):
            check([ca,], [cb, pa, ra, rb, rc])
        # Before the round start, but after the pub_dates before it
        with fake_time(get_time(20)):
            check([ca, cb], [pa, ra, rb, rc])
        # After the round start, but before the last pub_date
        with fake_time(get_time(21)):
            check([ca, cb, pa, ra, rb], [rc])
        # After the last pub_date
        with fake_time(get_time(23)):
            check([ca, cb, pa, ra, rb, rc], [])

    def test_attachments_order(self):
        contest = Contest.objects.get()
        problem = Problem.objects.get()
        list_url = reverse('contest_files', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_admin'))

        # Models have names that would make them sorted in a wrong order with old sorting.
        TestsPackage.objects.create(
            problem=problem,
            name='A-2-test-package',
        )
        TestsPackage.objects.create(
            problem=problem,
            name='A-1-test-package',
        )
        ProblemAttachment.objects.create(
            problem=problem,
            description='problem-attachment',
            content=ContentFile(b'content-of-pa', name='B-2-pa.txt'),
        )
        ProblemAttachment.objects.create(
            problem=problem,
            description='problem-attachment',
            content=ContentFile(b'content-of-pa', name='B-1-pa.txt'),
        )
        ContestAttachment.objects.create(
            contest=contest,
            description='contest-attachment',
            content=ContentFile(b'content-of-ca', name='C-2-ca.txt'),
        )
        ContestAttachment.objects.create(
            contest=contest,
            description='contest-attachment',
            content=ContentFile(b'content-of-ca', name='C-1-ca.txt'),
        )

        response = self.client.get(list_url)
        last = 0
        for name in ['C-1-ca.txt', 'C-2-ca.txt', 'B-1-pa.txt', 'B-2-pa.txt', 'A-1-test-package', 'A-2-test-package']:
            self.assertContains(response, name)
            pos = response.content.find(name.encode())
            self.assertTrue(pos > last)
            last = pos


class TestRoundExtension(TestCase, SubmitFileMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_extra_rounds',
    ]

    def test_round_extension(self):
        contest = Contest.objects.get()
        round1 = Round.objects.get(pk=1)
        round2 = Round.objects.get(pk=2)
        problem_instance1 = ProblemInstance.objects.get(pk=1)
        problem_instance2 = ProblemInstance.objects.get(pk=2)
        self.assertTrue(problem_instance1.round == round1)
        self.assertTrue(problem_instance2.round == round2)
        round1.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round1.end_date = datetime(2012, 8, 5, tzinfo=timezone.utc)
        round1.save()
        round2.start_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round2.end_date = datetime(2012, 8, 12, tzinfo=timezone.utc)
        round2.save()

        user = User.objects.get(username='test_user')
        ext = RoundTimeExtension(user=user, round=round1, extra_time=10)
        ext.save()

        with fake_time(datetime(2012, 8, 5, 0, 5, tzinfo=timezone.utc)):
            self.assertTrue(self.client.login(username='test_user2'))
            response = self.submit_file(contest, problem_instance1)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, 'Sorry, there are no problems')
            self.assertTrue(self.client.login(username='test_user'))
            response = self.submit_file(contest, problem_instance1)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 5, 0, 11, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance1)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, 'Sorry, there are no problems')

        with fake_time(datetime(2012, 8, 12, 0, 5, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance2)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, 'Sorry, there are no problems')

    def test_round_extension_admin(self):
        self.assertTrue(self.client.login(username='test_admin'))

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_roundtimeextension_add')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {'user': '1001', 'round': '1', 'extra_time': '31415926'}
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'was added successfully')
        self.assertEqual(RoundTimeExtension.objects.count(), 1)
        rext = RoundTimeExtension.objects.get()
        self.assertEqual(rext.round, Round.objects.get(pk=1))
        self.assertEqual(rext.user, User.objects.get(pk=1001))
        self.assertEqual(rext.extra_time, 31415926)

        url = reverse('oioioiadmin:contests_roundtimeextension_change', args=('1',))
        response = self.client.get(url)
        self.assertContains(response, '31415926')
        post_data = {'user': '1001', 'round': '1', 'extra_time': '27182818'}
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RoundTimeExtension.objects.count(), 1)
        rext = RoundTimeExtension.objects.get()
        self.assertEqual(rext.extra_time, 27182818)


class TestPermissions(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_extra_contests',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_permissions',
    ]

    def factory(self, user, timestamp=None):
        factory = RequestFactory()
        request = factory.request()
        request.contest = self.contest
        request.user = user
        request.timestamp = timestamp or self.during 
        return request

    def setUp(self):
        self.contest = Contest.objects.get(id='c')
        self.contest.controller_name = 'oioioi.contests.tests.PrivateContestController'
        self.contest.save()
        self.ccontr = self.contest.controller
        self.round = Round.objects.get(contest=self.contest)
        self.round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        self.round.end_date = datetime(2012, 8, 5, tzinfo=timezone.utc)
        self.round.save()

        self.during = datetime(2012, 8, 1, tzinfo=timezone.utc)

        self.superuser = User.objects.get(username='test_admin')
        self.observer = User.objects.get(username='test_observer')
        self.cadmin = User.objects.get(username='test_contest_admin')
        self.pdata = User.objects.get(username='test_personal_data_user')
        self.badmin = User.objects.get(username='test_contest_basicadmin')
        self.cowner = User.objects.get(username='test_contest_owner')
        self.user = User.objects.get(username='test_user')

        self.perms_list = (
            'contests.personal_data',
            'contests.contest_observer',
            'contests.contest_basicadmin',
            'contests.contest_admin',
            'contests.contest_owner',
        )

        super().setUp()

    def test_utils(self):
        all_funlist = [
            is_superuser,
            is_contest_owner,
            is_contest_admin,
            is_contest_basicadmin,
            is_contest_observer,
            can_enter_contest,
            can_see_personal_data,
        ]

        def check_perms(user, perms):
            request = self.factory(user)
            for f in all_funlist:
                self.assertEqual(f(request), f in perms)

        check_perms(self.superuser, all_funlist)
        check_perms(self.cowner, [
            is_contest_owner,
            is_contest_admin,
            is_contest_basicadmin,
            can_enter_contest,
        ])
        check_perms(
            self.cadmin,
            [is_contest_admin, is_contest_basicadmin, can_enter_contest,],
        )
        check_perms(self.badmin, [is_contest_basicadmin, can_enter_contest])
        check_perms(self.observer, [is_contest_observer, can_enter_contest])
        check_perms(self.pdata, [can_see_personal_data, can_enter_contest])
        check_perms(self.user, [])

    def test_privilege_manipulation(self):
        def check_perms(user, perms):
            for p in self.perms_list:
                self.assertEqual(user.has_perm(p, self.contest), p in perms)

        check_perms(self.superuser, self.perms_list)
        check_perms(self.cowner, [
            'contests.contest_owner',
            'contests.contest_admin',
            'contests.contest_basicadmin',
        ])
        check_perms(
            self.cadmin,
            ['contests.contest_admin', 'contests.contest_basicadmin'],
        )
        check_perms(self.badmin, ['contests.contest_basicadmin'])
        check_perms(self.observer, ['contests.contest_observer'])
        check_perms(self.pdata, ['contests.personal_data'])
        check_perms(self.user, [])

        for perm in self.perms_list:
            del self.user._contest_perms_cache
            cperm = ContestPermission.objects.create(
                user=self.user, contest=self.contest, permission=perm
            )
            self.assertTrue(self.user.has_perm(perm, self.contest))
            cperm.delete()

    def try_post_perm(self, url, cid, perm, should_fail, user=None):
        user = user or self.user
        qs = ContestPermission.objects.filter(
            user=user,
            contest_id=cid,
            permission=perm,
        )
        self.assertEqual(qs.count(), 0)

        data = {
            'user': user.username,
            'contest': cid,
            'permission': perm,
        }

        resp = self.client.post(url, data, follow=True)
        if resp.status_code == 403:
            self.assertTrue(should_fail)
            return
        self.assertEqual(resp.status_code, 200)
        if should_fail:
            self.assertEqual(qs.count(), 0)
            return
        self.assertEqual(qs.count(), 1)
        qs.delete()

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_contestpermission_admin(self):
        list_url = reverse(
            'oioioiadmin:contests_contestpermission_changelist',
            kwargs={'contest_id': self.contest.id},
        )
        list_url_another_contest = reverse(
            'oioioiadmin:contests_contestpermission_changelist',
            kwargs={'contest_id': 'c1'},
        )
        list_url_nocontest = reverse(
            'noncontest:oioioiadmin:contests_contestpermission_changelist',
        )
        add_url = reverse(
            'oioioiadmin:contests_contestpermission_add',
            kwargs={'contest_id': self.contest.id},
        )
        add_url_nocontest = reverse(
            'noncontest:oioioiadmin:contests_contestpermission_add',
        )
        # Only superusers and contest owners should see these pages
        for u in (
            self.observer, self.cadmin, self.badmin, self.pdata, self.user,
        ):
            self.client.force_login(u)
            for url in (
                list_url, add_url, list_url_nocontest, add_url_nocontest,
            ):
                self.assertEqual(self.client.get(url).status_code, 403)

        perm_different_contest = ContestPermission(
            user=self.user,
            contest_id='c1',
            permission='contests.personal_data',
        )

        for u in (self.cowner, self.superuser):
            self.client.force_login(u)
            for url in (list_url, add_url):
                self.assertEqual(self.client.get(url).status_code, 200)
            resp = self.client.get(list_url)
            # All perms should be visible on the list. We check for the users'
            # names here.
            self.assertContains(resp, 'Test Contest owner')
            self.assertContains(resp, 'Test Contest admin')
            self.assertContains(resp, 'Test Contest basicadmin')
            self.assertNotContains(resp, 'Test User')

            perm_different_contest.save()
            # This shouldn't be visible, since it's in a different contest...
            self.assertNotContains(resp, 'Test User')
            # ... but a superuser with no selected contest should see it.
            if u == self.cowner:
                # This will have been redirected to the last contest
                resp = self.client.get(list_url_nocontest)
                self.assertEqual(resp.status_code, 403)
                resp = self.client.get(list_url_another_contest)
                self.assertEqual(resp.status_code, 403)
            else:
                resp = self.client.get(list_url_nocontest)
                self.assertEqual(resp.status_code, 200)
                self.assertContains(resp, 'Test Contest owner')
                self.assertContains(resp, 'Test Contest admin')
                self.assertContains(resp, 'Test Contest basicadmin')
                self.assertContains(resp, 'Test User')
            perm_different_contest.delete()

            # Creating new ContestPermission objects for self.user
            for perm in self.perms_list:
                # This should fail only for contest owners trying to add
                # another contest owner
                self.try_post_perm(
                    add_url,
                    self.contest.id,
                    perm,
                    u == self.cowner and perm == 'contests.contest_owner',
                )
                # Different contest should always fail...
                self.try_post_perm(
                    add_url,
                    'c1',
                    perm,
                    True,
                )
                # ... except for a superuser with no selected contest.
                self.try_post_perm(
                    add_url_nocontest,
                    'c1',
                    perm,
                    u == self.cowner,
                )

                # Editing objects, mostly same as above
                tmp_perm = ContestPermission.objects.create(
                    user=self.user,
                    contest=self.contest,
                    permission='nonexistent_permission',
                )

                cid = self.contest.id
                # Different contest should always fail...
                change_url = reverse(
                    'oioioiadmin:contests_contestpermission_change',
                    kwargs={'object_id': tmp_perm.id, 'contest_id': cid},
                )
                self.try_post_perm(
                    change_url,
                    'c1',
                    perm,
                    True,
                )

                # the url is still up to date
                self.try_post_perm(
                    change_url,
                    self.contest.id,
                    perm,
                    u == self.cowner and perm == 'contests.contest_owner',
                )

                # ... except for a superuser with no selected contest.
                tmp_perm.save()
                change_url = reverse(
                    'noncontest:oioioiadmin:contests_contestpermission_change',
                    kwargs={'object_id': tmp_perm.id,},
                )
                self.try_post_perm(
                    change_url,
                    'c1',
                    perm,
                    u == self.cowner,
                )
                tmp_perm.delete()

        # Deleting
        perm_different_contest.save()
        # 'post' is to bypass confirmation screen
        data_owner = {
            'post': 'yes',
            'action': 'delete_selected',
            '_selected_action': ContestPermission.objects.get(
                permission='contests.contest_owner').id,
        }
        data_admin = {
            'post': 'yes',
            'action': 'delete_selected',
            '_selected_action': ContestPermission.objects.get(
                permission='contests.contest_admin').id,
        }
        data_different_contest = {
            'post': 'yes',
            'action': 'delete_selected',
            '_selected_action': perm_different_contest.id,
        }

        self.client.force_login(self.cadmin)
        resp = self.client.post(list_url, data_owner)
        self.assertEqual(resp.status_code, 403)
        resp = self.client.post(list_url, data_admin)
        self.assertEqual(resp.status_code, 403)

        self.client.force_login(self.cowner)
        resp = self.client.post(list_url, data_owner)
        self.assertEqual(resp.status_code, 403)
        resp = self.client.post(list_url, data_different_contest, follow=True)
        # Verifying this is tricky
        self.assertEqual(resp.status_code, 200)
        redir_url = resp.redirect_chain[-1]
        resp = self.client.post(redir_url, data_different_contest, follow=True)
        self.assertEqual(resp.status_code, 404)
        resp = self.client.post(
            list_url_another_contest,
            data_different_contest,
            follow=True,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(ContestPermission.objects.filter(
            id=perm_different_contest.id).count(), 1)

        self.assertEqual(ContestPermission.objects.filter(
            permission='contests.contest_admin').count(), 1)
        resp = self.client.post(list_url, data_admin)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContestPermission.objects.filter(
            permission='contests.contest_admin').count(), 0)

        self.client.force_login(self.superuser)
        resp = self.client.post(list_url, data_different_contest, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ContestPermission.objects.filter(
            id=perm_different_contest.id).count(), 1)

        resp = self.client.post(
            list_url_another_contest,
            data_different_contest,
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContestPermission.objects.filter(
            id=perm_different_contest.id).count(), 0)

        resp = self.client.post(list_url, data_owner)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ContestPermission.objects.filter(
            permission='contests.contest_owner').count(), 0)

    def test_menu(self):
        unregister_contest_dashboard_view(simpleui_contest_dashboard)
        unregister_contest_dashboard_view(teachers_contest_dashboard)
        url = reverse(
            'default_contest_view',
            kwargs={'contest_id': self.contest.id}
        )

        self.client.force_login(self.cadmin)
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, 'System Administration')
        self.assertContains(response, 'Contest Administration')
        self.assertNotContains(response, 'Contest rights')
        self.assertNotContains(response, 'Observer Menu')

        self.client.force_login(self.observer)
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, 'Contest Administration')
        self.assertNotContains(response, 'Contest rights')
        self.assertContains(response, 'Observer Menu')

        self.client.force_login(self.superuser)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'System Administration')
        # The menus are duplicated in the html and this entry
        # should only appear once in the visible part.
        self.assertContains(response, 'Contest rights', count=2)
        self.assertContains(response, 'Contest Administration')

        self.client.force_login(self.cowner)
        response = self.client.get(url, follow=True)
        self.assertNotContains(response, 'System Administration')
        # Same as above
        self.assertContains(response, 'Contest rights', count=2)
        self.assertContains(response, 'Contest Administration')


class TestPermissionsBasicAdmin(TestCase):
    # The following tests make sure what the contests.contest_basicadmin
    # permission gives access to, which will be used for the user contests.
    #
    # WARNING: If you are here because one of these tests broke on your change,
    # double check that you have not altered the behaviour in an unsafe way -
    # for example allowing the basicadmins control over stuff outside the
    # contest, or leaking data from outside the contest. If you have made
    # additions to any of the affected admin pages the safest course of action
    # is to use the is_contest_admin check to deny basicadmins access to them.
    #
    # In essence, you should probably only change these tests if you are
    # absolutely sure of what you are doing.

    fixtures = [
        'test_users',
        'test_permissions',
        'test_contest',
        'test_full_package',
        'test_problem_packages',
        'test_problem_instance',
        'test_problem_site',
        'test_submission',
        'test_model_submissions',
        'test_messages',
    ]

    def setUp(self):
        self.contest = Contest.objects.get()
        self.contest.controller_name = (
            'oioioi.programs.controllers.ProgrammingContestController'
        )
        self.contest.save()

        unregister_contest_dashboard_view(simpleui_contest_dashboard)
        unregister_contest_dashboard_view(teachers_contest_dashboard)

        super().setUp()

    def test_dashboard(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        url = reverse('default_contest_view', kwargs={'contest_id': 'c'})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_menu(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')
        url = reverse('contest_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contest Administration")

        self.assertContains(response, "Settings")
        self.assertContains(response, "Problems")
        self.assertContains(response, "Submissions")
        self.assertContains(response, "Problem packages")

        html = response.content.decode('utf-8')
        pos = html.find('menu-accordion')
        self.assertNotEqual(pos, -1)
        pos = html.find('Contest Administration', pos)
        self.assertNotEqual(pos, -1)
        pos = html.find('list-group', pos)
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</div', pos)
        self.assertNotEqual(pos2, -1)

        self.assertEqual(html[pos:pos2].count('list-group-item'), 8)

    def test_menu_settings(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('oioioiadmin:contests_contest_change', args=('c',))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'round_set-group')
        self.assertContains(response, 'c_attachments-group')
        self.assertContains(response, 'contestlink_set-group')
        self.assertContains(response, 'messagenotifierconfig_set-group')
        self.assertContains(response, 'contesticon_set-group')
        self.assertContains(response, 'contestlogo-group')

        self.assertContains(response, 'js-inline-admin-formset', count=7)

    def test_menu_problems(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('oioioiadmin:contests_probleminstance_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'column-name_link')
        self.assertContains(response, 'column-short_name_link')
        self.assertContains(response, 'column-round')
        self.assertContains(response, 'column-actions_field')
        self.assertContains(response, 'column-suspended_on_init_display')
        self.assertContains(response, 'column-suspended_on_final_display')

        self.assertContains(response, 'column-', count=6)

        html = response.content.decode('utf-8')
        pos = html.find('field-actions_field')
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</td>', pos)
        self.assertNotEqual(pos2, -1)

        self.assertIn("Edit", html[pos:pos2])
        self.assertIn("Model solutions", html[pos:pos2])
        self.assertIn("Reset tests limits", html[pos:pos2])
        self.assertIn("Attach to another contest", html[pos:pos2])
        self.assertIn("Reupload package", html[pos:pos2])
        self.assertIn("Advanced settings", html[pos:pos2])
        self.assertIn("Suspend all tests", html[pos:pos2])
        self.assertIn("Suspend final tests", html[pos:pos2])
        self.assertIn("Edit package", html[pos:pos2])
        self.assertIn("Replace statement", html[pos:pos2])
        self.assertEqual(html[pos:pos2].count('|'), 9)

    def test_problem_admin(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')
        for problem in Problem.objects.all():
            url = reverse('oioioiadmin:problems_problem_change', args=(problem.id,))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        html = response.content.decode('utf-8')
        pos = html.find('problem_form')
        self.assertNotEqual(pos, -1)
        pos = html.find('<fieldset', pos)
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</fieldset>', pos)
        self.assertNotEqual(pos2, -1)

        self.assertNotContains(response, 'id_visibility')
        self.assertIn('field-visibility', html[pos:pos2])
        self.assertIn('field-author', html[pos:pos2])
        self.assertIn('field-legacy_name', html[pos:pos2])
        self.assertIn('field-short_name', html[pos:pos2])
        self.assertIn('field-controller_name', html[pos:pos2])
        self.assertIn('field-package_backend_name', html[pos:pos2])
        self.assertIn('field-main_problem_instance', html[pos:pos2])
        self.assertIn('field-ascii_name', html[pos:pos2])
        self.assertEqual(html[pos:pos2].count('field-'), 8)

        self.assertContains(response, 'statements-group')
        self.assertContains(response, 'attachments-group')
        self.assertContains(response, 'problemsite-group')
        self.assertNotContains(response, 'test_run_config-group')
        self.assertContains(response, 'libraryproblemdata-group')
        self.assertContains(response, 'js-inline-admin-formset', 7)

    def test_probleminstance_admin(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')
        for pi in ProblemInstance.objects.all():

            url = reverse(
                'oioioiadmin:contests_probleminstance_change',
                kwargs={'contest_id': 'c'},
                args=(pi.id,),
            )
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

            self.assertContains(response, 'scores_reveal_config-group')
            self.assertContains(response, 'test_run_config-group')

    def test_modelsolutions(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('model_solutions', args=(1,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')

        pos = html.find('table')
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</tr>', pos)
        self.assertNotEqual(pos2, -1)

        self.assertEqual(html[pos:pos2].count('<th>'), 4)

    def test_modelsubmission_source(self):
        submission_id = ModelProgramSubmission.objects.first().id
        url = reverse('show_submission_source', args=(submission_id,))

        self.assertTrue(self.client.login(username='test_contest_admin'))
        response = self.client.get(url)
        # Test for 302 redirect instead of downloading a nonexistent file
        self.assertEqual(response.status_code, 302)

        self.assertTrue(self.client.login(username='test_observer'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_menu_submissions(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('oioioiadmin:contests_submission_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        submission_id = ModelProgramSubmission.objects.first().id
        url = reverse('show_submission_source', args=(submission_id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        url = reverse('source_diff', args=(1, 13))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        url = reverse('show_submission_source', args=(1,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_menu_problempackages_basicadmin(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('oioioiadmin:problems_contestproblempackage_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'column-problem_name')
        self.assertContains(response, 'column-colored_status')
        self.assertContains(response, 'column-creation_date')
        self.assertContains(response, 'column-package_info')
        self.assertContains(response, 'column-inner')
        self.assertContains(response, 'column-', count=5)

        self.assertNotContains(response, 'uploader')

        package = ProblemPackage.objects.first()
        package.traceback = ContentFile(b'foo', name='bar')
        package.package_file = ContentFile(b'foo2', name='bar2')
        package.save()
        url = reverse('download_package_traceback', args=(package.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        url = reverse('download_package', args=(package.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_menu_problempackages_admin(self):
        self.assertTrue(self.client.login(username='test_contest_admin'))
        self.client.get('/c/c/')

        url = reverse('oioioiadmin:problems_contestproblempackage_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'column-problem_name')
        self.assertContains(response, 'column-created_by')
        self.assertContains(response, 'column-colored_status')
        self.assertContains(response, 'column-creation_date')
        self.assertContains(response, 'column-package_info')
        self.assertContains(response, 'column-inner')
        self.assertContains(response, 'column-', count=6)

        package = ProblemPackage.objects.first()
        package.traceback = ContentFile(b'foo', name='bar')
        package.package_file = ContentFile(b'foo2', name='bar2')
        package.save()
        url = reverse('download_package_traceback', args=(package.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        url = reverse('download_package', args=(package.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_usermenu(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('contest_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "User Menu")

        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Rules")
        self.assertContains(response, "Problems")
        self.assertContains(response, "Downloads")
        self.assertContains(response, "Submit")
        self.assertContains(response, "My submissions")
        self.assertContains(response, "Ranking")
        self.assertContains(response, "Questions and news")
        self.assertContains(response, "Forum")

        html = response.content.decode('utf-8')
        pos = html.find('menu-accordion')
        self.assertNotEqual(pos, -1)
        pos = html.find('User Menu', pos)
        self.assertNotEqual(pos, -1)
        pos = html.find('list-group', pos)
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</div', pos)
        self.assertNotEqual(pos2, -1)

        self.assertEqual(html[pos:pos2].count('list-group-item'), 18)

    def test_usermenu_files(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')
        url = reverse('contest_files')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add file')

    def test_usermenu_submit(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')
        url = reverse('submit')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id_user')
        self.assertContains(response, 'id_kind')

    def test_usermenu_ranking(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')
        url = reverse('default_ranking')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Export to CSV')
        self.assertContains(response, 'Regenerate ranking')

        url = reverse('ranking_csv', args=('c',))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        url = reverse('ranking_invalidate', args=('c',))
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_usermenu_questions_and_news(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')
        url = reverse('contest_messages')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All message types')
        self.assertContains(response, 'All categories')
        self.assertContains(response, 'Author username')

        self.assertContains(response, 'Subscribe')
        self.assertContains(response, 'Add news')
        self.assertContains(response, 'Edit reply templates')
        self.assertContains(response, 'Show all messages')
        self.assertNotContains(response, 'Ask a question')

        url = reverse('add_contest_message')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        url = reverse('oioioiadmin:questions_replytemplate_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        url = reverse('contest_all_messages')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        html = response.content.decode('utf-8')
        pos = html.find('oioioi-message__actions')
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</p>', pos)
        self.assertNotEqual(pos2, -1)

        self.assertEqual(html[pos:pos2].count('oioioi-message__action'), 4)

    def test_show_info_about(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('contest_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Show info about...")

        url = reverse('user_info', args=(1001,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestProblemsMenuWithQuizzes(TestCase):
    fixtures = [
        'test_users',
        'test_permissions',
        'test_contest',
        'test_quiz_problem',
        'test_problem_instance',
        'test_problem_site',
    ]

    def test_menu_problems(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self.client.get('/c/c/')

        url = reverse('oioioiadmin:contests_probleminstance_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'column-name_link')
        self.assertContains(response, 'column-short_name_link')
        self.assertContains(response, 'column-round')
        self.assertContains(response, 'column-actions_field')
        self.assertContains(response, 'column-suspended_on_init_display')
        self.assertContains(response, 'column-suspended_on_final_display')

        self.assertContains(response, 'column-', count=6)

        html = response.content.decode('utf-8')
        pos = html.find('field-actions_field')
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</td>', pos)
        self.assertNotEqual(pos2, -1)

        self.assertIn("Edit", html[pos:pos2])
        self.assertIn("Quiz questions", html[pos:pos2])
        self.assertIn("Attach to another contest", html[pos:pos2])
        self.assertIn("Advanced settings", html[pos:pos2])
        self.assertIn("Suspend all tests", html[pos:pos2])
        self.assertIn("Suspend final tests", html[pos:pos2])
        self.assertIn("Edit package", html[pos:pos2])
        self.assertIn("Replace statement", html[pos:pos2])
        self.assertEqual(html[pos:pos2].count('|'), 7)


class TestSubmissionChangeKind(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_multiple_submissions',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_admin'))
        super().setUp()

    def change_kind(self, submission, kind):
        contest = Contest.objects.get()
        url1 = reverse(
            'change_submission_kind',
            kwargs={
                'contest_id': contest.id,
                'submission_id': submission.id,
                'kind': kind,
            },
        )
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

        urp = UserResultForProblem.objects.get(
            user__username='test_user', problem_instance=pi
        )
        self.assertEqual(urp.score, 90)

        self.change_kind(s2, 'IGNORED')
        urp = UserResultForProblem.objects.get(
            user__username='test_user', problem_instance=pi
        )
        urc = UserResultForContest.objects.get(
            user__username='test_user', contest=contest
        )
        self.assertEqual(urp.score, 100)
        self.assertEqual(urc.score, 100)

        self.change_kind(s2, 'NORMAL')

        urp = UserResultForProblem.objects.get(
            user__username='test_user', problem_instance=pi
        )
        self.assertEqual(urp.score, 90)

        self.change_kind(s2, 'IGNORED_HIDDEN')
        urp = UserResultForProblem.objects.get(
            user__username='test_user', problem_instance=pi
        )
        urc = UserResultForContest.objects.get(
            user__username='test_user', contest=contest
        )
        self.assertEqual(urp.score, 100)
        self.assertEqual(urc.score, 100)


class TestDeleteSelectedSubmissions(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
        'test_permissions',
    ]

    def test_delete_one_submission(self):
        self.assertTrue(self.client.login(username='test_contest_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        post_data = {'action': 'delete_selected', '_selected_action': ['1']}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'), post_data
        )

        # Test confirmation dialog
        self.assertContains(
            response, 'Are you sure you want to delete the selected submission?'
        )
        self.assertContains(
            response,
            'All of the following objects and their related items ' 'will be deleted:',
        )
        self.assertContains(response, 'Submission(')
        self.assertContains(response, 'NORMAL, OK)')
        self.assertContains(response, 'Score report')
        self.assertContains(response, 'Compilation report')
        self.assertContains(response, 'Program submission: Submission(1, ')

        # Delete it and check if there is one submission remaining
        post_data = {
            'action': 'delete_selected',
            '_selected_action': ['1'],
            'post': 'yes',
        }
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data,
            follow=True,
        )

        self.assertContains(response, 'Successfully deleted 1 submission.')

    def test_delete_many_submissions(self):
        self.assertTrue(self.client.login(username='test_contest_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        post_data = {'action': 'delete_selected', '_selected_action': ['1', '2']}
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'), post_data
        )

        # Test confirmation dialog
        self.assertContains(
            response, 'Are you sure you want to delete the selected submissions?'
        )
        self.assertContains(
            response,
            'All of the following objects and their related items ' 'will be deleted:',
        )
        self.assertContains(response, 'Submission(')
        self.assertContains(response, 'NORMAL, OK)')
        self.assertContains(response, 'Score report')
        self.assertContains(response, 'Compilation report')
        self.assertContains(response, 'Program submission: Submission(1, ')

        # Delete them and check if there are no submissions remaining
        post_data = {
            'action': 'delete_selected',
            '_selected_action': ['1', '2'],
            'post': 'yes',
        }
        response = self.client.post(
            reverse('oioioiadmin:contests_submission_changelist'),
            post_data,
            follow=True,
        )

        self.assertContains(response, 'Successfully deleted 2 submissions.')


class TestSubmitSelectOneProblem(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_problems_list(self):
        self.assertTrue(self.client.login(username='test_user2'))
        contest = Contest.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertEqual(len(form.fields['problem_instance_id'].choices), 1)


class TestSubmitSelectManyProblems(TestCase):
    fixtures = [
        'test_users',
        'test_extra_problem',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_problems_list(self):
        self.assertTrue(self.client.login(username='test_user2'))
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
            contest.controller_name = (
                'oioioi.contests.tests.tests.ContestWithPublicResultsController'
            )
        else:
            contest.controller_name = (
                'oioioi.programs.controllers.ProgrammingContestController'
            )
        contest.save()

    def test_round_inline(self):
        self.assertTrue(self.client.login(username='test_admin'))

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_contest_change', args=(quote('c'),))

        response = self.client.get(url)
        self.assertNotContains(response, 'Public results date')

        self._change_controller(public_results=True)

        response = self.client.get(url)
        self.assertContains(response, 'Public results date')

    def _check_public_results(self, expected):
        before_results = datetime(2012, 6, 20, 8, 0, tzinfo=timezone.utc)
        after_results_before_public = datetime(2012, 8, 20, 8, 0, tzinfo=timezone.utc)
        after_public = datetime(2012, 10, 20, 8, 0, tzinfo=timezone.utc)
        dates = [before_results, after_results_before_public, after_public]

        request = RequestFactory().request()
        request.contest = Contest.objects.get(id='c')
        request.user = User.objects.get(username='test_admin')
        round = Round.objects.get()

        rtime = rounds_times(request, round.contest)[round]
        for date, exp in zip(dates, expected):
            self.assertEqual(rtime.public_results_visible(date), exp)

    def test_public_results_visible(self):
        # Default controller implementation, there is only one results date
        self._check_public_results([False, True, True])

        self._change_controller(public_results=True)
        # public_results_date == None, so public results will never be visible
        self._check_public_results([False, False, False])

        round = Round.objects.get()
        round.public_results_date = datetime(2012, 9, 20, 8, 0, tzinfo=timezone.utc)
        round.save()
        self._check_public_results([False, False, True])

    def test_all_results_visible(self):
        def fake_request(timestamp):
            request = RequestFactory().request()
            request.contest = Contest.objects.get(id='c')
            request.user = AnonymousUser()
            request.timestamp = timestamp
            return request

        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.contests.tests.tests.ContestWithPublicResultsController'
        )
        contest.save()

        self.assertFalse(
            all_public_results_visible(
                fake_request(datetime(2012, 7, 31, 21, 0, 0, tzinfo=timezone.utc))
            )
        )

        round1 = Round.objects.get()
        round1.public_results_date = datetime(2012, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
        round1.save()

        self.assertFalse(
            all_public_results_visible(
                fake_request(datetime(2012, 7, 31, 21, 0, 0, tzinfo=timezone.utc))
            )
        )
        self.assertTrue(
            all_public_results_visible(
                fake_request(datetime(2012, 8, 1, 12, 30, 0, tzinfo=timezone.utc))
            )
        )

        round2 = Round(
            contest=round1.contest,
            name="Round 2",
            start_date=round1.start_date,
            results_date=round1.results_date,
            public_results_date=None,
            is_trial=True,
        )
        round2.save()

        self.assertFalse(
            all_public_results_visible(
                fake_request(datetime(2012, 8, 2, 12, 30, 0, tzinfo=timezone.utc))
            )
        )
        self.assertTrue(
            all_non_trial_public_results_visible(
                fake_request(datetime(2012, 8, 2, 12, 30, 0, tzinfo=timezone.utc))
            )
        )

        round2.public_results_date = datetime(2012, 8, 2, 12, 0, 0, tzinfo=timezone.utc)
        round2.save()

        self.assertTrue(
            all_public_results_visible(
                fake_request(datetime(2012, 8, 2, 12, 30, 0, tzinfo=timezone.utc))
            )
        )


class TestContestLinks(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_menu(self):
        self.assertTrue(self.client.login(username='test_user2'))
        contest = Contest.objects.get()

        ContestLink(
            contest=contest,
            description='Test Menu Item 1',
            url='/test_menu_link1',
            order=10,
        ).save()
        ContestLink(
            contest=contest, description='Test Menu Item 2', url='/test_menu_link2'
        ).save()

        url = reverse('default_contest_view', kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Menu Item 1')
        self.assertContains(response, 'Test Menu Item 2')
        self.assertContains(response, '/test_menu_link1')
        self.assertContains(response, '/test_menu_link2')
        content = response.content.decode('utf-8')
        self.assertLess(
            content.index('Test Menu Item 1'), content.index('Test Menu Item 2')
        )
        self.assertLess(
            content.index('/test_menu_link1'), content.index('/test_menu_link2')
        )


class TestPersonalDataUser(TestCase):
    fixtures = ['test_contest', 'test_permissions']

    def testUser(self):
        self.assertTrue(self.client.login(username='test_personal_data_user'))
        self.assertTrue(can_see_personal_data)


class TestUserInfo(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_user_info_page(self):
        contest = Contest.objects.get()
        user = User.objects.get(pk=1001)
        url = reverse(
            'user_info', kwargs={'contest_id': contest.id, 'user_id': user.id}
        )

        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url, follow=True)
            self.assertContains(response, '403', status_code=403)

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url, follow=True)
            self.assertContains(response, 'title>Test User - User info')
            self.assertContains(response, "User's submissions")
            self.assertNotContains(response, "<h4>User's round time extensions:</h4>")

        round = Round.objects.get()
        ext = RoundTimeExtension(user=user, round=round, extra_time=20)
        ext.save()

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertContains(response, "<h4>User's round time extensions:</h4>")
        self.assertContains(response, "Extra time: 20")


class TestProblemInstanceView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
        'test_problem_site',
    ]

    def test_admin_change_view(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        problem_instance = Problem.objects.all()[0]
        url = reverse(
            'oioioiadmin:contests_probleminstance_change', args=(problem_instance.id,)
        )
        response = self.client.get(url)
        elements_to_find = ['0', '1a', '1b', '1ocen', '2', 'Example', 'Normal']
        for element in elements_to_find:
            self.assertContains(response, element)

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
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        problem_instance = ProblemInstance.objects.filter(contest__isnull=False)[0]
        url = reverse(
            'reset_tests_limits_for_probleminstance', args=(problem_instance.id,)
        )
        for t in problem_instance.test_set.all():
            t.delete()

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, data={'submit': True}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tests limits reset successfully")
        self.assertEqual(
            problem_instance.test_set.count(),
            problem_instance.problem.main_problem_instance.test_set.count(),
        )
        self.assertNotEqual(problem_instance.test_set.count(), 0)

    def test_rejudge_not_needed(self):
        pi = ProblemInstance.objects.get()
        pi.needs_rejudge = True
        pi.save()

        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/{}/'.format(pi.contest.pk))
        response = self.client.post(
            reverse('rejudge_not_needed', args=(pi.id,)),
            data={'submit': True},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        pi.refresh_from_db()
        self.assertFalse(pi.needs_rejudge)


class TestReattachingProblems(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_extra_contests',
        'test_full_package',
        'test_problem_instance',
        'test_extra_problem',
        'test_permissions',
        'test_problem_site',
    ]

    def test_reattaching_problem(self):
        c2 = Contest.objects.get(id='c2')
        c2.default_submissions_limit = 123
        c2.save()

        pi_id = ProblemInstance.objects.get(id=1).id
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('reattach_problem_contest_list', args=('full',)) + "/?ids={}".format(pi_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a contest to attach the following problems to:")
        self.assertContains(response, '<td><a', count=Contest.objects.count())

        url = reverse('reattach_problem_confirm', args=('c2',)) + "/?ids={}".format(pi_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Extra test contest 2")
        self.assertContains(response, u'Sum\u017cyce')
        self.assertContains(response, "Attach")

        response = self.client.post(url, data={'submit': True}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'c2')
        self.assertEqual(ProblemInstance.objects.count(), 3)
        self.assertContains(response, ' added successfully.')
        self.assertContains(response, u'Sum\u017cyce')
        self.assertTrue(ProblemInstance.objects.filter(contest__id='c2').exists())
        self.assertEqual(
            ProblemInstance.objects.get(contest__id='c2').submissions_limit, 123
        )

        for test in Problem.objects.get().main_problem_instance.test_set.all():
            test.delete()
        self.assertTrue(Test.objects.count() > 0)

    def test_reattaching_problems(self):
        c2 = Contest.objects.get(id='c2')
        c2.default_submissions_limit = 123
        c2.save()

        pi_id1 = ProblemInstance.objects.get(id=1).id
        pi_id2 = ProblemInstance.objects.get(id=2).id
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('reattach_problem_contest_list', args=('full',)) + "/?ids={}%2C{}".format(
            pi_id1, pi_id2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose a contest to attach the following problems to:")
        self.assertContains(response, '<td><a', count=Contest.objects.count())
        self.assertContains(response, 'zad1')
        self.assertContains(response, 'zad-extra')

        url = reverse('reattach_problem_confirm', args=('c2',)) + "/?ids={}%2C{}".format(
            pi_id1, pi_id2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Extra test contest 2")
        self.assertContains(response, u'Sum\u017cyce')
        self.assertContains(response, "Attach")

        response = self.client.post(url, data={'submit': True}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'c2')
        self.assertEqual(ProblemInstance.objects.count(), 4)
        self.assertContains(response, ' added successfully.')
        self.assertContains(response, u'Sum\u017cyce')
        self.assertTrue(ProblemInstance.objects.filter(contest__id='c2').exists())
        for problem in ProblemInstance.objects.filter(contest__id='c2'):
            self.assertEqual(problem.submissions_limit, 123)

        for problem in Problem.objects.all():
            for test in problem.main_problem_instance.test_set.all():
                test.delete()
        self.assertTrue(Test.objects.count() > 0)



    def test_permissions(self):
        pi_id = ProblemInstance.objects.get(id=1).id
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        urls = [
            reverse('reattach_problem_contest_list') + "/?ids={}".format(pi_id),
            reverse('reattach_problem_confirm', args=('c1',)) + "/?ids={}".format(pi_id),
        ]
        for url in urls:
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_user'))
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
        controller_name = 'oioioi.programs.controllers.ProgrammingContestController'

        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Judging priority")
        self.assertNotContains(response, "Judging weight")
        post_data = make_empty_contest_formset()
        post_data.update(
            {
                'name': 'Yet Another Contest',
                'id': 'yac',
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': controller_name,
                'is_archived': 'False',
            }
        )
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # self.assertContains(response, 'was added successfully')
        contest = Contest.objects.get()
        self.assertEqual(controller_name, contest.controller_name)
        ContestPermission(
            user=User.objects.get(pk=1001),
            contest=contest,
            permission='contests.contest_admin',
        ).save()

        url = reverse('oioioiadmin:contests_contest_change', args=(quote('yac'),))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Judging priority")
        self.assertContains(response, "Judging weight")

        self.assertTrue(self.client.login(username='test_user'))
        url = (
            reverse('oioioiadmin:contests_contest_change', args=(quote('yac'),))
            + '?simple=true'
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Default submissions limit")
        self.assertNotContains(response, "Judging priority")
        self.assertNotContains(response, "Judging weight")
        post_data = make_empty_contest_formset()
        post_data.update(
            {
                'name': 'New Name',
                'start_date_0': '2013-02-03',
                'start_date_1': '14:05:06',
                'end_date_0': '2013-02-04',
                'end_date_1': '15:06:07',
                'results_date_0': '2013-02-05',
                'results_date_1': '16:07:08',
            }
        )
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        contest = Contest.objects.get()
        self.assertEqual(contest.id, 'yac')
        self.assertEqual(controller_name, contest.controller_name)

        url = reverse('oioioiadmin:contests_contest_change', args=(quote('yac'),))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Default submissions limit")
        self.assertNotContains(response, "Judging priority")
        self.assertNotContains(response, "Judging weight")


class TestRegistrationController(TestCase):
    fixtures = ['test_two_empty_contests', 'test_users']

    def test_filter_visible_contests(self):
        invisible_contest = Contest(
            id='invisible',
            name='Invisible Contest',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        invisible_contest.save()

        c1 = Contest.objects.get(id='c1')
        c2 = Contest.objects.get(id='c2')

        request = self.client.get('/').wsgi_request

        public_rc = c1.controller.registration_controller()
        private_rc = invisible_contest.controller.registration_controller()

        def assert_public_are_visible():
            results = public_rc.filter_visible_contests(
                request, Contest.objects.filter(id__in=[c1.id, c2.id])
            )
            visible_contests = list(results.values_list('id', flat=True))
            self.assertEqual(len(visible_contests), 2)
            self.assertTrue(c1.id in visible_contests)
            self.assertTrue(c2.id in visible_contests)

        def query_private(request):
            return private_rc.filter_visible_contests(
                request, Contest.objects.filter(id=invisible_contest.id)
            )

        # Check anonymous
        assert_public_are_visible()
        self.assertFalse(query_private(request).exists())

        # Check logged in
        self.assertTrue(self.client.login(username='test_user'))
        user = User.objects.get(username='test_user')

        assert_public_are_visible()
        self.assertFalse(query_private(request).exists())

        ContestPermission(
            user=user, contest=invisible_contest, permission='contests.contest_admin'
        ).save()
        request = self.client.get('/', follow=True).wsgi_request
        visible = list(query_private(request).values_list('id', flat=True))
        self.assertEqual(len(visible), 1)
        self.assertTrue(invisible_contest.id in visible)


class TestAdministeredContests(TestCase):
    fixtures = ['test_two_empty_contests', 'test_users']

    def test_administered_contests(self):
        self.assertTrue(self.client.login(username='test_user'))
        request = self.client.get('/').wsgi_request
        administered = administered_contests(request)
        self.assertEqual(len(administered), 0)
        self.assertTrue(self.client.login(username='test_admin'))
        request = self.client.get('/').wsgi_request
        administered = administered_contests(request)
        self.assertEqual(len(administered), 2)


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestSubmissionViewWithoutContest(TestCase):
    fixtures = [
        'test_contest',
        'test_users',
        'test_full_package',
        'test_problem_site',
        'test_problem_instance_with_no_contest',
        'test_submission',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))
        super().setUp()

    def test_submission_view_without_contest(self):
        submission = Submission.objects.get(id=1)
        response = self.client.get(reverse('submission', kwargs={'submission_id': 1}))
        self.assertEqual(response.status_code, 200)

        # Submit another button
        problemsite = submission.problem_instance.problem.problemsite
        problemsite_url = reverse(
            'problem_site', kwargs={'site_key': problemsite.url_key}
        )
        self.assertContains(response, problemsite_url)


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestSubmissionAdminWithoutContest(TestCase, SubmitFileMixin):
    fixtures = [
        'test_extra_contests',
        'test_users',
        'test_full_package',
        'test_extra_problem_instance',
        'test_extra_submission',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_admin'))
        super().setUp()

    def test_submission_admin_without_contest(self):
        contest1 = Contest.objects.get(pk='c1')
        url = reverse(
            'oioioiadmin:contests_submission_changelist', kwargs={'contest_id': None}
        )
        response = self.client.get(url)
        self.assertContains(response, '<th class="field-id">', count=2, status_code=200)
        url = reverse(
            'oioioiadmin:contests_submission_changelist',
            kwargs={'contest_id': contest1.id},
        )
        response = self.client.get(url)
        self.assertContains(response, '<th class="field-id">', count=1, status_code=200)


def see_limits_on_problems_list(
    self, username, displays_submissions_limit, displays_tries_left, additional=[]
):
    def assert_contains_if(should_contain):
        return self.assertContains if should_contain else self.assertNotContains

    if username is None:
        self.client.logout()
    else:
        self.assertTrue(self.client.login(username=username))

    response = self.client.get('/c/c/p', follow=True)
    assert_contains_if(displays_tries_left)(response, 'Tries left')
    assert_contains_if(displays_submissions_limit)(response, 'Submissions limit')
    for text in additional:
        self.assertContains(response, text)


class TestSubmissionsLimitOnListView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_anonymous_user(self):
        see_limits_on_problems_list(
            self,
            None,
            displays_submissions_limit=True,
            displays_tries_left=False,
            additional=['10'],
        )

    def test_user(self):
        see_limits_on_problems_list(
            self,
            'test_user',
            displays_submissions_limit=False,
            displays_tries_left=True,
            additional=['9 of 10'],
        )

    def test_admin(self):
        see_limits_on_problems_list(
            self,
            'test_admin',
            displays_submissions_limit=False,
            displays_tries_left=False,
        )


def see_link_for_submission_on_problem_list(self, username, should_see):
    if username is None:
        self.client.logout()
    else:
        self.assertTrue(self.client.login(username=username))

    contest = Contest.objects.get(pk='c')
    problems_url = reverse('problems_list', kwargs={'contest_id': contest.id})
    submission_url = reverse(
        'submission', kwargs={'contest_id': contest.id, 'submission_id': 1}
    )
    expected_hyperlink = '<a href="%s">' % submission_url

    response = self.client.get(problems_url, follow=True)

    if should_see:
        self.assertContains(response, expected_hyperlink)
    else:
        self.assertNotContains(response, expected_hyperlink)


class TestSubmissionsLinksOnListView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_link_to_submission_no_user(self):
        see_link_for_submission_on_problem_list(self, None, False)

    def test_link_to_submission_user(self):
        see_link_for_submission_on_problem_list(self, "test_user", True)

    def test_link_to_submission_admin(self):
        see_link_for_submission_on_problem_list(self, "test_admin", False)


class TestNoSubmissionsLimitOnListView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_submission',
        'test_problem_instance_with_no_submissions_limit',
    ]

    def test_not_displaying_limits(self):
        for user in [None, 'test_user', 'test_admin']:
            see_limits_on_problems_list(
                self, user, displays_submissions_limit=False, displays_tries_left=False
            )


class TestAPIGetProblemId(APITestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]
    view_name = 'api_contest_get_problem_id'

    def setUp(self):
        self.client.force_authenticate(user=User.objects.get(username='test_user'))
        self.contest = Contest.objects.get()
        self.problem_instance = ProblemInstance.objects.get(pk=1)
        self.problem = self.problem_instance.problem
        super().setUp()

    def test_successful_query(self):
        url = reverse(self.view_name, args=(self.contest.id, self.problem.short_name))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(self.problem.id == data.get('problem_id'))
        self.assertTrue(self.problem_instance.id == data.get('problem_instance_id'))

    def test_invalid_contest_id(self):
        url = reverse(
            self.view_name, args=('invalid-contest-id', self.problem.short_name)
        )
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_invalid_problem_short_name(self):
        url = reverse(self.view_name, args=(self.contest.id, 'invalid-short-name'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 404)


class TestAPISubmitBase(APITestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package', 'test_submission']
    extra_fixtures = []

    def __init__(self, *args, **kwargs):
        self.fixtures += self.extra_fixtures
        super(TestAPISubmitBase, self).__init__(*args, **kwargs)

    def setUp(self):
        self.client.force_authenticate(user=User.objects.get(username='test_user'))
        super().setUp()

    def submit_file(
        self,
        url_name,
        url_kwargs,
        file_size=1024,
        file_name='submission.cpp',
        kind=None,
    ):
        url = reverse(url_name, kwargs=url_kwargs)
        file = ContentFile(b'a' * file_size, name=file_name)
        post_data = {'file': file}
        if kind:
            post_data['kind'] = kind
        return self.client.post(url, post_data)

    def _assertSubmitted(self, response, i=None):
        self.assertEqual(response.status_code, 200)
        if i is not None:
            self.assertEqual(str(i), response.content.decode('utf-8'))
        Submission.objects.get(id=response.content)


class TestAPIContestSubmit(TestAPISubmitBase):
    extra_fixtures = ['test_problem_instance']

    def contest_submit(self, contest, pi, *args, **kwargs):
        return self.submit_file(
            'api_contest_submit',
            {'contest_name': contest.id, 'problem_short_name': pi.short_name},
            *args,
            **kwargs
        )

    def test_simple_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.save()

        with fake_time(datetime(2012, 7, 10, tzinfo=timezone.utc)):
            response = self.contest_submit(contest, problem_instance)
            self.assertContains(response, 'Permission denied', status_code=400)

        with fake_time(datetime(2012, 7, 31, tzinfo=timezone.utc)):
            response = self.contest_submit(contest, problem_instance)
            self._assertSubmitted(response, 2)

        with fake_time(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            response = self.contest_submit(contest, problem_instance)
            self._assertSubmitted(response, 3)

        with fake_time(datetime(2012, 8, 10, tzinfo=timezone.utc)):
            response = self.contest_submit(contest, problem_instance)
            self._assertSubmitted(response, 4)

        with fake_time(datetime(2012, 8, 11, tzinfo=timezone.utc)):
            response = self.contest_submit(contest, problem_instance)
            self.assertContains(response, 'Permission denied', status_code=400)

    def test_submissions_limitation(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        problem_instance.submissions_limit = 2
        problem_instance.save()
        response = self.contest_submit(contest, problem_instance)
        self._assertSubmitted(response, 2)
        response = self.contest_submit(contest, problem_instance)
        self.assertContains(
            response, 'Submission limit for the problem', status_code=400
        )

    def test_huge_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.contest_submit(contest, problem_instance, file_size=102405)
        self.assertContains(response, 'File size limit exceeded.', status_code=400)

    def test_size_limit_accuracy(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.contest_submit(contest, problem_instance, file_size=102400)
        self._assertSubmitted(response, 2)

    def _assertUnsupportedExtension(self, contest, problem_instance, name, ext):
        response = self.contest_submit(
            contest, problem_instance, file_name='%s.%s' % (name, ext)
        )
        self.assertContains(
            response, 'Unknown or not supported file extension.', status_code=400
        )

    def test_limiting_extensions(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        self._assertUnsupportedExtension(
            contest, problem_instance, 'xxx', 'inv4l1d_3xt'
        )
        response = self.contest_submit(contest, problem_instance, file_name='a.c')
        self._assertSubmitted(response, 2)


class TestAPIProblemsetSubmit(TestAPISubmitBase):
    extra_fixtures = ['test_problem_site', 'test_problem_instance_with_no_contest']

    # As problemset submissions share most of the logic with contest submissions
    # they have only few simple tests

    def problemset_submit(self, problem=None, site_key=None, *args, **kwargs):
        if problem is not None:
            site_key = problem.problemsite.url_key
        return self.submit_file(
            'api_problemset_submit', {'problem_site_key': site_key}, *args, **kwargs
        )

    def test_problemset_submission(self):
        response = self.problemset_submit(site_key='123')
        self.assertEqual(response.status_code, 200)
        self._assertSubmitted(response, 2)


class TestAPIContestList(TestCase):
    fixtures = [
        'test_users',
        'test_participant',
        'test_contest',
    ]

    def test(self):
        contest_list_endpoint = reverse('api_contest_list')
        request_anon = self.client.get(contest_list_endpoint)
        self.assertEqual(403, request_anon.status_code)

        self.assertTrue(self.client.login(username='test_user'))
        request_auth = self.client.get(contest_list_endpoint)
        self.assertEqual(200, request_auth.status_code)


class TestAPIRoundList(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
    ]

    def test(self):
        contest_id = Contest.objects.get(pk='c').id
        round_list_endpoint = reverse('api_round_list', args=(contest_id))
        request_anon = self.client.get(round_list_endpoint)

        self.assertEqual(401, request_anon.status_code)
        self.assertTrue(self.client.login(username='test_user'))
        request_auth = self.client.get(round_list_endpoint)
        self.assertEqual(200, request_auth.status_code)

        json_data = request_auth.json()
        self.assertEqual(1, len(json_data))

        json_data_0 = json_data[0]
        self.assertEqual('Round 1', json_data_0['name'])
        self.assertEqual(None, json_data_0['end_date'])
        self.assertTrue(json_data_0['is_active'])
        self.assertFalse(json_data_0['is_trial'])


class TestAPIProblemList(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test(self):
        contest_id = Contest.objects.get(pk='c').id
        problem_list_endpoint = reverse('api_problem_list', args=(contest_id))
        request_anon = self.client.get(problem_list_endpoint)

        self.assertEqual(401, request_anon.status_code)
        self.assertTrue(self.client.login(username='test_user'))
        request_auth = self.client.get(problem_list_endpoint)
        self.assertEqual(200, request_auth.status_code)

        json_data = request_auth.json()
        self.assertEqual(1, len(json_data))

        json_data_0 = json_data[0]
        self.assertEqual(1, json_data_0['id'])
        self.assertEqual('zad1', json_data_0['short_name'])
        self.assertEqual(1, json_data_0['round'])
        self.assertEqual(10, json_data_0['submissions_limit'])
        self.assertEqual(1, json_data_0['round'])
        self.assertEqual('Sumżyce', json_data_0['full_name'])
        self.assertEqual(10, json_data_0['submissions_left'])
        self.assertTrue(json_data_0['can_submit'])
        self.assertEqual('.pdf', json_data_0['statement_extension'])


class TestAPIProblemSubmissionList(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test(self):
        pi = ProblemInstance.objects.get(pk=1)
        # It is really important, that ProblemInstance.short_name matches
        # Problem.short_name, as otherwise this endpoint does not work.
        # Situation, where it doesn't match is only possible in test.
        pi.short_name = pi.problem.short_name
        pi.save()
        submission_list_endpoint = reverse(
            'api_user_problem_submission_list', args=(
                pi.contest.id,
                pi.problem.short_name
            )
        )
        request_anon = self.client.get(submission_list_endpoint)

        self.assertEqual(401, request_anon.status_code)
        self.assertTrue(self.client.login(username='test_user'))
        request_auth = self.client.get(submission_list_endpoint)
        self.assertEqual(200, request_auth.status_code)

        json_data = request_auth.json()
        self.assertFalse(json_data['is_truncated_to_20'])
        self.assertEqual(len(json_data['submissions']), 1)
        self.assertEqual(json_data['submissions'][0]['id'], 1)
        self.assertEqual(json_data['submissions'][0]['score'], 34)
        self.assertEqual(json_data['submissions'][0]['status'], 'OK')


class TestAPIProblemSubmissionCode(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_submission_source',
    ]

    def test(self):
        pi = ProblemInstance.objects.get(pk=1)
        # A submission of a file `submission.cpp`
        submission_code_endpoint = reverse(
            'api_user_problem_submission_code', args=(
                pi.contest.id,
                1
            )
        )
        request_anon = self.client.get(submission_code_endpoint)

        self.assertEqual(401, request_anon.status_code)
        self.assertTrue(self.client.login(username='test_user'))
        request_auth = self.client.get(submission_code_endpoint, follow=True)
        self.assertEqual(200, request_auth.status_code)

        json_data = request_auth.json()
        self.assertEqual(json_data['lang'], 'cpp');
        self.assertTrue('#include <iostream>' in json_data['code']);


class TestManyRoundsNoEnd(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_rounds_no_end',
    ]

    def test_not_sorting(self):
        contest = Contest.objects.get(pk='c')
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(
            reverse('problems_list', kwargs={'contest_id': contest.id})
        )
        prev = 0
        response_body = bytes(response).decode('utf-8')

        for task in ['zad2', 'zad3', 'zad4', 'zad1']:
            self.assertContains(response, task)
            current = response_body.index(task)
            self.assertLess(prev, current)
            prev = current


# checks ranking visibility without RankingVisibilityConfig,
# with it set to default and with it set to 'YES'
def check_ranking_visibility(self, url, rvc):

    # test without RankingVisibilityConfig
    response = self.client.get(url)
    self.assertContains(response, 'Test User')

    rvc.save()

    # test with default RankingVisibilityConfig
    response = self.client.get(url)
    self.assertContains(response, 'Test User')

    rvc.visible = 'YES'
    rvc.save()

    # test with RankingVisibilityConfig set to 'YES'
    response = self.client.get(url)
    self.assertContains(response, 'Test User')


class TestRankingVisibility(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_user(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_user'))

        rvc = RankingVisibilityConfig(contest=contest)

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        check_ranking_visibility(self, url, rvc)

        rvc.visible = 'NO'
        rvc.save()

        # test with RankingVisibilityConfig set to 'NO'
        response = self.client.get(url)
        with self.assertRaises(AssertionError):
            self.assertContains(response, 'Test User')

    def test_admin(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))

        rvc = RankingVisibilityConfig(contest=contest)

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        check_ranking_visibility(self, url, rvc)

        rvc.visible = 'NO'
        rvc.save()

        # test with RankingVisibilityConfig set to 'NO'
        response = self.client.get(url)
        self.assertContains(response, 'Test User')


@override_settings(LANGUAGE_CODE="en")
class TestContestChangeForm(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_contest_change_form(self):
        url = reverse('admin:contests_contest_change', args=('c',))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Advanced </button>')
        self.assertNotContains(response, '<h5 class="mb-0">Rounds</h5>')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Advanced </button>')
        self.assertContains(response, '<h5 class="mb-0">Rounds</h5>')
        self.assertNotContains(response, 'None </button>')


def set_registration_availability(rvc, enabled, available_from=None, available_to=None):
    rvc.enabled = enabled
    rvc.registration_available_from = available_from
    rvc.registration_available_to = available_to
    rvc.save()


def check_registration(self, expected_status_code, availability, available_from=None, available_to=None, expected_template=None):
    contest = Contest.objects.get()
    contest.controller_name = 'oioioi.oi.controllers.OIContestController'
    contest.save()

    url = reverse('participants_register', kwargs={'contest_id': contest.id})
    self.assertTrue(self.client.login(username='test_user'))

    rvc = RegistrationAvailabilityConfig(contest=contest)

    set_registration_availability(rvc, availability, available_from, available_to)
    response = self.client.get(url)
    self.assertEqual(expected_status_code, response.status_code)
    if expected_template == 'registration_not_open_yet':
        self.assertTemplateUsed(response, 'contests/registration_not_open_yet.html')


class TestOpenRegistration(TestCase):
    fixtures = [
        'test_users',
        'test_contest'
    ]

    def test_open_registration(self):
        check_registration(self, 200, 'YES')

    def test_closed_registration(self):
        check_registration(self, 403, 'NO')

    def test_configured_registration_opened(self):
        now = datetime.utcnow()
        available_from = now - timedelta(days=1)
        available_to = now + timedelta(days=1)
        check_registration(self, 200, 'CONFIG', available_from, available_to)

    def test_configured_registration_closed_before(self):
        now = datetime.utcnow()
        available_from = now + timedelta(hours=1)
        available_to = now + timedelta(days=1)
        check_registration(self, 200, 'CONFIG', available_from, available_to, 'registration_not_open_yet')

    def test_configured_registration_closed_after(self):
        now = datetime.utcnow()
        available_from = now - timedelta(hours=1)
        available_to = now - timedelta(minutes=5)
        check_registration(self, 403, 'CONFIG', available_from, available_to)

class TestRulesVisibility(TestCase):
    fixtures = [
        'test_users',
        'test_participant',
        'test_contest',
        'test_full_package',
        'test_three_problem_instances.json'
    ]

    controller_names = [
        'oioioi.acm.controllers.ACMContestController',
        'oioioi.acm.controllers.ACMOpenContestController',
        'oioioi.amppz.controllers.AMPPZContestController',
        'oioioi.mp.controllers.MPContestController',
        'oioioi.oi.controllers.OIContestController',
        'oioioi.oi.controllers.OIOnsiteContestController',
        'oioioi.oi.controllers.OIFinalOnsiteContestController',
        'oioioi.oi.controllers.BOIOnsiteContestController',
        'oioioi.oi.controllers.BOIOnlineContestController',
        'oioioi.pa.controllers.PAContestController',
        'oioioi.pa.controllers.PAFinalsContestController',
        'oioioi.programs.controllers.ProgrammingContestController'         
    ]

    # left to fill in when added, in order of the controllers above
    scoring_descriptions = [
        "The solutions are judged on real-time. "
        "The submission is correct if it passes all the test cases.<br>"
        "Participants are ranked by the number of solved problems. "
        "In case of a tie, the times of first correct submissions are summed up and a penalty of 20 minutes is added for each incorrect submission.<br>"
        "The lower the total time, the higher the rank.<br>"
        "Compilation errors and system errors are not considered as an incorrect submission.<br>"
        "The ranking is frozen 60 minutes before the end of the round.",

        "The solutions are judged on real-time. "
        "The submission is correct if it passes all the test cases.<br>"
        "Participants are ranked by the number of solved problems. "
        "In case of a tie, the times of first correct submissions are summed up and a penalty of 20 minutes is added for each incorrect submission.<br>"
        "The lower the total time, the higher the rank.<br>"
        "Compilation errors and system errors are not considered as an incorrect submission.<br>"
        "The ranking is frozen 60 minutes before the end of the round.",

        "The solutions are judged on real-time. "
        "The submission is correct if it passes all the test cases.<br>"
        "Participants are ranked by the number of solved problems. "
        "In case of a tie, the times of first correct submissions are summed up and a penalty of 20 minutes is added for each incorrect submission.<br>"
        "The lower the total time, the higher the rank.<br>"
        "Compilation errors and system errors are not considered as an incorrect submission.<br>"
        "The ranking is frozen 15 minutes before the end of the trial rounds and 60 minutes before the end of the normal rounds.",

        "The submissions are scored from 0 to 100 points.<br>"
        "The participant can submit to finished rounds, but a multiplier is applied to the score of such submissions.",

        "The solutions are judged with sio2jail. They can be scored from 0 to 100 points. "
        "If the submission runs for longer than half of the time limit, the points for this test are linearly decreased to 0.<br>"
        "The score for a group of test cases is the minimum score for any of the test cases.<br>"
        "The ranking is determined by the total score.<br>"
        "Until the end of the contest, participants can only see scoring of their submissions on example test cases. "
        "Full scoring is available after the end of the contest.",

        "The solutions are judged with sio2jail. They can be scored from 0 to 100 points. "
        "If the submission runs for longer than half of the time limit, the points for this test are linearly decreased to 0.<br>"
        "The score for a group of test cases is the minimum score for any of the test cases.<br>"
        "The ranking is determined by the total score.<br>"
        "Until the end of the contest, participants can only see scoring of their submissions on example test cases. "
        "Full scoring is available after the end of the contest.",

        "The solutions are judged with sio2jail. They can be scored from 0 to 100 points. "
        "If the submission runs for longer than half of the time limit, the points for this test are linearly decreased to 0.<br>"
        "The score for a group of test cases is the minimum score for any of the test cases<br>."
        "The ranking is determined by the total score.<br>"
        "Full scoring of the submissions can be revealed during the contest.",

        '',

        '',

        "The submissions are judged on real-time. All problems have 10 test groups, each worth 1 point. "
        "If any of the tests in a group fails, the group is worth 0 points.<br>"
        "The full scoring is available after the end of the round."
        "The ranking is determined by the total score and number of 10-score submissions, 9-score, 8-score etc.",

        "The solutions are judged on real-time. "
        "The submission is correct if it passes all the test cases.<br>"
        "Participants are ranked by the number of solved problems. "
        "In case of a tie, the times of first correct submissions are summed up and a penalty of 20 minutes is added for each incorrect submission.<br>"
        "The lower the total time, the higher the rank.<br>"
        "Compilation errors and system errors are not considered as an incorrect submission.<br>"
        "The ranking is frozen 15 minutes before the end of the trial rounds and 60 minutes before the end of the normal rounds.",

        "The submissions are scored on a set of groups of test cases. Each group is worth a certain number of points.<br>"
        "The score is a sum of the scores of all groups. The ranking is determined by the total score.<br>"
        "The full scoring is available after the results date for the round."
    ]

    visibility_dates = [
        [
            datetime(2012, 8, 15, 20, 27, 58, tzinfo=timezone.utc),
            None
        ],
        [
            datetime(2012, 8, 15, 20, 27, 58, tzinfo=timezone.utc), 
            datetime(2013, 4, 20, 21, 37, 13, tzinfo=timezone.utc)
        ],
        [
            None,
            None
        ]
    ]

    def _set_problem_limits(self, url, limits_list):
        for i in range(len(limits_list)):
            problem = ProblemInstance.objects.get(pk=i+1)
            problem.submissions_limit = limits_list[i]
            problem.save()
        
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        return response
    
    def _set_results_dates(self, url, dates):
        round = Round.objects.get()
        round.results_date = dates[0]
        round.public_results_date = dates[1]
        round.save()

        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        return response

    def _change_controller(self, public_results=False):
        contest = Contest.objects.get()
        if public_results:
            contest.controller_name = (
                'oioioi.contests.tests.tests.ContestWithPublicResultsController'
            )
        else:
            contest.controller_name = (
                'oioioi.programs.controllers.ProgrammingContestController'
            )
        contest.save()
    
    def test_dashboard_view(self):
        for c in self.controller_names:
            contest = Contest.objects.get()
            contest.controller_name = c
            contest.save()
            self.assertTrue(self.client.login(username='test_user'))
            url = reverse('default_contest_view', kwargs={'contest_id': 'c'})
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Rules")
        
    def test_contest_type(self):
        for c, d in zip(self.controller_names, self.scoring_descriptions):
            contest = Contest.objects.get()
            contest.controller_name = c
            contest.save()
            self.assertTrue(self.client.login(username='test_user'))
            url = reverse('contest_rules', kwargs={'contest_id': 'c'})
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, d)

    def test_no_of_rounds(self):
        for c in self.controller_names:
            contest = Contest.objects.get()
            contest.controller_name = c
            contest.save()

            # a bigger number of rounds is tested in TestManyRounds::test_rules_visibility
            self.assertTrue(self.client.login(username='test_user'))
            url = reverse('contest_rules', kwargs={'contest_id': 'c'})
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "The contest has 1 round.")

    def test_problem_limits(self):
        for c in self.controller_names:
            contest = Contest.objects.get()
            contest.controller_name = c
            contest.save()

            self.assertTrue(self.client.login(username='test_user'))
            url = reverse('contest_rules', kwargs={'contest_id': 'c'})
            response = self._set_problem_limits(url, [0, 0, 0])
            self.assertContains(response, "There is a limit of infinity submissions for each problem.")

            response = self._set_problem_limits(url, [0, 10, 0])
            self.assertContains(response, "There is a limit of 10 to infinity submissions, depending on a problem.")

            response = self._set_problem_limits(url, [20, 10, 0])
            self.assertContains(response, "There is a limit of 10 to infinity submissions, depending on a problem.")

            response = self._set_problem_limits(url, [10, 10, 10])
            self.assertContains(response, "There is a limit of 10 submissions for each problem.")

    def test_contest_dates(self):
        times = [
            fake_time(datetime(2012, 8, 5, 12, 37, 45, tzinfo=timezone.utc)),
            fake_time(datetime(2012, 8, 15, 15, 16, 18, tzinfo=timezone.utc))
        ]

        for t in times:
            with t:
                for c in self.controller_names:
                    contest = Contest.objects.get()
                    contest.controller_name = c
                    contest.save()
                    
                    round = Round.objects.get()
                    round.end_date = None
                    round.save()

                    self.assertTrue(self.client.login(username='test_user'))
                    url = reverse('contest_rules', kwargs={'contest_id': 'c'})
                    response = self.client.get(url, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, "The contest starts on 2011-07-31 20:27:58.")

                    round.end_date = datetime(2012, 8, 10, 0, 0, tzinfo=timezone.utc)
                    round.save()
                    response = self.client.get(url, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, "The contest starts on 2011-07-31 20:27:58 and ends on 2012-08-10 00:00:00.")

    def test_ranking_visibility(self):
        # here we don't check for individual contests, as it would be hard to get the separate_public_results()
        # from the specific controller, and the only thing that utimately matters is separate_public_results setting
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('contest_rules', kwargs={'contest_id': 'c'})

        with fake_time(datetime(2012, 8, 4, 13, 46, 37, tzinfo=timezone.utc)):
            response = self._set_results_dates(url, self.visibility_dates[0])
            self.assertContains(response, "In round Round 1, your results as well as " \
                                "public ranking will be visible after 2012-08-15 20:27:58.")
        
            self._change_controller(public_results=True)
            response = self._set_results_dates(url, self.visibility_dates[1])
            self.assertContains(response, "In round Round 1, your results will be visible after 2012-08-15 20:27:58" \
                                " and the public ranking will be visible after 2013-04-20 21:37:13.")

            response = self._set_results_dates(url, self.visibility_dates[2])
            self.assertContains(response, "In round Round 1, your results as well as public ranking will be visible immediately.")

        with fake_time(datetime(2012, 12, 24, 11, 23, 56, tzinfo=timezone.utc)):
            response = self._set_results_dates(url, self.visibility_dates[0])
            self.assertContains(response, "In round Round 1, your results as well as public ranking will be visible immediately.")
        
            self._change_controller(public_results=True)
            response = self._set_results_dates(url, self.visibility_dates[1])
            self.assertContains(response, "In round Round 1, your results will be visible immediately" \
                                " and the public ranking will be visible after 2013-04-20 21:37:13.")

            response = self._set_results_dates(url, self.visibility_dates[2])
            self.assertContains(response, "In round Round 1, your results as well as public ranking will be visible immediately.")

        with fake_time(datetime(2014, 8, 26, 11, 23, 56, tzinfo=timezone.utc)):
            response = self._set_results_dates(url, self.visibility_dates[0])
            self.assertContains(response, "In round Round 1, your results as well as public ranking will be visible immediately.")
        
            self._change_controller(public_results=True)
            response = self._set_results_dates(url, self.visibility_dates[1])
            self.assertContains(response, "In round Round 1, your results as well as public ranking will be visible immediately.")

            response = self._set_results_dates(url, self.visibility_dates[2])
            self.assertContains(response, "In round Round 1, your results as well as public ranking will be visible immediately.")


class PublicMessageContestController(ProgrammingContestController):
    files_message = 'Test public message'
    submissions_message = 'Test public message'
    submit_message = 'Test public message'
    submission_message = 'Test public message'


class TestFilesMessage(TestPublicMessage):
    model = FilesMessage
    button_viewname = 'contest_files'
    edit_viewname = 'edit_files_message'
    viewname = 'contest_files'
    controller_name = 'oioioi.contests.tests.tests.PublicMessageContestController'


class TestSubmissionsMessage(TestPublicMessage):
    model = SubmissionsMessage
    button_viewname = 'my_submissions'
    edit_viewname = 'edit_submissions_message'
    viewname = 'my_submissions'
    controller_name = 'oioioi.contests.tests.tests.PublicMessageContestController'


class TestSubmitMessage(TestPublicMessage):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]
    model = SubmitMessage
    button_viewname = 'my_submissions'
    edit_viewname = 'edit_submit_message'
    viewname = 'submit'
    controller_name = 'oioioi.contests.tests.tests.PublicMessageContestController'


class TestSubmissionMessage(TestPublicMessage):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]
    model = SubmissionMessage
    button_viewname = 'my_submissions'
    edit_viewname = 'edit_submission_message'
    viewname = 'submission'
    controller_name = 'oioioi.contests.tests.tests.PublicMessageContestController'

    def setUp(self):
        super().setUp()
        contest = Contest.objects.get()
        submission = Submission.objects.get()
        self.viewname_kwargs = {'contest_id': contest.id, 'submission_id': submission.id}


class TestContestArchived(TestCase):
    fixtures = [
        'test_users',
        'test_archived_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_contest_archived(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()
        url = reverse('participants_register', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_submit(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('submit', kwargs={'contest_id': 'c'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_dashboard_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('default_contest_view', kwargs={'contest_id': 'c'})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This contest is archived.")
        self.assertNotContains(response, "Submit")

    def test_submissions_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('my_submissions', kwargs={'contest_id': 'c'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Submit")
        
    def test_submission_view(self):
        contest = Contest.objects.get()
        submission = Submission.objects.get(pk=1)
        self.assertTrue(self.client.login(username='test_user'))
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertNotContains(response, "Submit")

    def test_submission_list_visibility(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('my_submissions', kwargs={'contest_id': 'c'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sumżyce")

    def test_add_question(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('add_contest_message', kwargs={'contest_id': 'c'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_question_list_visibility(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('contest_all_messages', kwargs={'contest_id': 'c'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_registration(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()

        url = reverse('participants_register', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(url)
        self.assertEqual(403, response.status_code)

class TestScoreBadges(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_three_problem_instances',
        'test_full_package',
        'test_three_submissions',
    ]

    def _get_badge_for_problem(self, content, problem):
        soup = bs4.BeautifulSoup(content, 'html.parser')
        problem_row = soup.find('td', string=problem).parent
        return problem_row.find_all('td')[2].a.div.attrs['class']

    def test_score_badge(self):
        contest = Contest.objects.get()
        url = reverse('problems_list', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertIn('badge-success', self._get_badge_for_problem(response.content, 'zad1'))
        self.assertIn('badge-warning', self._get_badge_for_problem(response.content, 'zad2'))
        self.assertIn('badge-danger', self._get_badge_for_problem(response.content, 'zad3'))

class TestContestListFiltering(TestCase):
    fixtures = [
        'test_contest',
        'test_extra_contests',
    ]

    def setUp(self):
        self.c = Contest.objects.get(id='c')
        self.c1 = Contest.objects.get(id='c1')   
        self.c2 = Contest.objects.get(id='c2')

        return super().setUp()

    def test_simple_filter(self):
        self.url = reverse('filter_contests', kwargs={'filter_value':'test'})
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, self.c.name)
        self.assertContains(response, self.c1.name)
        self.assertContains(response, self.c2.name)

    def extra_filter(self):
        self.url = reverse('filter_contests', kwargs={'filter_value':'ExTrA'})
        response = self.client.get(self.url, follow=True)
        self.assertNotContains(response, self.c.name)
        self.assertContains(response, self.c1.name)
        self.assertContains(response, self.c2.name)
