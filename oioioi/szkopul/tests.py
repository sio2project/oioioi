# coding: utf8
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

        self.assertContains(response, 'Contests')
        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

        self.assertContains(response, 'href="/contest/"')
        self.assertContains(response, 'href="/problemset/"')

    #Regression test for SIO-2278
    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navbar_links_translation(self):
        response = self.client.get(reverse('problemset_main'), follow=True, HTTP_ACCEPT_LANGUAGE='en')

        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

        response = self.client.get(reverse('problemset_main'), follow=True, HTTP_ACCEPT_LANGUAGE='pl')

        self.assertContains(response, 'Baza zadań')
        self.assertContains(response, 'Archiwum zadań')


    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_anonymous_user(self):
        try:
            response = self.client.get(reverse('index'))
        except NoReverseMatch as e:
            self.fail(str(e))

        self.assertContains(response, 'class="szkopul-logo"')


    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_logged_user(self):
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get('/', follow=True)

        self.assertContains(response, 'Contests')
        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

        self.assertContains(response, 'Latest Contests')
        self.assertContains(response, 'My Submissions')

        self.assertContains(response, 'Test contest')
        self.assertContains(response, '2012-06-03')
        self.assertContains(response, '34')


    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_user_no_submissions(self):
        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get('/', follow=True)

        self.assertContains(response, "You haven't submitted anything yet. Try entering a contest!")
