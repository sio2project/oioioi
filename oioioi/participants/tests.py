from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils.timezone import utc
from django.contrib.auth.models import User
from oioioi.base.tests import fake_time
from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.contests.controllers import ContestController
from oioioi.contests.tests import SubmitFileMixin
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.programs.controllers import ProgrammingContestController

from datetime import datetime

class ParticipantsContestController(ProgrammingContestController):
    def registration_controller(self):
        return ParticipantsController(self.contest)

class OpenRegistrationController(ParticipantsController):
    def anonymous_can_enter_contest(self):
        return True

    def can_enter_contest(self, request):
        return True

    def can_register(self, request):
        return True

class OpenRegistrationContestController(ContestController):
    def registration_controller(self):
        return OpenRegistrationController(self.contest)

class TestParticipantsContestViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_participants_contest_visibility(self):
        contest = Contest(id='invisible', name='Invisible Contest')
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()
        user = User.objects.get(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertIn('contests/select_contest.html',
                [t.name for t in response.templates])
        self.assertEqual(len(response.context['contests']), 1)

        self.client.login(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 1)

        p1 = Participant(contest=contest, user=user, status='BANNED')
        p1.save()
        self.client.login(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 1)

        p1.status = 'ACTIVE'
        p1.save()
        self.client.login(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)

        self.client.login(username='test_admin')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertIn('Invisible Contest', response.content)

    def test_participants_contest_access(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()


        self.client.login(username='test_user2')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertEqual(403, response.status_code)
        # Make sure we get nice page, allowing to log out.
        self.assertNotIn('My submissions', response.content)
        self.assertIn('OIOIOI', response.content)
        self.assertIn('Log out', response.content)

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertEqual(403, response.status_code)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertEqual(200, response.status_code)

class TestParticipantsSubmit(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_submit_permissions(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()

        round = Round.objects.get(pk=1)
        problem_instance = ProblemInstance.objects.get(pk=1)
        self.assertTrue(problem_instance.round == round)
        round.start_date = datetime(2012, 7, 31, tzinfo=utc)
        round.end_date = datetime(2012, 8, 5, tzinfo=utc)
        round.save()

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()

        with fake_time(datetime(2012, 8, 4, 0, 5, tzinfo=utc)):
            self.client.login(username='test_user2')
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

            p.status = 'ACTIVE'
            p.save()

            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

class TestParticipantsRegistration(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_participants_accounts_menu(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertNotIn('Register to the contest', response.content)
        self.assertIn('Edit contest registration', response.content)

    def test_participants_with_open_registration(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.OpenRegistrationContestController'
        contest.save()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertIn('Register to the contest', response.content)
        self.assertNotIn('Edit contest registration', response.content)

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user)
        p.save()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertNotIn('Register to the contest', response.content)
        self.assertIn('Edit contest registration', response.content)

    def test_participants_unregister(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.OpenRegistrationContestController'
        contest.save()

        self.client.login(username='test_user')
        response = self.client.post('/c/%s/unregister' % (contest.id,),
                                    {'post': 'yes'})
        self.assertEqual(403, response.status_code)

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()
        self.assertEqual(Participant.objects.count(), 1)

        self.client.login(username='test_user')
        response = self.client.post('/c/%s/unregister' % (contest.id,),
                                    {'post': 'yes'})
        self.assertEqual(403, response.status_code)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.post('/c/%s/unregister' % (contest.id,),
                                    {'post': 'yes'})
        self.assertEqual(302, response.status_code)
        self.assertEqual(Participant.objects.count(), 0)

