from datetime import datetime

from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.contrib.auth.models import User
from django.http import QueryDict
from django.conf import settings

from oioioi.base.tests import TestCase, fake_time, check_not_accessible
from oioioi.contests.models import Contest, UserResultForProblem, \
        ProblemInstance
from oioioi.programs.controllers import ProgrammingContestController


VISIBLE_TASKS = ["zad1", "zad2"]
HIDDEN_TASKS = ["zad3", "zad4"]


class StatementHiderForContestController(ProgrammingContestController):
    def default_can_see_statement(self, request, problem_instance):
        return problem_instance.short_name in VISIBLE_TASKS


class TestRankingViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_extra_rounds',
            'test_ranking_data', 'test_permissions']

    @override_settings(PARTICIPANTS_ON_PAGE=3)
    def test_find_user(self):
        number_of_users = 7  # this test will create that number of users
        per_page = settings.PARTICIPANTS_ON_PAGE
        contest = Contest.objects.get()
        pis = ProblemInstance.objects.get(id=1)

        UserResultForProblem.objects.all().delete()

        # Creates user and adds him a score for problem pis
        def create_score(username, score):
            user = User.objects.create_user(username, username + '@example.pl',
                                            username)
            result = UserResultForProblem()
            result.user = user
            result.problem_instance = pis
            result.status = 'OK'
            result.score = 'int:%s' % score
            result.save()
            return user

        # Recently created users
        users = []

        # Create all users with scores 0..number_of_users-1
        for i in xrange(number_of_users):
            users.append(create_score('find_user_generated%s' % i, i))

        self.client.login(username='test_contest_admin')

        url = reverse('ranking', kwargs={'contest_id': contest.id,
                                         'key': pis.round.id})

        def get_url_for_user(username):
            get = QueryDict('', mutable=True)
            get['user'] = username
            get['page'] = 1
            return url + '?' + get.urlencode()

        def get_url_found_user(user, page):
            get = QueryDict('', mutable=True)
            get['page'] = page
            return url + '?' + get.urlencode() + '#' + str(user.id)

        user_not_in_ranking = User.objects.get(username='test_user')
        response = self.client.get(
                get_url_for_user(user_not_in_ranking.username))
        self.assertIn('User is not in the ranking.', response.content)

        response = self.client.get(get_url_for_user('not_existing_username'))
        self.assertIn('User not found', response.content)

        # Contest admin shouldn't see 'Find my position' button
        self.assertNotIn('<span class="toolbar-button-text">' +
                         'Find my place</span>', response.content)

        for i in xrange(number_of_users):
            user = users[i]
            response = self.client.get(get_url_for_user(user.username))
            # On which page should the user be?
            page = ((number_of_users - 1 - i) // per_page) + 1
            self.assertRedirects(response, get_url_found_user(user, page))

        # Login as someone who is in the ranking
        user_num = 6  # a users list index
        self.client.login(username=users[user_num].username)
        response = self.client.get(
                get_url_for_user(user_not_in_ranking.username))
        self.assertNotIn('User is not in the ranking.', response.content)
        # Normal user shouldn't see the form
        self.assertNotIn('<div class="search-for-user">', response.content)
        # Normal user should see 'Find my position' button
        self.assertIn('<span class="toolbar-button-text">' +
                      'Find my place</span>', response.content)

        # Test if users[0] can find himself
        response = self.client.get(get_url_for_user(users[user_num].username))
        page = ((number_of_users - user_num) // per_page) + 1
        self.assertRedirects(response, get_url_found_user(users[user_num],
                                                          page))

        for i in xrange(number_of_users):
            if i == user_num:
                continue
            user = users[i]
            response = self.client.get(get_url_for_user(user.username))
            # Checking if user wasn't redirected (is on page 1)
            # User with the highest score should be visible
            self.assertIn('<tr id="ranking_row_%s"' % users[-1].id,
                          response.content)

    def test_ranking_view(self):
        contest = Contest.objects.get()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        self.client.login(username='test_admin')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertContains(response, 'Export to CSV')

        # Check that Admin is filtered out.
        self.client.login(username='test_user')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertNotIn('<td>Test Admin</td>', response.content)
            self.assertNotContains(response, 'Export to CSV')

        # Ok, so now we make test_admin a regular user.
        admin = User.objects.get(username='test_admin')
        admin.is_superuser = False
        admin.save()

        self.client.login(username='test_user')
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertIn('rankings/ranking_view.html',
                    [t.name for t in response.templates])
            self.assertEqual(len(response.context['choices']), 3)
            self.assertEqual(response.content.count('<td>Test User'), 1)
            self.assertNotIn('<td>Test Admin</td>', response.content)

        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            expected_order = ['Test User', 'Test User 2', 'Test Admin']
            prev_pos = 0
            for user in expected_order:
                pattern = '<td>%s</td>' % (user,)
                self.assertIn(user, response.content)
                pos = response.content.find(pattern)
                self.assertGreater(pos, prev_pos, msg=('User %s has incorrect '
                    'position' % (user,)))
                prev_pos = pos

            response = self.client.get(reverse('ranking',
                kwargs={'contest_id': contest.id, 'key': '1'}))
            self.assertEqual(response.content.count('<td>Test User'), 1)

        # Test visibility of links to problem statements
        contest.controller_name = \
            'oioioi.rankings.tests.StatementHiderForContestController'
        contest.save()

        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)

            for task in VISIBLE_TASKS:
                self.assertIn(task + '</a></th>', response.content)

            for task in HIDDEN_TASKS:
                self.assertIn(task + '</th>', response.content)

    def test_ranking_csv_view(self):
        contest = Contest.objects.get()
        url = reverse('ranking_csv', kwargs={'contest_id': contest.id,
                                            'key': 'c'})

        self.client.login(username='test_user')
        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            check_not_accessible(self, url)

        self.client.login(username='test_admin')
        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertContains(response, 'User,')
            # Check that Admin is filtered out.
            self.assertNotContains(response, 'Admin')

            expected_order = ['Test,User', 'Test,User 2']
            prev_pos = 0
            for user in expected_order:
                pattern = '%s,' % (user,)
                self.assertIn(user, response.content)
                pos = response.content.find(pattern)
                self.assertGreater(pos, prev_pos, msg=('User %s has incorrect '
                       'position' % (user,)))
                prev_pos = pos

            for task in ['zad1', 'zad2', 'zad3', 'zad3']:
                self.assertContains(response, task)

            response = self.client.get(reverse('ranking',
                kwargs={'contest_id': contest.id, 'key': '1'}))
            self.assertContains(response, 'zad1')
            for task in ['zad2', 'zad3', 'zad3']:
                self.assertNotContains(response, task)
