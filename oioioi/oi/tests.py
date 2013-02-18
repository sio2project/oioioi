from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from django.utils.encoding import force_unicode
from django.utils.timezone import utc
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from oioioi.base.tests import fake_time
from oioioi.contests.handlers import update_user_results
from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.contests.tests import SubmitFileMixin
from oioioi.participants.models import Participant
from oioioi.oi.models import Region, OIOnsiteRegistration, School
from oioioi.oi.management.commands import import_onsite_participants, \
        import_schools

from datetime import datetime
import os

class TestOIAdmin(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_admin_menu(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()

        self.client.login(username='test_admin')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertIn('Schools', response.content)
        self.assertNotIn('Regions', response.content)

    def test_schools_import(self):
        filename = os.path.join(os.path.dirname(__file__), 'files',
                                'schools.csv')
        manager = import_schools.Command()
        manager.run_from_argv(['manage.py', 'import_schools', filename])
        self.assertEqual(School.objects.count(), 3)

class TestOIOnsiteAdmin(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_admin_menu(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()

        self.client.login(username='test_admin')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertIn('Schools', response.content)
        self.assertIn('Regions', response.content)

    def test_regions_admin(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()

        r = Region(short_name='waw', name='Warszawa', contest=contest)
        r.save()

        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:oi_region_changelist')
        response = self.client.get(url)
        elements_to_find = ['Short name', 'Name', 'waw', 'Warszawa']
        for element in elements_to_find:
            self.assertIn(element, response.content)

        url = reverse('oioioiadmin:oi_region_change', args=(r.id,))
        response = self.client.get(url)
        elements_to_find = ['Change region', 'waw', 'Warszawa']
        for element in elements_to_find:
            self.assertIn(element, response.content)

        url = reverse('oioioiadmin:oi_region_delete', args=(r.id,))
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(Region.objects.count(), 0)

    def test_participants_import(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()

        r = Region(short_name='waw', name='Warszawa', contest=contest)
        r.save()

        filename = os.path.join(os.path.dirname(__file__), 'files',
                                'onsite_participants.csv')
        manager = import_onsite_participants.Command()
        manager.run_from_argv(['manage.py', 'import_onsite_participants',
                               str(contest.id), filename])
        self.assertEqual(Participant.objects.count(), 3)
        self.assertEqual(OIOnsiteRegistration.objects.count(), 3)

        p = Participant.objects.get(pk=1)
        self.assertEqual(p.status, 'ACTIVE')
        self.assertEqual(force_unicode(p.registration_model), '1/waw/1')

class TestOIRegistration(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_participants_accounts_menu(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
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
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()

        self.client.login(username='test_user')
        response = self.client.post('/c/%s/unregister' % (contest.id,),
                                    {'post': 'yes'})
        self.assertEqual(404, response.status_code)

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

class TestOIOnsiteRegistration(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_missing_registration_model(self):
        contest = Contest.objects.get()
        contest.controller_name = \
            'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()

        self.assertRaises(ObjectDoesNotExist,
            lambda: getattr(p, 'registration_model'))


    def test_participants_accounts_menu(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertNotIn('Register to the contest', response.content)
        self.assertNotIn('Edit contest registration', response.content)

    def test_participants_unregister(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()

        self.client.login(username='test_user')
        response = self.client.post('/c/%s/unregister' % (contest.id,),
                                    {'post': 'yes'})
        self.assertEqual(404, response.status_code)

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
        self.assertEqual(403, response.status_code)

class TestOIViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_contest_visibility(self):
        contest = Contest(id='visible', name='Visible Contest')
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()

        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertIn('Visible Contest', response.content)

        user = User.objects.get(username='test_user')
        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertIn('Visible Contest', response.content)

    def test_contest_access(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()

        self.client.login(username='test_user2')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertEqual(200, response.status_code)

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertEqual(200, response.status_code)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertEqual(200, response.status_code)

class TestOIOnsiteViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_contest_visibility(self):
        contest = Contest(id='invisible', name='Invisible Contest')
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
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

    def test_contest_access(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
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
        # Make sure we get nice page, allowing to log out.
        self.assertNotIn('My submissions', response.content)
        self.assertIn('OIOIOI', response.content)
        self.assertIn('Log out', response.content)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.get('/c/%s/' % (contest.id,), follow=True)
        self.assertEqual(200, response.status_code)

class TestOISubmit(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_submit_permissions(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
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
            self.client.logout()
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)

            self.client.login(username='test_user2')
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)

            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Select a valid choice.', response.content)

            p.status = 'ACTIVE'
            p.save()

            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

class TestOIOnsiteSubmit(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_submit_permissions(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
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
            self.client.logout()
            response = self.submit_file(contest, problem_instance)
            self._assertNotSubmitted(contest, response)

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

class TestIgnoringCE(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_submission',
        'test_submissions_CE']

    def _test(self, controller_name):
        contest = Contest.objects.get()
        contest.controller.name = controller_name
        contest.save()

        test_env = {}
        test_env['problem_instance_id'] = 1
        test_env['round_id'] = 1
        test_env['contest_id'] = contest.id

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        for i in range(1,3):
            test_env['submission_id'] = i
            update_user_results(test_env)

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertIn('Test User', response.content)
        self.assertNotIn('Test User 2', response.content)
        self.assertIn('34', response.content)

    def test_all_oi_style_contests(self):
        self._test('oioioi.oi.controllers.OIContestController')
        self._test('oioioi.oi.controllers.OIOnsiteContestController')

