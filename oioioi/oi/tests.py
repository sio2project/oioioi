# ~*~ coding: utf-8 ~*~
import os
from datetime import datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.test.utils import override_settings
from django.utils.encoding import force_unicode
from django.utils.timezone import utc
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.handlers import update_user_results
from oioioi.contests.models import Contest, Round, ProblemInstance
from oioioi.contests.tests import SubmitFileMixin
from oioioi.contests.current_contest import ContestMode
from oioioi.participants.models import Participant
from oioioi.oi.models import Region, OIOnsiteRegistration, School, \
        OIRegistration
from oioioi.oi.management.commands import import_onsite_participants, \
        import_schools


class TestOIAdmin(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_admin_menu(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.oi.controllers.OIContestController'
        contest.save()

        self.client.login(username='test_admin')
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertIn('Schools', response.content)
        self.assertNotIn('Regions', response.content)

    def test_schools_import(self):
        filename = os.path.join(os.path.dirname(__file__), 'files',
                                'schools.csv')
        manager = import_schools.Command()
        manager.run_from_argv(['manage.py', 'import_schools', filename])
        self.assertEquals(School.objects.count(), 3)
        school = School.objects.get(postal_code='02-044')
        self.assertEquals(school.city, u'Bielsko-Biała Zdrój')


class TestOIOnsiteAdmin(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()

    def test_admin_menu(self):
        contest = Contest.objects.get()

        self.client.login(username='test_admin')
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertIn('Schools', response.content)
        self.assertIn('Regions', response.content)

    def test_regions_admin(self):
        contest = Contest.objects.get()

        r = Region(short_name='waw', name='Warszawa', contest=contest)
        r.save()

        self.client.login(username='test_admin')
        self.client.get('/c/c/')  # 'c' becomes the current contest
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
        self.client.post(url, {'post': 'yes'})
        self.assertEqual(Region.objects.count(), 0)

    def test_participants_import(self):
        contest = Contest.objects.get()

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
    fixtures = ['test_users', 'test_contest', 'test_schools']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIContestController'
        contest.save()

    def test_participants_accounts_menu(self):
        contest = Contest.objects.get()

        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertIn('Register to the contest', response.content)
        self.assertNotIn('Edit contest registration', response.content)

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user)
        p.save()

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertNotIn('Register to the contest', response.content)
        self.assertIn('Edit contest registration', response.content)

    def test_participants_unregister_forbidden(self):
        contest = Contest.objects.get()

        url = reverse('participants_unregister',
                      kwargs={'contest_id': contest.id})

        self.client.login(username='test_user')
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()
        self.assertEqual(Participant.objects.count(), 1)

        self.client.login(username='test_user')
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)
        self.assertEqual(Participant.objects.count(), 1)

    def test_participants_registration(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        url = reverse('participants_register',
                      kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertContains(response, 'Postal code')
        self.assertContains(response, 'School')
        self.assertContains(response, 'add it')

        user.first_name = 'Sir Lancelot'
        user.last_name = 'du Lac'
        user.save()
        reg_data = {
            'address': 'The Castle',
            'postal_code': '31-337',
            'city': 'Camelot',
            'phone': '000-000-000',
            'birthday_month': '5',
            'birthday_day': '25',
            'birthday_year': '1975',
            'birthplace': 'Lac',
            't_shirt_size': 'L',
            'school': '1',
            'class_type': '1LO',
            'terms_accepted': 'y',
        }

        response = self.client.post(url, reg_data)
        self.assertEquals(302, response.status_code)

        registration = OIRegistration.objects.get(participant__user=user)
        self.assertEquals(registration.address, reg_data['address'])
        self.assertEquals(registration.school.address, 'Nowowiejska 37a')

    def test_registration_with_new_school(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        url = reverse('participants_register',
            kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertContains(response, 'Postal code')
        self.assertContains(response, 'School')
        self.assertContains(response, 'add it')

        user.first_name = 'Sir Lancelot'
        user.last_name = 'du Lac'
        user.save()
        reg_data = {
            'address': 'The Castle',
            'postal_code': '31-337',
            'school': '999',
            'terms_accepted': 'y',
            '_add_school': 'add it'
        }

        response = self.client.post(url, reg_data, follow=True)
        add_school_url = reverse('add_school')
        self.assertRedirects(response, add_school_url)
        self.assertIn('oi_oiregistrationformdata', self.client.session)

        school_data = {
            'name': 'Lady of the Lake',
            'address': 'some lake',
            'postal_code': '13-337',
            'city': 'N/A',
            'province': 'mazowieckie',
            'phone': '000-000-000',
            'email': 'not.applicable@example.com',
        }

        response = self.client.post(add_school_url, school_data, follow=True)
        self.assertRedirects(response, url)
        school = School.objects.get(pk=5)
        self.assertEquals(school.name, school_data['name'])
        self.assertTrue(school.is_active)
        self.assertFalse(school.is_approved)

        self.assertContains(response, 'Postal code')
        self.assertContains(response, reg_data['address'])
        self.assertContains(response, 'selected>\n    Lady of the Lake')


class TestOIOnsiteRegistration(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()

    def test_missing_registration_model(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()

        self.assertRaises(ObjectDoesNotExist,
            lambda: getattr(p, 'registration_model'))

    def test_participants_accounts_menu(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()

        self.client.login(username='test_user')
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertNotIn('Register to the contest', response.content)
        self.assertNotIn('Edit contest registration', response.content)

    def test_participants_unregister_forbidden(self):
        contest = Contest.objects.get()

        url = reverse('participants_unregister',
                      kwargs={'contest_id': contest.id})

        self.client.login(username='test_user')
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()
        self.assertEqual(Participant.objects.count(), 1)

        self.client.login(username='test_user')
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)


class TestOIViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission']

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_contest_visibility(self):
        contest = Contest(id='visible', name='Visible Contest')
        contest.controller_name = \
                'oioioi.oi.controllers.OIContestController'
        contest.save()

        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertIn('Visible Contest', response.content)

        response = self.client.get(reverse('select_contest'))
        self.assertEqual(len(response.context['contests']), 2)
        self.assertIn('Visible Contest', response.content)

    def test_contest_access(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIContestController'
        contest.save()

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()

        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})

        self.client.login(username='test_user2')
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)

    def test_ranking_access(self):
        contest = Contest.objects.get()
        contest.controller_name = \
            'oioioi.oi.controllers.OIContestController'
        contest.save()
        round = contest.round_set.get()
        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user)
        p.save()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        with fake_time(round.results_date + timedelta(days=1)):
            self.client.login(username='test_user')
            response = self.client.get(url)
            self.assertContains(response, "No rankings available.")
            self.client.login(username='test_admin')
            response = self.client.get(url)
            self.assertContains(response, '>Test User</a>')


class TestOIOnsiteViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    @override_settings(CONTEST_MODE=ContestMode.neutral)
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

        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})

        self.client.login(username='test_user2')
        response = self.client.get(url, follow=True)
        self.assertEqual(403, response.status_code)
        # Make sure we get nice page, allowing to log out.
        self.assertNotIn('My submissions', response.content)
        self.assertIn('OIOIOI', response.content)
        self.assertIn('Log out', response.content)

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertEqual(403, response.status_code)
        # Make sure we get nice page, allowing to log out.
        self.assertNotIn('My submissions', response.content)
        self.assertIn('OIOIOI', response.content)
        self.assertIn('Log out', response.content)

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)


class TestSchoolAdding(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_schools']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIContestController'
        contest.save()

    def test_schools_similar_view(self):
        self.client.login(username='test_user')

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('schools_similar')

        response = self.client.post(url, {'city': 'Warszawa'})
        self.assertContains(response, 'LO')
        self.assertContains(response, 'Gimnazjum')
        self.assertContains(response, 'click its name')


class TestSchoolAdmin(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_schools']

    def test_schools_similar_finding(self):
        s = School.objects.all()
        self.assertTrue(s[0].is_similar(s[1]))
        self.assertTrue(s[2].is_similar(s[3]))
        self.assertTrue(s[3].is_similar(s[2]))
        self.assertFalse(s[1].is_similar(s[2]))


class TestSchoolMerging(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_schools']

    def _call_admin_merge_action(self, schools_pk_list):
        url = reverse('oioioiadmin:oi_school_changelist')
        data = {'_selected_action': schools_pk_list, 'action': 'merge_action'}
        return self.client.post(url, data, follow=True)

    def test_schools_merging_unsuccessfull(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIContestController'
        contest.save()

        user = User.objects.get(username='test_user')
        url = reverse('participants_register',
                      kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        response = self.client.get(url)

        user.first_name = 'Sir Lancelot'
        user.last_name = 'du Lac'
        user.save()
        reg_data = {
            'address': 'The Castle',
            'postal_code': '31-337',
            'city': 'Camelot',
            'phone': '000-000-000',
            'birthday_month': '5',
            'birthday_day': '25',
            'birthday_year': '1975',
            'birthplace': 'Lac',
            't_shirt_size': 'L',
            'school': '2',
            'class_type': '1LO',
            'terms_accepted': 'y',
        }

        response = self.client.post(url, reg_data)
        self.assertEquals(302, response.status_code)

        s1 = School.objects.get(pk=1)
        s2 = School.objects.get(pk=2)
        s2.is_approved = False
        s2.save()

        self.client.login(username='test_admin')

        response = self._call_admin_merge_action((1))
        self.assertContains(response, 'exactly one')

        response = self._call_admin_merge_action((2))
        self.assertContains(response, 'exactly one')

        response = self._call_admin_merge_action((1, 3))
        self.assertContains(response, 'exactly one')

        response = self._call_admin_merge_action((1, 2, 3))
        self.assertContains(response, 'exactly one')

        s2reg = OIRegistration.objects.get(participant__user=user)
        self.assertFalse(s2reg.school == s1)
        self.assertTrue(s2reg.school == s2)
        response = self._call_admin_merge_action((1, 2))
        self.assertNotContains(response, 'exactly one')
        s2reg = OIRegistration.objects.get(participant__user=user)
        self.assertTrue(s2reg.school == s1)
        self.assertFalse(s2reg.school == s2)
        self.assertTrue(s2 not in School.objects.all())


class TestOISubmit(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIContestController'
        contest.save()

    def test_submit_permissions(self):
        contest = Contest.objects.get()

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
            self.assertIn('Sorry, there are no problems', response.content)

            self.client.login(username='test_user2')
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Sorry, there are no problems', response.content)

            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertIn('Sorry, there are no problems', response.content)

            p.status = 'ACTIVE'
            p.save()

            self.client.login(username='test_user')
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)


class TestOIOnsiteSubmit(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()

    def test_submit_permissions(self):
        contest = Contest.objects.get()

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
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_submissions_CE']

    def _test(self, controller_name):
        contest = Contest.objects.get()
        contest.controller.name = controller_name
        contest.save()

        test_env = {}
        test_env['problem_instance_id'] = 1
        test_env['round_id'] = 1
        test_env['contest_id'] = contest.id

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        for i in [1, 3, 4]:
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


class TestUserInfo(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_schools',
                'test_permissions']

    def test_user_info_page(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIContestController'
        contest.save()

        user = User.objects.get(username='test_user')
        url = reverse('participants_register',
                      kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        self.client.get(url)

        user.first_name = 'Sir Lancelot'
        user.last_name = 'du Lac'
        user.save()
        reg_data = {
            'address': 'The Castle',
            'postal_code': '31-337',
            'city': 'Camelot',
            'phone': '000-000-000',
            'birthday_month': '5',
            'birthday_day': '25',
            'birthday_year': '1975',
            'birthplace': 'Lac',
            't_shirt_size': 'L',
            'school': '1',
            'class_type': '1LO',
            'terms_accepted': 'y',
        }

        response = self.client.post(url, reg_data)
        self.assertEquals(302, response.status_code)
        url = reverse('user_info', kwargs={'contest_id': contest.id,
                                           'user_id': user.id})

        reg_data['birthday_day'] = 'May 25, 1975'
        to_delete = ['school', 'birthday_month', 'birthday_year',
                     'terms_accepted']
        for k in to_delete:
            del reg_data[k]

        for k in reg_data:
            reg_data[k] = ': ' + reg_data[k]

        can_see_list = [('test_admin', True), ('test_observer', False),
                   ('test_personal_data_user', True)]

        for (username, can_see) in can_see_list:
            self.client.login(username=username)
            response = self.client.get(url)
            self.client.logout()

            for k in reg_data:
                if can_see:
                    self.assertIn(reg_data[k], response.content)
                else:
                    self.assertNotIn(reg_data[k], response.content)

    def test_oionsite_user_info_page(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.oi.controllers.OIOnsiteContestController'
        contest.save()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()
        reg = OIOnsiteRegistration(participant=p, number=3, local_number=5)
        reg.save()

        self.client.login(username='test_admin')
        url = reverse('user_info', kwargs={'contest_id': contest.id,
                                           'user_id': user.id})
        response = self.client.get(url)

        self.assertIn('<h4>OI info:</h4>', response.content)
