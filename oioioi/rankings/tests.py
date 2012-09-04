from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from oioioi.base.tests import fake_time
from oioioi.contests.models import Contest
from datetime import datetime

class TestRankingViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_submission', 'test_extra_rounds', 'test_ranking_data']

    def test_ranking_view(self):
        contest = Contest.objects.get()
        self.client.login(username='test_user')

        with fake_time(datetime(2012, 8, 5, tzinfo=utc)):
            response = self.client.get(reverse('default_ranking',
                kwargs={'contest_id': contest.id}))
            self.assertIn('rankings/ranking_view.html',
                    [t.name for t in response.templates])
            self.assertEqual(len(response.context['choices']), 3)
            self.assertEqual(response.content.count('<td>Test User'), 1)
            self.assertNotIn('<td>Test Admin</td>', response.content)

        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(reverse('default_ranking',
                kwargs={'contest_id': contest.id}))
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
