from __future__ import print_function

from django.test.utils import override_settings
from django.core.urlresolvers import NoReverseMatch, reverse

from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import ContestMode


class TestMainPageView(TestCase):

    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_submission']

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navbar_links(self):
        try:
            response = self.client.get('/', follow=True)
        except NoReverseMatch as e:
            self.fail(str(e))

        self.assertIn('Contests', response.content)
        self.assertIn('Problemset', response.content)
        self.assertIn('Task archive', response.content)

        self.assertIn('href="/contest/"', response.content)
        self.assertIn('href="/problemset/"', response.content)


    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_anonymous_user(self):
        try:
            response = self.client.get(reverse('index'))
        except NoReverseMatch as e:
            self.fail(str(e))

        self.assertIn('class="szkopul-logo"', response.content)


    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_logged_user(self):
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get('/', follow=True)

        self.assertIn('Contests', response.content)
        self.assertIn('Problemset', response.content)
        self.assertIn('Task archive', response.content)

        self.assertIn('Latest Contests', response.content)
        self.assertIn('My Submissions', response.content)

        self.assertIn('Test contest', response.content)
        self.assertIn('2012-06-03', response.content)
        self.assertIn('34', response.content)


    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_user_no_submissions(self):
        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get('/', follow=True)

        self.assertIn("You haven't submitted anything yet. Try entering a contest!", response.content)
