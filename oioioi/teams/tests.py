from datetime import datetime

from django.test import RequestFactory
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.utils.timezone import utc
from django.contrib.auth.models import User

from oioioi.contests.models import Contest, ProblemInstance, Submission
from oioioi.programs.tests import SubmitFileMixin
from oioioi.teams.models import TeamsConfig
from oioioi.base.tests import TestCase, fake_time
from oioioi.teams.utils import can_join_team, can_quit_team, can_delete_team, \
                               can_create_team
from oioioi.teams.views import create_team
from oioioi.teams.models import TeamMembership


class TestTeamsViews(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    def test_permissions(self):
        contest = Contest.objects.get()
        tconf = TeamsConfig(contest=contest,
            modify_begin_date=datetime(2012, 1, 1, 8, tzinfo=utc),
            modify_end_date=datetime(2012, 1, 1, 12, tzinfo=utc),
            enabled=True)
        tconf.save()

        user = User.objects.get(username='test_user')

        factory = RequestFactory()
        request = factory.request()
        request.contest = contest
        request.user = user

        timestamp = datetime(2012, 1, 1, 10, tzinfo=utc)
        with fake_time(timestamp):
            request.timestamp = timestamp
            self.assertEqual(contest.controller.can_modify_team(request), True)
            self.assertEqual(can_join_team(request), True)
            self.assertEqual(can_quit_team(request), False)
            self.assertEqual(can_delete_team(request), False)
            self.assertEqual(can_create_team(request), True)
            team = create_team('test_team', 'Super Team!', contest)
            tm = TeamMembership(team=team, user=user)
            tm.save()
            self.assertEqual(can_join_team(request), False)
            self.assertEqual(can_quit_team(request), False)
            self.assertEqual(can_delete_team(request), True)
            self.assertEqual(can_create_team(request), False)
            user2 = User.objects.get(username='test_user2')
            tm = TeamMembership(team=team, user=user2)
            tm.save()
            self.assertEqual(can_join_team(request), False)
            self.assertEqual(can_quit_team(request), True)
            self.assertEqual(can_delete_team(request), False)
            self.assertEqual(can_create_team(request), False)

            self.client.login(username='test_user')
            problem_instance = ProblemInstance.objects.get()
            self.submit_file(contest, problem_instance, user=team.user)
            self.assertEqual(can_quit_team(request), False)

    def test_views(self):
        contest = Contest.objects.get()
        tconf = TeamsConfig(contest=contest,
            modify_begin_date=datetime(2012, 1, 1, 8, tzinfo=utc),
            modify_end_date=datetime(2012, 1, 1, 12, tzinfo=utc),
            enabled=True)
        tconf.save()

        timestamp = datetime(2012, 1, 1, 10, tzinfo=utc)
        with fake_time(timestamp):
            self.client.login(username='test_user')
            response = self.client.get(reverse('default_contest_view',
                              kwargs={'contest_id': contest.id}), follow=True)
            self.assertIn('Team', response.content)

            response = self.client.get(reverse('team_view',
                              kwargs={'contest_id': contest.id}), follow=True)
            self.assertIn('Create a team', response.content)

            user = User.objects.get(username='test_user')
            team = create_team('test_team', 'Super Team!', contest)
            tm = TeamMembership(team=team, user=user)
            tm.save()

            response = self.client.get(reverse('team_view',
                              kwargs={'contest_id': contest.id}), follow=True)
            self.assertIn('Super Team!', response.content)
            self.assertIn('delete the team', response.content)

            user2 = User.objects.get(username='test_user2')
            tm = TeamMembership(team=team, user=user2)
            tm.save()

            response = self.client.get(reverse('team_view',
                              kwargs={'contest_id': contest.id}), follow=True)
            self.assertIn('Super Team!', response.content)
            self.assertIn('Leave the team', response.content)


class TestTeamSubmit(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    def test_submit_file_without_team(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        problem_instance = ProblemInstance.objects.get()

        self.client.login(username='test_user')
        self.submit_file(contest, problem_instance, user=user)

        self.assertEqual(Submission.objects.get().user, user)

    def test_submit_file_with_team(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        problem_instance = ProblemInstance.objects.get()

        team = create_team('test_team', 'Super Team!', contest)
        tm = TeamMembership(team=team, user=user)
        tm.save()

        self.client.login(username='test_user')

        response = self.submit_file(contest, problem_instance, user=user)
        self.assertIn('You can&#39;t submit a solution for another team!',
                      response.content)

        response = self.submit_file(contest, problem_instance, user=team.user)
        self.assertEqual(Submission.objects.get().user, team.user)

    def test_submit_file_with_team_deleted(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        problem_instance = ProblemInstance.objects.get()

        team = create_team('test_team', 'Super Team!', contest)
        tm = TeamMembership(team=team, user=user)
        tm.save()

        self.client.login(username='test_user')
        url = reverse('submit', kwargs={'contest_id': contest.id})

        file = ContentFile('a' * 1024, name='submission.cpp')
        post_data = {
            'problem_instance_id': problem_instance.id,
            'file': file,
            'kind': 'NORMAL',
            'user': team.user, }

        tm.delete()
        self.client.post(url, post_data)
        self.assertEqual(Submission.objects.get().user, user)


class TestTeamsListView(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_team']

    def test_visibility_no(self):
        contest = Contest.objects.get()
        tconf = TeamsConfig(contest=contest,
            enabled=True, teams_list_visible='NO')
        tconf.save()

        response = self.client.get(reverse('default_contest_view',
                kwargs={'contest_id': contest.id}), follow=True)
        self.assertNotIn('Teams', response.content)

        self.client.login(username='test_user')

        response = self.client.get(reverse('default_contest_view',
                kwargs={'contest_id': contest.id}), follow=True)
        self.assertNotIn('Teams', response.content)

    def test_visibility_yes(self):
        contest = Contest.objects.get()
        tconf = TeamsConfig(contest=contest,
            enabled=True, teams_list_visible='YES')
        tconf.save()

        response = self.client.get(reverse('default_contest_view',
                kwargs={'contest_id': contest.id}), follow=True)
        self.assertNotIn('Teams', response.content)

        self.client.login(username='test_user')

        response = self.client.get(reverse('default_contest_view',
                kwargs={'contest_id': contest.id}), follow=True)
        self.assertIn('Teams', response.content)

    def test_visibility_public(self):
        contest = Contest.objects.get()
        tconf = TeamsConfig(contest=contest,
            enabled=True, teams_list_visible='PUBLIC')
        tconf.save()

        response = self.client.get(reverse('default_contest_view',
                kwargs={'contest_id': contest.id}), follow=True)
        self.assertIn('Teams', response.content)

        self.client.login(username='test_user')

        response = self.client.get(reverse('default_contest_view',
                kwargs={'contest_id': contest.id}), follow=True)
        self.assertIn('Teams', response.content)

    def test_list(self):
        contest = Contest.objects.get()
        tconf = TeamsConfig(contest=contest,
            enabled=True, teams_list_visible='PUBLIC')
        tconf.save()

        response = self.client.get(reverse('teams_list',
                kwargs={'contest_id': contest.id}), follow=True)

        self.assertIn('test_team', response.content)
        self.assertIn('Test Team1', response.content)
        self.assertIn('Test Team2', response.content)
