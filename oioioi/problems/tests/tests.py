# coding: utf-8

import pytest
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.base.utils.test_migrations import TestCaseMigrations
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.problems.models import (
    Problem,
    ProblemSite,
    ProblemStatement,
    make_problem_filename,
)
from oioioi.problems.tests.utilities import TestProblemController, get_test_filename
from oioioi.problemsharing.models import Friendship


class TestModels(TestCase):
    def test_problem_controller_property(self):
        problem = Problem(controller_name='oioioi.problems.tests.TestProblemController')
        self.assertIsInstance(problem.controller, TestProblemController)

    def test_make_problem_filename(self):
        p12 = Problem(pk=12)
        self.assertEqual(make_problem_filename(p12, 'a/hej.txt'), 'problems/12/hej.txt')
        ps = ProblemStatement(pk=22, problem=p12)
        self.assertEqual(make_problem_filename(ps, 'a/hej.txt'), 'problems/12/hej.txt')


class TestProblemsharing(TestCase):
    fixtures = ['test_users', 'teachers', 'test_contest']

    def test_shared_with_me_view(self):
        Problem.objects.all().delete()
        Friendship.objects.all().delete()
        ProblemSite.objects.all().delete()
        author_user = User.objects.get(username='test_user')
        teacher = User.objects.get(username='test_user2')
        Problem(
            author=author_user,
            visibility=Problem.VISIBILITY_FRIENDS,
            legacy_name='problem1',
            short_name='prob1',
            controller_name='oioioi.problems.tests.TestProblemController',
        ).save()
        self.assertEqual(Problem.objects.all().count(), 1)
        ProblemSite(
            problem=Problem.objects.get(legacy_name='problem1'),
            url_key='przykladowyurl',
        ).save()
        self.assertEqual(ProblemSite.objects.all().count(), 1)
        Friendship(
            creator=User.objects.get(username='test_user'),
            receiver=User.objects.get(username='test_user2'),
        ).save()
        self.assertEqual(Friendship.objects.all().count(), 1)
        self.assertTrue(self.client.login(username='test_user2'))
        url = reverse('problemset_shared_with_me')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        friends = Friendship.objects.filter(receiver=teacher).values_list(
            'creator', flat=True
        )
        self.assertEqual(friends.count(), 1)
        problems = Problem.objects.filter(
            visibility=Problem.VISIBILITY_FRIENDS,
            author__in=friends,
            problemsite__isnull=False,
        )
        self.assertEqual(problems.count(), 1)
        for problem in problems:
            self.assertContains(response, problem.name)
        # User with no administered contests doesn't see the button
        self.assertNotContains(response, "Add to contest")

    def test_visibility_field_present(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('problemset_add_or_update')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visibility")
        self.assertContains(response, "Add problem")

    def test_visibility_default_preference(self):
        Problem.objects.all().delete()
        ProblemSite.objects.all().delete()
        ProblemInstance.objects.all().delete()

        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].initial['visibility'], Problem.VISIBILITY_FRIENDS
        )

        filename = get_test_filename('test_simple_package.zip')
        user = User.objects.filter(username='test_admin').first()
        url = response.redirect_chain[-1][0]
        self.assertIn(
            'problems/add-or-update.html',
            [getattr(t, 'name', None) for t in response.templates],
        )
        response = self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': Problem.VISIBILITY_PRIVATE,
                'user': user,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 2)

        problem = (
            Problem.objects.filter(contest=contest, author=user).order_by('-id').first()
        )
        self.assertEqual(problem.visibility, Problem.VISIBILITY_PRIVATE)

        # now the last uploaded problem (for this contest)
        # has private visibility, so the form.initial['visibility'] should be set to private too
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].initial['visibility'], Problem.VISIBILITY_PRIVATE
        )


class TestNavigationBarItems(TestCase):
    fixtures = ['test_users']

    def test_navigation_bar_items_anonymous(self):
        url_main = reverse('problemset_main')

        response = self.client.get(url_main, follow=True)
        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

    # Regression test for SIO-2278
    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navigation_bar_items_translation(self):
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

    def test_navigation_bar_items_admin(self):
        url_main = reverse('problemset_main')
        url_my = reverse('problemset_my_problems')
        url_all = reverse('problemset_all_problems')
        url_add = reverse('problemset_add_or_update')

        self.assertTrue(self.client.login(username='test_admin'))

        for url in [url_main, url_my, url_all, url_add]:
            response = self.client.get(url, follow=True)
            self.assertContains(response, 'Problemset')
            self.assertContains(response, 'Task archive')


@pytest.mark.skip(reason="Migrations have already been applied at the production")
class TestVisibilityMigration(TestCaseMigrations):
    migrate_from = '0013_newtags'
    migrate_to = '0016_visibility_part3'

    def setUpBeforeMigration(self, apps):
        Problem = apps.get_model('problems', 'Problem')
        self.public_problem_id = Problem.objects.create(is_public=True).id
        self.private_problem_id = Problem.objects.create(is_public=False).id

    def test(self):
        self.assertEqual(
            Problem.objects.get(id=self.public_problem_id).visibility,
            Problem.VISIBILITY_PUBLIC,
        )
        self.assertEqual(
            Problem.objects.get(id=self.private_problem_id).visibility,
            Problem.VISIBILITY_FRIENDS,
        )


@pytest.mark.skip(reason="Migrations have already been applied at the production")
class TestVisibilityMigrationReverse(TestCaseMigrations):
    migrate_from = '0016_visibility_part3'
    migrate_to = '0013_newtags'

    def setUpBeforeMigration(self, apps):
        Problem = apps.get_model('problems', 'Problem')
        self.public_problem_id = Problem.objects.create(visibility='PU').id
        self.friends_problem_id = Problem.objects.create(visibility='FR').id
        self.private_problem_id = Problem.objects.create(visibility='PR').id

    def test(self):
        Problem = self.apps.get_model('problems', 'Problem')
        self.assertEqual(Problem.objects.get(id=self.public_problem_id).is_public, True)
        self.assertEqual(
            Problem.objects.get(id=self.friends_problem_id).is_public, False
        )
        self.assertEqual(
            Problem.objects.get(id=self.private_problem_id).is_public, False
        )
