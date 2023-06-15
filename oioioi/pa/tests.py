import re
from datetime import datetime, timezone  # pylint: disable=E0611

import urllib.parse

from django.contrib.admin.utils import quote
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from oioioi.base.tests import TestCase, fake_time, fake_timezone_now
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    Submission,
    UserResultForProblem,
)
from oioioi.contests.scores import IntegerScore
from oioioi.pa import utils
from oioioi.pa.controllers import A_PLUS_B_RANKING_KEY, B_RANKING_KEY
from oioioi.pa.models import PAProblemInstanceData, PARegistration
from oioioi.pa.score import PAScore, ScoreDistribution
from oioioi.participants.models import Participant, TermsAcceptedPhrase
from oioioi.problems.models import Problem


class TestPAScore(TestCase):
    def test_score_distribution(self):
        dist1 = ScoreDistribution([1] + [0] * 9)
        dist2 = ScoreDistribution([0] + [10] * 9)
        dist_null = ScoreDistribution([0] * 10)

        self.assertLess(dist2, dist1)
        self.assertLess(dist1, dist1 + dist2)
        self.assertLess(dist2 + dist2, dist1)
        self.assertLess(dist_null, dist1)
        self.assertLess(dist_null, dist2)

        self.assertEqual(dist_null, ScoreDistribution())
        self.assertEqual(dist_null + dist_null, dist_null)
        self.assertEqual(dist1 + dist_null, dist1)

        self.assertEqual(
            dist1._to_repr(),
            '00001:00000:00000:00000:00000:00000:00000:00000:00000:00000',
        )
        self.assertEqual(
            dist2._to_repr(),
            '00000:00010:00010:00010:00010:00010:00010:00010:00010:00010',
        )
        self.assertEqual(
            (dist1 + dist2)._to_repr(),
            '00001:00010:00010:00010:00010:00010:00010:00010:00010:00010',
        )

        self.assertEqual(dist1, ScoreDistribution._from_repr(dist1._to_repr()))
        self.assertEqual(dist2, ScoreDistribution._from_repr(dist2._to_repr()))

        self.assertEqual(
            repr(dist1),
            'ScoreDistribution(10: 1, 9: 0, 8: 0, 7: 0, 6: 0, 5: 0, 4: 0, '
            '3: 0, 2: 0, 1: 0)',
        )

    def test_pa_score(self):
        score = [PAScore(IntegerScore(x)) for x in range(0, 11)]

        self.assertLess(score[0], score[5])
        self.assertLess(score[5], score[10])
        self.assertLess(score[5] + score[5], score[10])
        self.assertLess(score[5] + score[5], score[2] + score[2] + score[6])
        self.assertLess(score[10], score[2] + score[4] + score[5])
        self.assertLess(score[2] + score[2] + score[6], score[1] + score[3] + score[6])

        dist1 = ScoreDistribution([0] * 8 + [2, 4])
        dist2 = ScoreDistribution([0] * 8 + [1, 6])
        score1 = PAScore(IntegerScore(8), dist1)
        score2 = PAScore(IntegerScore(8), dist2)
        self.assertLess(score2, score1)

        score3 = (
            score[10] + score[10] + score[10] + score[4] + score[2] + score1 + score2
        )

        self.assertEqual(score3, (3 * 10 + 4 + 2 + 2 * 8))
        self.assertEqual(
            repr(score3),
            'PAScore(IntegerScore(52), ScoreDistribution(10: 3, 9: 0, 8: '
            '0, 7: 0, 6: 0, 5: 0, 4: 1, 3: 0, 2: 4, 1: 10))',
        )
        self.assertEqual(
            score3._to_repr(),
            '0000000000000000052;00003:00000:'
            '00000:00000:00000:00000:00001:00000:00004:00010',
        )
        self.assertEqual(score3, PAScore._from_repr(score3._to_repr()))


class TestPARoundTimes(TestCase):
    fixtures = ['test_users', 'test_pa_contest']

    def test_round_states(self):
        contest = Contest.objects.get()
        controller = contest.controller

        not_last_submission = Submission.objects.get(id=6)
        # user's last submission
        not_my_submission = Submission.objects.get(id=10)
        user = User.objects.get(username='test_user')

        def check_round_state(date, expected):
            request = RequestFactory().request()
            request.contest = contest
            request.user = user
            request.timestamp = date

            self.assertTrue(self.client.login(username='test_user'))
            with fake_timezone_now(date):
                url = reverse(
                    'ranking', kwargs={'contest_id': 'c', 'key': A_PLUS_B_RANKING_KEY}
                )
                response = self.client.get(url)
                if expected[0]:
                    self.assertContains(response, 'taskA1')
                else:
                    self.assertNotContains(response, 'taskA1')

            self.assertEqual(
                expected[1], controller.can_see_source(request, not_my_submission)
            )

            self.assertEqual(
                False, controller.can_see_source(request, not_last_submission)
            )

        dates = [
            datetime(2012, 6, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2012, 8, 1, 0, 0, tzinfo=timezone.utc),
            datetime(2012, 10, 1, 0, 0, tzinfo=timezone.utc),
        ]

        # 1) results date of round 1
        # 2) public results date of round 1
        # 3) public results date of all rounds
        #
        #       ============== ==============
        # can: | see ranking  | see solutions of other participants
        #       ============== ==============
        # 1 -> |              |              |
        #      |    False     |    False     |
        # 2 -> |              |              |
        #      |    True      |    False     |
        # 3 -> |              |              |
        #      |    True      |    True      |
        #      |              |              |
        #       ============== ==============
        expected = [[False, False], [True, False], [True, True]]

        for date, exp in zip(dates, expected):
            check_round_state(date, exp)


class TestPARanking(TestCase):
    fixtures = ['test_users', 'test_pa_contest']

    def _ranking_url(self, key):
        contest = Contest.objects.get()
        return reverse('ranking', kwargs={'contest_id': contest.id, 'key': key})

    def test_divisions(self):
        def check_visibility(good_keys, response):
            division_for_pi = {1: 'A', 2: 'A', 3: 'B', 4: 'B', 5: 'NONE'}
            for key, div in division_for_pi.items():
                p = ProblemInstance.objects.get(pk=key)
                if div in good_keys:
                    self.assertContains(response, p.short_name)
                else:
                    self.assertNotContains(response, p.short_name)

        self.assertTrue(self.client.login(username='test_user'))

        with fake_timezone_now(datetime(2013, 1, 1, 0, 0, tzinfo=timezone.utc)):
            response = self.client.get(self._ranking_url(B_RANKING_KEY))
            check_visibility(['B'], response)
            response = self.client.get(self._ranking_url(A_PLUS_B_RANKING_KEY))
            check_visibility(['A', 'B'], response)
            # Round 3 is trial
            response = self.client.get(self._ranking_url(3))
            check_visibility(['NONE'], response)

    def test_no_zero_scores_in_ranking(self):
        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2013, 1, 1, 0, 0, tzinfo=timezone.utc)):
            response = self.client.get(self._ranking_url(3))
            # Test User should be present in the ranking.
            self.assertTrue(re.search(b'<td[^>]*>Test User</td>', response.content))
            # Test User 2 scored 0 points for the only task in the round.
            self.assertFalse(re.search(b'<td[^>]*>Test User 2</td>', response.content))

    def test_ranking_ordering(self):
        def check_order(response, expected):
            prev_pos = 0
            for user in expected:
                pattern = b'<td[^>]*>%s</td>' % (user,)
                pattern_match = re.search(pattern, response.content)

                self.assertTrue(pattern_match)
                self.assertContains(response, user)

                pos = pattern_match.start()
                self.assertGreater(
                    pos, prev_pos, msg=('User %s has incorrect ' 'position' % (user,))
                )
                prev_pos = pos

        self.assertTrue(self.client.login(username='test_user'))

        with fake_timezone_now(datetime(2013, 1, 1, 0, 0, tzinfo=timezone.utc)):
            # 28 (10, 8, 6, 4), 28 (9, 9, 7, 3), 10 (10)
            response = self.client.get(self._ranking_url(A_PLUS_B_RANKING_KEY))
            check_order(response, [b'Test User', b'Test User 2', b'Test User 3'])
            self.assertContains(response, b'28</td>')

            # 10 (10), 10 (7, 3), 10 (6, 4)
            response = self.client.get(self._ranking_url(B_RANKING_KEY))
            check_order(response, [b'Test User 3', b'Test User 2', b'Test User'])
            self.assertNotContains(response, b'28</td>')


class TestPARegistration(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_terms_accepted_phrase']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.pa.controllers.PAContestController'
        contest.save()
        self.reg_data = {
            'address': 'The Castle',
            'postal_code': '31-337',
            'city': 'Camelot',
            't_shirt_size': 'L',
            'job': 'AS',
            'job_name': 'WSRH',
            'terms_accepted': 't',
        }

    def test_default_terms_accepted_phrase(self):
        TermsAcceptedPhrase.objects.get().delete()
        contest = Contest.objects.get()
        url = reverse('participants_register', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)

        self.assertContains(
            response,
            'I declare that I have read the contest rules and '
            'the technical arrangements. I fully understand '
            'them and accept them unconditionally.',
        )

    def test_participants_registration(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        url = reverse('participants_register', kwargs={'contest_id': contest.id})
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)

        self.assertContains(response, 'Postal code')
        self.assertContains(response, 'Test terms accepted')

        user.first_name = 'Sir Lancelot'
        user.last_name = 'du Lac'
        user.save()

        response = self.client.post(url, self.reg_data)
        self.assertEqual(302, response.status_code)

        registration = PARegistration.objects.get(participant__user=user)
        self.assertEqual(registration.address, self.reg_data['address'])

    def test_contest_info(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user)
        p.save()
        PARegistration(participant_id=p.id, **self.reg_data).save()
        url = reverse('contest_info', kwargs={'contest_id': contest.id})
        data = self.client.get(url).json()
        self.assertEqual(data['users_count'], 1)


class TestPAScorer(TestCase):
    t_results_ok = (
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 0},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 10},
            {'result_code': 'OK', 'time_used': 99},
        ),
        (
            {'exec_time_limit': 1000, 'max_score': 0},
            {'result_code': 'OK', 'time_used': 123},
        ),
    )

    t_expected_ok = [
        (IntegerScore(1), IntegerScore(1), 'OK'),
        (IntegerScore(1), IntegerScore(1), 'OK'),
        (IntegerScore(0), IntegerScore(0), 'OK'),
    ]

    t_results_wrong = [
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'WA', 'time_used': 75},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 0},
            {'result_code': 'RV', 'time_used': 75},
        ),
    ]

    t_expected_wrong = [
        (IntegerScore(0), IntegerScore(1), 'WA'),
        (IntegerScore(0), IntegerScore(0), 'RV'),
    ]

    def test_pa_test_scorer(self):
        results = list(map(utils.pa_test_scorer, *list(zip(*self.t_results_ok))))
        self.assertEqual(self.t_expected_ok, results)

        results = list(map(utils.pa_test_scorer, *list(zip(*self.t_results_wrong))))
        self.assertEqual(self.t_expected_wrong, results)


class TestPAResults(TestCase):
    fixtures = ['test_users', 'test_pa_contest']

    def test_pa_user_results(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        old_results = sorted(
            [result.score for result in UserResultForProblem.objects.filter(user=user)]
        )
        for pi in ProblemInstance.objects.all():
            contest.controller.update_user_results(user, pi)
        new_results = sorted(
            [result.score for result in UserResultForProblem.objects.filter(user=user)]
        )
        self.assertEqual(old_results, new_results)


@override_settings(
    PROBLEM_PACKAGE_BACKENDS=('oioioi.problems.tests.DummyPackageBackend',)
)
class TestPADivisions(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_prolem_upload(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.pa.controllers.PAContestController'
        contest.save()

        self.assertTrue(self.client.login(username='test_admin'))
        url = (
            reverse('add_or_update_problem', kwargs={'contest_id': contest.id})
            + '?'
            + urllib.parse.urlencode({'key': 'upload'})
        )

        response = self.client.get(url)
        # "NONE" is the default division
        self.assertContains(response, '<option value="NONE" selected>None</option>')

        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'visibility': Problem.VISIBILITY_FRIENDS,
            'division': 'A',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        pid = PAProblemInstanceData.objects.get()
        problem = Problem.objects.get()
        self.assertEqual(pid.division, 'A')
        self.assertEqual(pid.problem_instance.problem, problem)

        url = (
            reverse('add_or_update_problem', kwargs={'contest_id': contest.id})
            + '?'
            + urllib.parse.urlencode({'problem': problem.id, 'key': 'upload'})
        )
        response = self.client.get(url)
        self.assertContains(response, '<option value="A" selected>A</option>')


class TestPAContestInfo(TestCase):
    fixtures = ['test_users', 'test_pa_contest']

    def test_contest_info_anonymous(self):
        c = Contest.objects.get()
        url = reverse('contest_info', kwargs={'contest_id': c.id})
        self.client.logout()
        response = self.client.get(url).json()
        self.assertEqual(response['users_count'], 2)

    def test_cross_origin(self):
        c = Contest.objects.get()
        url = reverse('contest_info', kwargs={'contest_id': c.id})
        response = self.client.get(url)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')


class TestPASafeExecModes(TestCase):
    fixtures = ['test_pa_contests_safe_exec_mode']

    def test_pa_quals_controller_safe_exec_mode(self):
        c = Contest.objects.get(pk="quals")
        self.assertEqual(c.controller.get_safe_exec_mode(), 'cpu')

    def test_pa_finals_controller_safe_exec_mode(self):
        c = Contest.objects.get(pk="finals")
        self.assertEqual(c.controller.get_safe_exec_mode(), 'cpu')


class TestPAAdmin(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_pa_registration',
        'test_permissions',
    ]

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.pa.controllers.PAContestController'
        contest.save()

    def test_terms_accepted_phrase_inline_admin_permissions(self):
        PARegistration.objects.all().delete()

        # Logging as superuser.
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_contest_change', args=(quote('c'),))

        response = self.client.get(url)
        self.assertContains(response, 'Text asking participant to accept contest terms')

        # Checks if the field is editable.
        self.assertContains(response, 'id_terms_accepted_phrase-0-text')

        # Logging as contest admin.
        self.assertTrue(self.client.login(username='test_contest_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_contest_change', args=(quote('c'),))

        response = self.client.get(url)
        self.assertContains(response, 'Text asking participant to accept contest terms')

        # Checks if the field is editable.
        self.assertContains(response, 'id_terms_accepted_phrase-0-text')

    def test_terms_accepted_phrase_inline_edit_restrictions(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_contest_change', args=(quote('c'),))

        response = self.client.get(url)
        self.assertContains(response, 'Text asking participant to accept contest terms')

        # Checks if the field is not editable.
        self.assertNotContains(response, 'id_terms_accepted_phrase-0-text')
