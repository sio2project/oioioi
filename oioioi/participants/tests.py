import os
from datetime import datetime
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils.timezone import utc
from django.contrib.auth.models import User
from django.core.cache import cache

from oioioi.base.tests import fake_time, check_not_accessible
from oioioi.contestexcl.models import ExclusivenessConfig
from oioioi.contestexcl.tests import ContestIdViewCheckMixin
from oioioi.contests.models import Contest, Round, ProblemInstance, \
    ContestPermission
from oioioi.contests.tests import SubmitFileMixin
from oioioi.contests.current_contest import ContestMode
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant, TestRegistration
from oioioi.participants.management.commands import import_participants
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.oi.controllers import OIContestController, OIRegistrationController
from oioioi.test_settings import MIDDLEWARE_CLASSES


basedir = os.path.dirname(__file__)


class ParticipantsContestController(ProgrammingContestController):
    def registration_controller(self):
        return ParticipantsController(self.contest)


class TestParticipantsContestViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

    @override_settings(CONTEST_MODE=ContestMode.neutral)
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

        p.status = 'ACTIVE'
        p.save()

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)


class TestParticipantsSubmit(TestCase, SubmitFileMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance']

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
        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertNotIn('Register to the contest', response.content)
        self.assertNotIn('Edit contest registration', response.content)

    def test_participants_registration(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()

        url = reverse('default_contest_view',
                      kwargs={'contest_id': contest.id})

        self.client.login(username='test_user')
        response = self.client.get(url, follow=True)

        register_url = reverse('participants_register',
                kwargs={'contest_id': contest.id})
        response = self.client.get(register_url)
        self.assertEquals(403, response.status_code)
        response = self.client.post(register_url)
        self.assertEquals(403, response.status_code)
        self.assertEqual(Participant.objects.count(), 0)

    def test_participants_unregister(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()

        url = reverse('participants_unregister',
                      kwargs={'contest_id': contest.id})

        self.client.login(username='test_user')
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()
        self.assertEqual(Participant.objects.count(), 1)

        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(403, response.status_code)
        self.assertEqual(Participant.objects.count(), 1)


class NoAdminParticipantsRegistrationController(ParticipantsController):
    @property
    def participant_admin(self):
        return None


class NoAdminParticipantsContestController(ProgrammingContestController):
    def registration_controller(self):
        return NoAdminParticipantsRegistrationController(self.contest)


class TestParticipantsModelAdmin(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_permissions']

    def test_participants_admin_visibility(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()

        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('oioioiadmin:participants_participant_changelist')
        self.client.login(username='test_user')
        check_not_accessible(self, url)

        self.client.login(username='test_contest_admin')
        response = self.client.get(url)
        self.assertContains(response, 'test_user')

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertContains(response, 'test_user')

    def test_noadmin_admin_visibility(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.' \
                'NoAdminParticipantsContestController'
        contest.save()
        user = User.objects.get(username='test_user')

        p = Participant(contest=contest, user=user)
        p.save()

        self.client.get('/c/c/')  # 'c' becomes the current contest

        url = reverse('oioioiadmin:participants_participant_changelist')
        self.client.login(username='test_user')
        check_not_accessible(self, url)

        self.client.login(username='test_admin')
        check_not_accessible(self, url)
        self.client.login(username='test_contest_admin')
        check_not_accessible(self, url)

    def test_participants_import(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()

        filename = os.path.join(basedir, 'files', 'participants.csv')
        manager = import_participants.Command()
        manager.run_from_argv(['manage.py', 'import_participants',
                               str(contest.id), filename])

        self.assertEqual(Participant.objects.count(), 2)

        p = Participant.objects.get(pk=1)
        self.assertEqual(p.status, 'ACTIVE')
        self.assertEqual(p.user.username, 'test_user')
        self.assertEqual(p.contest, contest)


@override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE_CLASSES +
    ('oioioi.contestexcl.middleware.ExclusiveContestsMiddleware',))
class TestParticipantsExclusiveContestsMiddlewareMixin(TestCase,
                                                       ContestIdViewCheckMixin
                                                       ):
    urls = 'oioioi.contests.test_urls'
    fixtures = ['test_users', 'test_two_empty_contests']

    def setUp(self):
        self.c1 = Contest.objects.get(id='c1')
        self.c2 = Contest.objects.get(id='c2')
        self.user = User.objects.get(username='test_user')

    def test_participants_selector(self):
        self.c1.controller_name = \
            'oioioi.participants.tests.ParticipantsContestController'
        self.c1.save()

        Participant(user=self.user, contest=self.c1).save()

        self.client.login(username='test_user')

        self._assertContestVisible('c1')
        self._assertContestVisible('c2')

        ex_conf = ExclusivenessConfig()
        ex_conf.contest = self.c1
        ex_conf.start_date = datetime(2012, 1, 1, 8, tzinfo=utc)
        ex_conf.end_date = datetime(2012, 1, 1, 12, tzinfo=utc)
        ex_conf.save()

        with fake_time(datetime(2012, 1, 1, 10, tzinfo=utc)):
            self._assertContestVisible('c1')
            self._assertContestRedirects('c2', '/c/c1/')
            self.client.login(username='test_user2')
            self._assertContestVisible('c2')

    def test_contest_admin_with_participant(self):
        self.c2.controller_name = \
            'oioioi.participants.tests.ParticipantsContestController'
        self.c2.save()

        ContestPermission(user=self.user, contest=self.c1,
                          permission='contests.contest_admin').save()
        Participant(user=self.user, contest=self.c2).save()

        ex_conf1 = ExclusivenessConfig()
        ex_conf1.contest = self.c1
        ex_conf1.start_date = datetime(2012, 1, 1, 8, tzinfo=utc)
        ex_conf1.end_date = datetime(2012, 1, 1, 12, tzinfo=utc)
        ex_conf1.save()
        ex_conf2 = ExclusivenessConfig()
        ex_conf2.contest = self.c2
        ex_conf2.start_date = datetime(2012, 1, 1, 8, tzinfo=utc)
        ex_conf2.end_date = datetime(2012, 1, 1, 12, tzinfo=utc)
        ex_conf2.save()

        self.client.login(username='test_user')

        with fake_time(datetime(2012, 1, 1, 10, tzinfo=utc)):
            self._assertContestVisible('c2')
            self._assertContestRedirects('c1', '/c/c2')


# This is a workaround for a django-nose bug that causes errors when
# invoking ./test.sh oioioi.participants.tests. See:
# https://github.com/django-nose/django-nose/issues/15#issuecomment-1033686
TestRegistration._meta.get_all_related_objects()


class TestRegistrationModel(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_both_hands_cascading_on_registration_delete(self):
        def _assert_equals_len(expectedLen=None):
            self.assertEquals(Participant.objects.count(),
                              TestRegistration.objects.count())
            if expectedLen:
                self.assertEquals(Participant.objects.count(), expectedLen)

        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.participants.tests.ParticipantsContestController'
        contest.save()

        reg = []

        for user in User.objects.all():
            p = Participant(contest=contest, user=user)
            p.save()
            r = TestRegistration(participant=p, name='trolololo')
            r.save()
            reg.append(r)

        _assert_equals_len(len(reg))
        reg[0].delete()
        _assert_equals_len(len(reg) - 1)
        reg[1].participant.delete()
        _assert_equals_len(len(reg) - 2)
        reg = TestRegistration.objects.filter(name='trolololo').delete()
        _assert_equals_len(0)


class AnonymousRegistrationController(OIRegistrationController):
    def allow_login_as_public_name(self):
        return True


class AnonymousContestController(OIContestController):
    def registration_controller(self):
        return AnonymousRegistrationController(self.contest)


class TestAnonymousParticipants(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_schools',
            'test_full_package', 'test_problem_instance', 'test_ranking_data',
            'test_extra_rounds', 'test_permissions']

    def _register(self, user, anonymous=False, possible=False):
        contest = Contest.objects.get()
        url = reverse('participants_register',
                      kwargs={'contest_id': contest.id})
        self.client.login(username=user.username)
        response = self.client.get(url)
        if possible:
            self.assertIn('anonymous', response.content)
        else:
            self.assertNotIn('anonymous', response.content)

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
            'anonymous': anonymous,
        }

        response = self.client.post(url, reg_data)
        self.assertIn(response.status_code, [200, 302])

    def test_no_anonymous_participants(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                "oioioi.oi.controllers.OIContestController"
        contest.save()

        u1 = User.objects.get(pk=1001)
        self._register(u1, anonymous=True, possible=False)

        contest = Contest.objects.get()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})
        self.client.login(username='test_admin')

        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertNotIn('>test_user</a>', response.content)
            self.assertIn('>Test User</a>', response.content)

    def test_anonymous_participants(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                "oioioi.participants.tests.AnonymousContestController"
        contest.save()

        u1 = User.objects.get(pk=1001)
        self._register(u1, anonymous=False, possible=True)

        u2 = User.objects.get(pk=1002)
        self._register(u2, anonymous=True, possible=True)

        contest = Contest.objects.get()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})
        self.client.login(username='test_contest_admin')

        with fake_time(datetime(2015, 8, 5, tzinfo=utc)):
            response = self.client.get(url)
            self.assertNotIn('>test_user</a>', response.content)
            self.assertIn('>Test User</a>', response.content)

            self.assertIn('>test_user2</a>', response.content)
            self.assertNotIn('>Test User 2</a>', response.content)

            # Edit contest registration
            self._register(u2, anonymous=False, possible=True)
            # To see the changes in the ranking we have to clear the cache
            cache.clear()

            self.client.login(username='test_contest_admin')
            response = self.client.get(url)
            self.assertNotIn('>test_user2</a>', response.content)
            self.assertIn('>Test User 2</a>', response.content)

    def test_user_info_page(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                "oioioi.participants.tests.ParticipantsContestController"
        contest.save()

        user = User.objects.get(pk=1001)
        p = Participant(contest=contest, user=user)
        p.save()
        url = reverse('user_info', kwargs={'contest_id': contest.id,
                                           'user_id': user.id})
        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertIn('<h4>Participant info:</h4>', response.content)


class TestParticipantsDataViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_schools']

    def register(self, contest):
        reg_url = reverse('participants_register',
                      kwargs={'contest_id': contest.id})

        self.client.get(reg_url)
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
            'anonymous': False,
        }
        self.client.post(reg_url, reg_data)

    def test_data_view(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                "oioioi.oi.controllers.OIContestController"
        contest.save()

        user = User.objects.get(username='test_user')
        url = reverse('participants_data', kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        try:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

            self.client.logout()
            perm = ContestPermission(user=user, contest=contest,
                                     permission='contests.personal_data')
            perm.save()
            if hasattr(user, '_contest_perms_cache'):
                delattr(user, '_contest_perms_cache')

            self.client.login(username='test_user')

            response = self.client.get(url)
            self.assertIn('no participants', response.content)

            self.register(contest)

            response = self.client.get(url)
            self.assertIn('<td>The Castle</td>', response.content)
            self.assertIn('<td>31-337</td>', response.content)
            self.assertIn('<td>Camelot</td>', response.content)
            self.assertIn('<td>000-000-000</td>', response.content)
            self.assertIn('<td>1975-05-25</td>', response.content)
            self.assertIn('<td>L</td>', response.content)
        finally:
            self.client.logout()

    def test_none_school(self):
        user2 = User.objects.get(username='test_user2')

        contest = Contest.objects.get()
        contest.controller_name = \
                "oioioi.oi.controllers.OIContestController"
        contest.save()

        url = reverse('participants_data', kwargs={'contest_id': contest.id})

        perm = ContestPermission(user=user2, contest=contest,
                                 permission='contests.personal_data')
        perm.save()
        if hasattr(user2, '_contest_perms_cache'):
            delattr(user2, '_contest_perms_cache')

        self.client.login(username='test_user2')

        try:
            self.register(contest)
            p_data = Participant.objects.get(user=user2).registration_model
            p_data.school = None
            p_data.save()

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        finally:
            self.client.logout()
