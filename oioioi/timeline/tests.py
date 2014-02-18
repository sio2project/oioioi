from django.core.urlresolvers import reverse
from django.test import TestCase

from oioioi.base.tests import check_not_accessible
from oioioi.contests.date_registration import date_registry
from oioioi.contests.models import Contest, Round


class TestTimelineView(TestCase):
    fixtures = ['test_contest', 'test_users']

    def test_response(self):
        contest = Contest.objects.get()
        url = reverse('timeline_view')

        self.client.login(username='test_user')
        check_not_accessible(self, url)

        self.client.login(username='test_admin')
        response = self.client.get(url, {'contest': contest})

        self.assertEqual(response.status_code, 200)

        for round in Round.objects.filter(contest=contest.id).values():
            self.assertIn(round['start_date'].strftime('%Y-%m-%d %H:%M:%S'),
                          response.content)

    def test_menu(self):
        contest = Contest.objects.get()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertNotIn('Timeline', response.content)

        self.client.login(username='test_admin')
        response = self.client.get('/c/%s/dashboard/' % contest.id)
        self.assertIn('Timeline', response.content)


class TestDateRegistry(TestCase):
    fixtures = ['test_contest']

    def test_registry_content(self):
        contest = Contest.objects.get()
        registry_length = len(date_registry.tolist(contest.id))
        rounds_count = Round.objects.filter(contest=contest.id).count()

        self.assertEqual(registry_length, 3 * rounds_count)
