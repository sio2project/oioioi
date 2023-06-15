import re
from datetime import datetime, timezone  # pylint: disable=E0611

from django.conf import settings
from django.contrib.auth.models import User
from django.http import QueryDict
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.templatetags.simple_filters import result_color_class
from oioioi.base.tests import (
    TestCase,
    check_not_accessible,
    fake_time,
    fake_timezone_now,
)
from oioioi.contests.models import Contest, ProblemInstance, UserResultForProblem
from oioioi.contests.scores import IntegerScore
from oioioi.pa.score import PAScore
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController
from oioioi.rankings.models import (
    Ranking,
    RankingPage,
    RankingRecalc,
    choose_for_recalculation,
    recalculate,
)

VISIBLE_TASKS = ["zad1", "zad2"]
HIDDEN_TASKS = ["zad3", "zad4"]

USER_CELL_PATTERN = '<td[^>]*>%s</td>'  # Pattern accepting classes in td.
USER_CELL_PATTERN_LEFT = '<td[^>]*>%s'  # Some tests need this tag opened.


class StatementHiderForContestController(ProgrammingContestController):
    def default_can_see_statement(self, request_or_context, problem_instance):
        return problem_instance.short_name in VISIBLE_TASKS


class TestRankingViews(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_rounds',
        'test_ranking_data',
        'test_permissions',
    ]

    @override_settings(PARTICIPANTS_ON_PAGE=3)
    def test_find_user(self):
        number_of_users = 7  # this test will create that number of users
        per_page = settings.PARTICIPANTS_ON_PAGE
        contest = Contest.objects.get()
        pis = ProblemInstance.objects.get(id=1)

        UserResultForProblem.objects.all().delete()

        # Creates user and adds him a score for problem pis
        def create_score(username, score):
            user = User.objects.create_user(
                username, username + '@example.pl', username
            )
            result = UserResultForProblem()
            result.user = user
            result.problem_instance = pis
            result.status = 'OK'
            result.score = IntegerScore(score)
            result.save()
            return user

        # Recently created users
        users = []

        # Create all users with scores 0..number_of_users-1
        for i in range(number_of_users):
            users.append(create_score('find_user_generated%s' % i, i))

        self.assertTrue(self.client.login(username='test_contest_admin'))

        url = reverse('ranking', kwargs={'contest_id': contest.id, 'key': pis.round.id})

        def get_url_for_user(username):
            get = QueryDict('', mutable=True)
            get['user'] = username
            get['page'] = '1'
            return url + '?' + get.urlencode()

        def get_url_found_user(user, page):
            get = QueryDict('', mutable=True)
            get['page'] = page
            return url + '?' + get.urlencode() + '#' + str(user.id)

        user_not_in_ranking = User.objects.get(username='test_user')
        response = self.client.get(get_url_for_user(user_not_in_ranking.username))

        # Because there are two possible sources of error message,
        # check also if there's only one displayed.
        self.assertContains(response, 'User is not in the ranking.', 1)

        response = self.client.get(get_url_for_user('not_existing_username'))
        self.assertContains(response, 'User not found')

        # User has already received more accurate error.
        self.assertNotContains(response, 'User is not in the ranking.')

        # Contest admin shouldn't see 'Find my position' button
        self.assertNotContains(response, 'Find my place')

        for i in range(number_of_users):
            user = users[i]
            response = self.client.get(get_url_for_user(user.username))
            # On which page should the user be?
            page = str(((number_of_users - 1 - i) // per_page) + 1)
            self.assertRedirects(response, get_url_found_user(user, page))

        # Login as someone who is in the ranking
        user_num = 6  # a users list index
        self.assertTrue(self.client.login(username=users[user_num].username))
        response = self.client.get(get_url_for_user(user_not_in_ranking.username))
        self.assertNotContains(response, 'User is not in the ranking.')
        # Normal user shouldn't see the form
        self.assertNotContains(response, '<div class="search-for-user">')
        # Normal user should see 'Find my position' button
        self.assertContains(response, 'Find my place')

        # Test if users[0] can find himself
        response = self.client.get(get_url_for_user(users[user_num].username))
        page = str(((number_of_users - user_num) // per_page) + 1)
        self.assertRedirects(response, get_url_found_user(users[user_num], page))

        for i in range(number_of_users):
            if i == user_num:
                continue
            user = users[i]
            response = self.client.get(get_url_for_user(user.username))
            # Checking if user wasn't redirected (is on page 1)
            # User with the highest score should be visible
            self.assertContains(response, '<tr id="ranking_row_%s"' % users[-1].id)

        # Test if user who is not in the ranking receives error message.
        self.assertTrue(self.client.login(username=user_not_in_ranking.username))
        response = self.client.get(get_url_for_user(user_not_in_ranking.username))

        self.assertContains(response, 'User is not in the ranking.', 1)

    def test_ranking_view(self):
        contest = Contest.objects.get()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertContains(response, 'Export to CSV')
            self.assertContains(response, 'Regenerate ranking')

        # Check that Admin is filtered out.
        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)

            self.assertFalse(
                re.search(
                    USER_CELL_PATTERN % ('Test Admin',),
                    response.content.decode('utf-8'),
                )
            )
            self.assertNotContains(response, 'Export to CSV')
            self.assertNotContains(response, 'Regenerate ranking')

        # Ok, so now we make test_admin a regular user.
        admin = User.objects.get(username='test_admin')
        admin.is_superuser = False
        admin.save()

        self.assertTrue(self.client.login(username='test_user'))
        with fake_timezone_now(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertIn(
                'rankings/ranking_view.html', [t.name for t in response.templates]
            )
            self.assertEqual(len(response.context['choices']), 3)
            self.assertEqual(
                len(
                    re.findall(
                        USER_CELL_PATTERN % ('Test User',),
                        response.content.decode('utf-8'),
                    )
                ),
                1,
            )

            self.assertFalse(
                re.search(
                    USER_CELL_PATTERN % ('Test Admin',),
                    response.content.decode('utf-8'),
                )
            )

        with fake_timezone_now(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            expected_order = ['Test User', 'Test User 2', 'Test Admin']
            prev_pos = 0
            content = response.content.decode('utf-8')
            for user in expected_order:
                pattern = USER_CELL_PATTERN % (user,)
                pattern_match = re.search(pattern, content)
                self.assertTrue(pattern_match)
                pos = pattern_match.start()
                self.assertGreater(
                    pos, prev_pos, msg=('User %s has incorrect ' 'position' % (user,))
                )
                prev_pos = pos

            response = self.client.get(
                reverse('ranking', kwargs={'contest_id': contest.id, 'key': '1'})
            )
            self.assertEqual(
                len(
                    re.findall(
                        USER_CELL_PATTERN_LEFT % ('Test User',),
                        response.content.decode('utf-8'),
                    )
                ),
                1,
            )

        # Test visibility of links to problem statements
        contest.controller_name = (
            'oioioi.rankings.tests.StatementHiderForContestController'
        )
        contest.save()

        with fake_timezone_now(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)

            for task in VISIBLE_TASKS:
                self.assertTrue(
                    re.search(
                        task + r'\s*</a>\s*</th>', response.content.decode('utf-8')
                    )
                )

            for task in HIDDEN_TASKS:
                self.assertTrue(
                    re.search(task + r'\s*</th>', response.content.decode('utf-8'))
                )

    def test_ranking_csv_view(self):
        contest = Contest.objects.get()
        url = reverse('ranking_csv', kwargs={'contest_id': contest.id, 'key': 'c'})

        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2015, 8, 5, tzinfo=timezone.utc)):
            check_not_accessible(self, url)

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertContains(response, 'User,')
            # Check that Admin is filtered out.
            self.assertNotContains(response, 'Admin')

            expected_order = ['Test,User', 'Test,User 2']
            prev_pos = 0
            content = response.content.decode('utf-8')
            for user in expected_order:
                pattern = '%s,' % (user,)
                self.assertContains(response, user)
                pos = content.find(pattern)
                self.assertGreater(
                    pos, prev_pos, msg=('User %s has incorrect ' 'position' % (user,))
                )
                prev_pos = pos

            for task in ['zad1', 'zad2', 'zad3', 'zad3']:
                self.assertContains(response, task)

            response = self.client.get(
                reverse('ranking', kwargs={'contest_id': contest.id, 'key': '1'})
            )
            self.assertContains(response, 'zad1')
            for task in ['zad2', 'zad3', 'zad3']:
                self.assertNotContains(response, task)

    def test_invalidate_view(self):
        contest = Contest.objects.get()
        url = reverse(
            'ranking_invalidate', kwargs={'contest_id': contest.id, 'key': 'key'}
        )

        self.assertTrue(self.client.login(username='test_user'))
        with fake_time(datetime(2019, 1, 27, tzinfo=timezone.utc)):
            check_not_accessible(self, url)

        self.assertTrue(self.client.login(username='test_admin'))
        with fake_time(datetime(2019, 1, 27, tzinfo=timezone.utc)):
            ranking, _ = Ranking.objects.get_or_create(
                contest=contest, key='admin#key', needs_recalculation=False
            )
            ranking.save()
            self.assertTrue(ranking.is_up_to_date())
            recalc = choose_for_recalculation()
            self.assertIsNone(recalc)
            response = self.client.post(url, key='key')
            ranking.refresh_from_db()
            self.assertFalse(ranking.is_up_to_date())
            recalc = choose_for_recalculation()
            self.assertIsNotNone(recalc)


class MockRankingController(DefaultRankingController):
    recalculation_result = ('serialized', ['1st', '2nd', '3rd'])

    def build_ranking(self, key):
        assert key == "key"
        return self.recalculation_result


class MockRankingContestController(ProgrammingContestController):
    def ranking_controller(self):
        return MockRankingController(self.contest)


class TestRecalc(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_rounds',
        'test_ranking_data',
        'test_permissions',
    ]

    def test_empty(self):
        contest = Contest.objects.get()
        ranking, _ = Ranking.objects.get_or_create(contest=contest, key='key')
        self.assertIsNone(ranking.serialized)
        self.assertFalse(ranking.is_up_to_date())
        self.assertIsNone(ranking.recalc_in_progress)

    def test_simple_flow(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.rankings.tests.MockRankingContestController'
        contest.save()
        ranking, _ = Ranking.objects.get_or_create(contest=contest, key='key')
        ranking.save()
        self.assertFalse(ranking.is_up_to_date())
        recalc = choose_for_recalculation()
        self.assertIsNotNone(recalc)
        self.assertIsNotNone(recalc.id)
        ranking.refresh_from_db()
        self.assertFalse(ranking.is_up_to_date())
        recalculate(recalc)
        ranking.refresh_from_db()
        self.assertTrue(ranking.is_up_to_date())
        self.assertEqual(ranking.serialized, 'serialized')
        self.assertEqual(
            [page.data for page in ranking.pages.all()], ['1st', '2nd', '3rd']
        )
        self.assertEqual([page.nr for page in ranking.pages.all()], [1, 2, 3])

    def test_simple_invalidate(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.rankings.tests.MockRankingContestController'
        contest.save()
        ranking, _ = Ranking.objects.get_or_create(
            contest=contest, key='key', needs_recalculation=False
        )
        ranking.save()
        self.assertTrue(ranking.is_up_to_date())
        recalc = choose_for_recalculation()
        self.assertIsNone(recalc)
        Ranking.invalidate_contest(contest)
        ranking.refresh_from_db()
        self.assertFalse(ranking.is_up_to_date())
        recalc = choose_for_recalculation()
        self.assertIsNotNone(recalc)

    def test_invalidate_preferences_saved(self):
        # PreferencesSaved signal is sent after user changes their preferences
        # (like name), so we need to test that ranking is invalidated after
        # this signal is broadcasted
        class MockSender:
            def __init__(self):
                self.cleaned_data = {'terms_accepted': True}

        from oioioi.base.models import PreferencesSaved

        result = UserResultForProblem.objects.first()
        sender = MockSender()
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.rankings.tests.MockRankingContestController'
        contest.save()
        ranking, _ = Ranking.objects.get_or_create(
            contest=contest, key='key', needs_recalculation=False
        )
        ranking.save()
        self.assertTrue(ranking.is_up_to_date())
        recalc = choose_for_recalculation()
        self.assertIsNone(recalc)
        PreferencesSaved.send(sender, user=result.user)
        ranking.refresh_from_db()
        self.assertFalse(ranking.is_up_to_date())
        recalc = choose_for_recalculation()
        self.assertIsNotNone(recalc)

    def test_null_checking(self):
        contest = Contest.objects.get()
        ranking, _ = Ranking.objects.get_or_create(contest=contest, key='key')
        self.assertIsNone(ranking.recalc_in_progress)
        self.assertIsNone(ranking.recalc_in_progress_id)
        ranking_recalc = RankingRecalc()
        ranking_recalc.save()
        ranking.recalc_in_progress = ranking_recalc
        ranking.needs_recalculation = False
        ranking.save()
        self.assertIsNotNone(ranking.recalc_in_progress)
        self.assertIsNotNone(ranking.recalc_in_progress_id)
        ranking = Ranking.objects.get(pk=ranking.pk)
        RankingRecalc.objects.filter(pk=ranking_recalc.pk).delete()
        self.assertIsNotNone(ranking.recalc_in_progress_id)
        with self.assertRaises(RankingRecalc.DoesNotExist):
            bool(ranking.recalc_in_progress)
        self.assertFalse(ranking.is_up_to_date())


class TestRankingsdFrontend(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_rounds',
        'test_ranking_data',
        'test_permissions',
    ]

    @override_settings(MOCK_RANKINGSD=False)
    def test_first_ranking_view(self):
        contest = Contest.objects.get()
        ranking_url = reverse('ranking', kwargs={'contest_id': contest.id, 'key': '1'})
        response = self.client.get(ranking_url)

        self.assertEqual(Ranking.objects.count(), 1)
        ranking = Ranking.objects.get()
        self.assertEqual(ranking.contest.id, contest.id)
        self.assertEqual(ranking.key, 'regular#1')
        self.assertContains(response, "We're generating the ranking right now")

        response = self.client.get(ranking_url + '?page=2')
        self.assertContains(response, "You have requested a non-existent ranking page")

    @override_settings(MOCK_RANKINGSD=False)
    def test_display_ranking(self):
        contest = Contest.objects.get()
        ranking_url = reverse('ranking', kwargs={'contest_id': contest.id, 'key': '1'})
        response = self.client.get(ranking_url)

        ranking = Ranking.objects.get(key='regular#1')
        page_content = '<b>Some</b> <br/> <i>data</i>'
        RankingPage(ranking=ranking, nr=1, data=page_content + " 1").save()
        RankingPage(ranking=ranking, nr=2, data=page_content + " 2").save()
        self.assertTrue(ranking.pages.count(), 2)

        # Make sure the page includes our rendered data and that HTML
        # hasn't been escaped
        response = self.client.get(ranking_url)
        self.assertContains(response, page_content + " 1")
        response = self.client.get(ranking_url + '?page=2')
        self.assertContains(response, page_content + " 2")

        # Check if the user still can't request pages beyond available limit
        response = self.client.get(ranking_url + '?page=3')
        self.assertContains(response, "You have requested a non-existent ranking page")

    @override_settings(MOCK_RANKINGSD=False)
    def test_display_outdated(self):
        contest = Contest.objects.get()
        ranking_url = reverse('ranking', kwargs={'contest_id': contest.id, 'key': '1'})
        response = self.client.get(ranking_url)

        # Add a page to the ranking
        ranking = Ranking.objects.get(key='regular#1')
        ranking.needs_recalculation = False
        ranking.save()
        page_content = '<b>Some</b> <br/> <i>data</i>'
        RankingPage(ranking=ranking, nr=1, data=page_content).save()
        self.assertTrue(ranking.pages.count(), 1)

        outdated_msg = "The data shown in here can be slightly outdated"
        # We shouldn't tell the ranking is outdated, when it isn't
        response = self.client.get(ranking_url)
        self.assertContains(response, page_content)
        self.assertNotContains(response, outdated_msg)

        # Invalidate ranking
        pi = ProblemInstance.objects.get(pk=1)
        user = User.objects.get(username='test_user')
        contest.controller.update_user_results(user, pi)

        # Make sure we're telling people that the ranking is outdated
        response = self.client.get(ranking_url)
        self.assertContains(response, page_content)
        self.assertContains(response, outdated_msg)

        # Check if the user still can't request pages beyond available limit
        response = self.client.get(ranking_url + '?page=2')
        self.assertContains(response, "You have requested a non-existent ranking page")


class TestResultColorClassFilter(TestCase):
    def test_integer_scores(self):
        self._test_scores(10, IntegerScore)

    def test_pa_scores(self):
        self._test_scores(1, self.pa_score_factory)

    def _test_scores(self, score_multiply, score_class_factory):
        values = [0, 1, 2, 3, 5, 8, 10]
        results = ['WA', 'OK0', 'OK0', 'OK25', 'OK50', 'OK75', 'OK100']

        for value, result in zip(values, results):
            self.check_score_color(
                value * score_multiply, 'submission--' + result, score_class_factory
            )

    @staticmethod
    def pa_score_factory(int_score):
        return PAScore(IntegerScore(int_score))

    def test_empty_scores(self):
        self.assertEqual(result_color_class(''), '')
        self.assertEqual(result_color_class(None), '')

    def check_score_color(self, int_score, color_class_name, score_class_factory):
        score = score_class_factory(int_score)
        self.assertEqual(result_color_class(score), color_class_name)
