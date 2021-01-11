from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.participants.models import Participant


class TestAMPPZContestController(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.amppz.controllers.AMPPZContestController'
        contest.save()

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user)
        p.save()

    def test_amppz_menu(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(
            reverse('default_contest_view', kwargs={'contest_id': contest.id}),
            follow=True,
        )
        self.assertContains(response, 'amppz/images/menu-icon')
        self.assertContains(response, 'amppz/images/logo')

    def test_safe_exec_mode(self):
        contest = Contest.objects.get()
        self.assertEqual(contest.controller.get_safe_exec_mode(), 'cpu')
