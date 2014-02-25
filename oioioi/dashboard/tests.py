from django.test import TestCase
from django.core.urlresolvers import reverse
from oioioi.contests.models import Contest


class TestDashboardMessage(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_templates']

    def test_adding_message(self):
        # Add a dashboard message
        self.client.login(username='test_admin')
        contest = Contest.objects.get()
        url = reverse('dashboard_message_edit',
                kwargs={'contest_id': contest.id})
        post_data = {
                'content': 'Test dashboard message',
            }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        # Check if message is visible
        self.client.login(username='test_user2')
        url = reverse('contest_dashboard',
                kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertIn('Test dashboard message', response.content)
