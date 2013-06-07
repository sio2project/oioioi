from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.contrib.auth.models import User
from oioioi.base.tests import fake_time, check_not_accessible
from oioioi.contests.models import Contest
from datetime import datetime


class TestRankingViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission', 'test_extra_rounds', 'test_ranking_data']

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
