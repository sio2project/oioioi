from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.problems.models import Problem


class TestProblemsetPage(TestCase):
    fixtures = ['test_users', 'test_problemset_author_problems', 'test_contest']

    def test_problemlist(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('problemset_main')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        public_problems = Problem.objects.filter(visibility=Problem.VISIBILITY_PUBLIC)
        for problem in public_problems:
            self.assertContains(response, problem.name)
        # User with no administered contests doesn't see the button
        self.assertNotContains(response, "Add to contest")

        url = reverse('problemset_my_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        author_user = User.objects.filter(username='test_user').get()
        author_problems = Problem.objects.filter(author=author_user)
        for problem in author_problems:
            self.assertContains(response, problem.name)
        # User with no administered contests doesn't see the button
        self.assertNotContains(response, "Add to contest")
        self.assertNotContains(response, 'All problems')

        url = reverse('problemset_all_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All problems')
        # One link for problem site, another
        # for "More contests..." link in "Actions"
        self.assertContains(
            response, '/problemset/problem/', count=Problem.objects.count() * 2
        )
        self.assertContains(response, 'Add to contest', count=Problem.objects.count())


class TestAddToProblemsetPermissions(TestCase):
    fixtures = ['test_users']

    def _assert_can_see_and_add(self):
        url_main = reverse('problemset_main')
        url_add = reverse('problemset_add_or_update')

        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add problem')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 200)

    def _assert_can_see_but_cannot_add(self):
        url_main = reverse('problemset_main')
        url_add = reverse('problemset_add_or_update')

        response = self.client.get(url_main, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Add problem')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 403)

    @override_settings(EVERYBODY_CAN_ADD_TO_PROBLEMSET=False)
    def test_default_permissions(self):
        self._assert_can_see_but_cannot_add()
        self.assertTrue(self.client.login(username='test_admin'))
        self._assert_can_see_and_add()
        self.assertTrue(self.client.login(username='test_user'))
        self._assert_can_see_but_cannot_add()

    @override_settings(EVERYBODY_CAN_ADD_TO_PROBLEMSET=True)
    def test_everyone_allowed_permissions(self):
        self._assert_can_see_but_cannot_add()
        self.assertTrue(self.client.login(username='test_admin'))
        self._assert_can_see_and_add()
        self.assertTrue(self.client.login(username='test_user'))
        self._assert_can_see_and_add()


class TestAddToContestFromProblemset(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_problem_site',
    ]

    def test_add_from_problemlist(self):
        self.assertTrue(self.client.login(username='test_admin'))
        # Visit contest page to register it in recent contests
        contest = Contest.objects.get()
        self.client.get('/c/%s/dashboard/' % contest.id)
        url = reverse('problemset_all_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All problems')
        # One link for problem site, another
        # for "More contests..." link in "Actions"
        self.assertContains(
            response, '/problemset/problem/', count=Problem.objects.count() * 2
        )
        self.assertContains(response, 'Add to contest', count=Problem.objects.count())
        self.assertContains(response, 'data-addorupdate')
        self.assertContains(response, 'data-urlkey')
        self.assertContains(response, 'add_to_contest')

    def test_add_from_problemsite(self):
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        self.client.get('/c/%s/dashboard/' % contest.id)
        url = reverse('problem_site', kwargs={'site_key': '123'})
        response = self.client.get(url + '?key=settings', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add to contest', count=3)
        self.assertContains(response, 'data-addorupdate')
        self.assertContains(response, 'data-urlkey')
        self.assertContains(response, 'add_to_contest')
        self.assertContains(response, '123')

    def test_add_from_selectcontest(self):
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

        self.assertTrue(self.client.login(username='test_admin'))
        # Now we're not having any contest in recent contests.
        # As we are contest administrator, the button should still appear.
        url = reverse('problemset_all_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All problems')
        self.assertContains(
            response, '/problemset/problem/', count=Problem.objects.count() * 2
        )
        self.assertContains(response, 'Add to contest', count=Problem.objects.count())
        # But it shouldn't be able to fill the form
        self.assertNotContains(response, 'data-addorupdate')
        self.assertNotContains(response, 'data-urlkey')
        # And it should point to select_contest page
        self.assertContains(response, '/problem/123/add_to_contest/?problem_name=sum')
        # Follow the link...
        url = reverse('problemset_add_to_contest', kwargs={'site_key': '123'})
        url += '?problem_name=sum'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'to add the <code>sum</code> problem to')
        # This time we should be able to fill the form
        self.assertContains(response, 'data-addorupdate')
        self.assertContains(response, 'data-urlkey')
        self.assertContains(response, 'add_to_contest')
        self.assertContains(response, '123')
        self.assertEqual(len(response.context['administered_contests']), 4)
        self.assertEqual(
            list(response.context['administered_contests']),
            list(Contest.objects.order_by('-creation_date').all()),
        )
        self.assertContains(response, 'Contest2', count=1)
        self.assertContains(response, 'Contest3', count=1)
        self.assertContains(response, 'Contest4', count=1)
        content = response.content.decode('utf-8')
        self.assertLess(content.index('Contest3'), content.index('Contest4'))
        self.assertLess(content.index('Contest4'), content.index('Contest2'))


@override_settings(PROBLEM_STATISTICS_AVAILABLE=True)
class TestProblemsetFilters(TestCase):
    fixtures = ['test_users', 'test_statistics_display']

    problems = [u'aaa', u'bbb', u'ccc', u'ddd']
    filtered_problems = {
        'all': [u'aaa', u'bbb', u'ccc', u'ddd'],
        'solved': [u'ddd'],
        'attempted': [u'bbb', u'ccc'],
        'not_attempted': [u'aaa'],
    }

    def test_filters(self):
        self.assertTrue(self.client.login(username='test_user'))

        for filter, filtered in self.filtered_problems.items():
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'filter': filter})
            self.assertEqual(response.status_code, 200)

            for problem in self.problems:
                if problem in filtered:
                    self.assertContains(response, problem)
                else:
                    self.assertNotContains(response, problem)
