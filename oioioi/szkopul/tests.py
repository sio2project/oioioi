# coding: utf-8
from __future__ import print_function

from datetime import datetime

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import NoReverseMatch, reverse

from oioioi.base.main_page import unregister_main_page_view
from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import ProblemInstance, Submission
from oioioi.problems.models import Problem
from oioioi.welcomepage.views import welcome_page_view


class TestMainPageView(TestCase):

    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def setUp(self):
        super(TestMainPageView, self).setUp()
        unregister_main_page_view(welcome_page_view)

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navbar_links(self):
        try:
            response = self.client.get('/', follow=True)
        except NoReverseMatch as e:
            self.fail(str(e))

        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

        self.assertContains(response, 'href="/problemset/"')
        self.assertContains(response, 'href="/task_archive/"')

    # Regression test for SIO-2278
    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navbar_links_translation(self):
        response = self.client.get(
            reverse('problemset_main'), follow=True, headers={"accept-language": 'en'}
        )

        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

        response = self.client.get(
            reverse('problemset_main'), follow=True, headers={"accept-language": 'pl'}
        )

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
        self.assertContains(response, '06-03')
        self.assertContains(response, '34')

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_order_in_last_submissions(self):
        # Provides some assertion that submissions will be sorted by date
        # in a descending order.

        self.assertTrue(self.client.login(username='test_user'))

        early_date = datetime.strptime("2012-06-01", "%Y-%m-%d")
        mid_date = datetime.strptime("2012-06-02", "%Y-%m-%d")

        test_problem = Problem.objects.get(pk=1)
        contestless_instance = test_problem.main_problem_instance

        test_user = User.objects.get(username='test_user')
        test_probleminstance = ProblemInstance.objects.get(pk=1)
        Submission(
            problem_instance=test_probleminstance, user=test_user, date=early_date
        ).save()

        Submission(
            problem_instance=contestless_instance,
            problem_instance_id=contestless_instance.id,
            user=test_user,
            date=mid_date,
        ).save()

        response = self.client.get('/', follow=True)

        # Cut off part of the response that is above submission table because
        # it can provide irrelevant noise.
        content = response.content.decode('utf-8')
        table_content = content[content.index('My Submissions') :]

        self.assertIn("06-01", table_content)
        self.assertIn("06-02", table_content)
        self.assertIn("06-03", table_content)

        test_early_index = table_content.index("06-01")
        test_mid_index = table_content.index("06-02")
        test_late_index = table_content.index("06-03")

        self.assertEqual(test_late_index < test_mid_index, True)
        self.assertEqual(test_mid_index < test_early_index, True)

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_user_no_submissions(self):
        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get('/', follow=True)

        self.assertContains(
            response, "You haven't submitted anything yet. Try entering a contest!"
        )
