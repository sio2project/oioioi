# pylint: disable=maybe-no-member
from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import Contest
from oioioi.participants.models import Participant
from oioioi.su import SU_BACKEND_SESSION_KEY, SU_UID_SESSION_KEY, SU_REAL_USER_IS_SUPERUSER, SU_ORIGINAL_CONTEST
from oioioi.su.utils import get_user, su_to_user


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestSwitchingUsers(TestCase):
    fixtures = ['test_users']

    def test_switching_users(self):
        test_user = User.objects.get(username='test_user')
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(reverse('su'))
        self.assertEqual(405, response.status_code)

        response = self.client.post(
            reverse('su'),
            {
                'user': 'test_user',
                'backend': 'django.contrib.auth.backends.ModelBackend',
            },
        )
        self.assertEqual(302, response.status_code)
        session = self.client.session
        self.assertEqual(test_user.id, session[SU_UID_SESSION_KEY])
        self.assertEqual(
            'django.contrib.auth.backends.ModelBackend', session[SU_BACKEND_SESSION_KEY]
        )

        response = self.client.get(reverse('index'), follow=True)
        self.assertContains(response, 'test_user')
        self.assertContains(response, 'Back to admin')
        self.assertEqual('test_user', response.context['user'].username)
        self.assertEqual(
            'django.contrib.auth.backends.ModelBackend',
            response.context['user'].backend,
        )
        self.assertEqual('test_admin', response.context['real_user'].username)
        self.assertEqual(
            'oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend,
        )

        # Being superuser at real privileges isn't enough
        response = self.client.post(
            reverse('su'),
            {
                'user': 'test_user2',
                'backend': 'django.contrib.auth.backends.ModelBackend',
            },
        )
        self.assertEqual(403, response.status_code)
        self.assertEqual('test_user', response.context['user'].username)
        self.assertEqual(
            'django.contrib.auth.backends.ModelBackend',
            response.context['user'].backend,
        )
        self.assertEqual('test_admin', response.context['real_user'].username)
        self.assertEqual(
            'oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend,
        )

        response = self.client.post(reverse('su_reset'))
        self.assertEqual(302, response.status_code)
        session = self.client.session
        self.assertNotIn(SU_UID_SESSION_KEY, session)
        self.assertNotIn(SU_BACKEND_SESSION_KEY, session)

        response = self.client.get(reverse('index'), follow=True)
        self.assertContains(response, 'django.contrib.auth.backends.ModelBackend')
        self.assertEqual('test_admin', response.context['user'].username)
        self.assertEqual(
            'oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['user'].backend,
        )
        self.assertEqual('test_admin', response.context['real_user'].username)
        self.assertEqual(
            'oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend,
        )
        self.assertContains(response, 'Login as user')

    def test_forbidden_su(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.post(reverse('su'), {'user': 'test_admin2'})
        self.assertEqual(200, response.status_code)
        self.assertEqual('test_admin', response.context['user'].username)

        self.client.login(username='test_admin')
        response = self.client.post(reverse('su'), {'user': 'test_user_inactive'})
        self.assertEqual(200, response.status_code)
        self.assertEqual('test_admin', response.context['user'].username)

        response = self.client.post(
            reverse('su'),
            data={'user': 'test_user', 'next': 'http://enemy.example.com/'},
        )
        self.assertEqual(302, response.status_code)
        self.assertNotIn('enemy', response['Location'])

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEqual(403, response.status_code)
        self.assertEqual('test_user', response.context['user'].username)
        self.assertEqual(
            'oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['user'].backend,
        )
        self.assertEqual('test_user', response.context['real_user'].username)
        self.assertEqual(
            'oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend,
        )

    def test_su_redirection(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.post(
            reverse('su'),
            {
                'user': 'test_user',
                'backend': 'django.contrib.auth.backends.ModelBackend',
            },
        )
        self.assertEqual(302, response.status_code)

        response = self.client.get(reverse('index'), follow=True)
        self.assertEqual(200, response.status_code)
        self.client.post(reverse('su_reset'))

        response = self.client.post(
            reverse('su'),
            {
                'user': 'test_user',
                'backend': 'django.contrib.auth.backends.ModelBackend',
            },
        )
        self.assertEqual(302, response.status_code)

        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEqual(302, response.status_code)
        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEqual(403, response.status_code)
        self.client.post(reverse('su_reset'))

        response = self.client.post(
            reverse('su'),
            {
                'user': 'test_user',
                'backend': 'django.contrib.auth.backends.ModelBackend',
                'next_page': reverse('su'),
            },
            follow=True,
        )
        self.assertEqual(200, response.status_code)
        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEqual(403, response.status_code)

    def test_inheriting_backend(self):
        test_user = User.objects.get(username='test_user')
        test_user2 = User.objects.get(username='test_user2')
        factory = RequestFactory()
        request = factory.get('/su')
        request.user = get_user(
            request, test_user.id, 'oioioi.base.tests.IgnorePasswordAuthBackend'
        )
        request.session = {}
        su_to_user(request, test_user2)

        self.assertEqual('test_user2', request.user.username)
        self.assertEqual(
            'oioioi.base.tests.IgnorePasswordAuthBackend', request.user.backend
        )

    def test_users_list(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(reverse('get_suable_users'), {'substr': ''})
        self.assertEqual(404, response.status_code)
        response = self.client.get(reverse('get_suable_users'))
        self.assertEqual(404, response.status_code)

        response = self.client.get(reverse('get_suable_users'), {'substr': 'te'})
        response = response.json()
        self.assertListEqual(
            [
                'test_user (Test User)',
                'test_user2 (Test User 2)',
                'test_user3 (Test User 3)',
            ],
            response,
        )

        response = self.client.post(reverse('su'), {'user': 'test_user'}, follow=True)
        self.assertEqual(200, response.status_code)
        response = self.client.get(reverse('get_suable_users'), {'substr': 'te'})
        self.assertEqual(403, response.status_code)

    def test_su_status(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(reverse('get_status')).json()
        self.assertEqual(False, response['is_under_su'])
        self.assertEqual(True, response['is_real_superuser'])
        self.assertEqual('test_admin', response['real_user'])

        self.client.post(reverse('su'), {'user': 'test_user'})
        response = self.client.get(reverse('get_status')).json()
        self.assertEqual(True, response['is_under_su'])
        self.assertEqual(True, response['is_real_superuser'])
        self.assertEqual(False, response['is_superuser'])
        self.assertEqual('test_admin', response['real_user'])
        self.assertEqual('test_user', response['user'])


@override_settings(CONTEST_ADMINS_CAN_SU=True)
class TestContestAdminsSu(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_permissions']

    def setUp(self):
        super().setUp()
        c = Contest.objects.get()
        # Use a controller with participant registration.
        c.controller_name = 'oioioi.oi.controllers.OIOnsiteContestController'
        c.save()

    def _test_su_visibility(self, contest, expected):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        url = reverse('contest_dashboard', kwargs={'contest_id': contest.id})
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(expected, 'Login as user' in response.content.decode())

    def _add_user_to_contest(self, username):
        contest = Contest.objects.get()
        p = Participant()
        p.user = User.objects.get(username=username)
        p.contest = contest
        p.save()

    def _do_su(self, username, backend, expected_fail, fail_code=400):
        contest = Contest.objects.get()
        user = User.objects.get(username=username)
        response = self.client.post(
            reverse('su', kwargs={'contest_id': contest.id}),
            {
                'user': username,
                'backend': backend,
            }
        )
        if expected_fail:
            self.assertEqual(fail_code, response.status_code)
        else:
            self.assertEqual(302, response.status_code)
            session = self.client.session
            self.assertEqual(user.id, session[SU_UID_SESSION_KEY])
            self.assertEqual(backend, session[SU_BACKEND_SESSION_KEY])
            self.assertFalse(session[SU_REAL_USER_IS_SUPERUSER])
            self.assertEqual(contest.id, session[SU_ORIGINAL_CONTEST])

    @override_settings(CONTEST_ADMINS_CAN_SU=False)
    def test_su_unavailable(self):
        contest = Contest.objects.get()
        self._test_su_visibility(contest, False)

    def test_su_available(self):
        contest = Contest.objects.get()
        self._test_su_visibility(contest, True)

    def test_users_list(self):
        # Tests if contest admin can only see hints with participants of the contest.
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        contest = Contest.objects.get()
        self._add_user_to_contest('test_user')

        response = self.client.get(
            reverse('get_suable_users', kwargs={'contest_id': contest.id}),
            {'substr': 'te'}
        )
        response = response.json()
        self.assertListEqual(
            [
                'test_user (Test User)',
            ],
            response,
        )

    def test_su(self):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        contest = Contest.objects.get()
        self._add_user_to_contest('test_user')

        # Should fail because this user is not in the contest.
        self._do_su('test_user2', 'django.contrib.auth.backends.ModelBackend', True)

        # Should work because this user is in the contest.
        self._do_su('test_user', 'django.contrib.auth.backends.ModelBackend', False)

        # Su-ed contest admin shouldn't be able to go to urls outside the contest.
        second_contest = Contest.objects.create(
            id='c2',
            controller_name='oioioi.programs.controllers.ProgrammingContestController',
            name='Test contest',
        )
        urls = [
            reverse('contest_dashboard', kwargs={'contest_id': second_contest.id}),
            reverse('select_contest', kwargs={'contest_id': None}),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(302, response.status_code)
            self.assertEqual(
                reverse('su_url_not_allowed', kwargs={'contest_id': contest.id}),
                response.url
            )

        # Contest admin should be able to reset su.
        response = self.client.post(reverse('su_reset'))
        self.assertEqual(302, response.status_code)
        session = self.client.session
        self.assertNotIn(SU_UID_SESSION_KEY, session)
        self.assertNotIn(SU_BACKEND_SESSION_KEY, session)
        self.assertNotIn(SU_REAL_USER_IS_SUPERUSER, session)
        self.assertNotIn(SU_ORIGINAL_CONTEST, session)

        # The user is not a contest admin in the second contest.
        self._test_su_visibility(second_contest, False)

    def _test_post(self, can_post):
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        self._add_user_to_contest('test_user')
        self._do_su('test_user', 'django.contrib.auth.backends.ModelBackend', False)
        contest = Contest.objects.get()
        response = self.client.post(reverse('contest_dashboard', kwargs={'contest_id': contest.id}))
        if can_post:
            self.assertEqual(200, response.status_code)
        else:
            self.assertEqual(302, response.status_code)
            self.assertEqual(
                reverse('su_method_not_allowed', kwargs={'contest_id': contest.id}),
                response.url
            )

    @override_settings(ALLOW_ONLY_GET_FOR_SU_CONTEST_ADMINS=True)
    def test_cant_post(self):
        self._test_post(False)

    @override_settings(ALLOW_ONLY_GET_FOR_SU_CONTEST_ADMINS=False)
    def test_can_post(self):
        self._test_post(True)

    def test_blocked_accounts(self):
        # Tests if contest admins can't su to superusers and other contest admins.
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        contest = Contest.objects.get()
        self._add_user_to_contest('test_admin')
        self._add_user_to_contest('test_contest_admin')

        for username in ['test_admin', 'test_contest_admin']:
            response = self.client.get(
                reverse('get_suable_users', kwargs={'contest_id': contest.id}),
                {'substr': username[:2]}
            )
            response = response.json()
            self.assertNotIn(username, response)

        self._do_su('test_contest_admin', 'django.contrib.auth.backends.ModelBackend', True)

        # Shows the su form with an error message that switching to superuser is forbidden.
        self._do_su('test_admin', 'django.contrib.auth.backends.ModelBackend', True, 200)
        session = self.client.session
        self.assertNotIn(SU_UID_SESSION_KEY, session)
        self.assertNotIn(SU_BACKEND_SESSION_KEY, session)
        self.assertNotIn(SU_REAL_USER_IS_SUPERUSER, session)
        self.assertNotIn(SU_ORIGINAL_CONTEST, session)

    def superusers_cant_su(self):
        # Tests if superusers switched to contest admins can't switch to other contest admins.
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        self._add_user_to_contest('test_contest_admin')
        self._add_user_to_contest('test_contest_basicadmin')
        self._do_su('test_contest_admin', 'django.contrib.auth.backends.ModelBackend', False)
        self._do_su('test_contest_basicadmin', 'django.contrib.auth.backends.ModelBackend', True)

    def user_becomes_superuser(self):
        # Test if being switched to a user which then becomes a superuser resets the user.
        self.assertTrue(self.client.login(username='test_contest_basicadmin'))
        contest = Contest.objects.get()
        self._add_user_to_contest('test_user')
        self._do_su('test_user', 'django.contrib.auth.backends.ModelBackend', False)

        user = User.objects.get(username='test_user')
        user.is_superuser = True
        user.save()

        response = self.client.get(reverse('contest_dashboard', kwargs={'contest_id': contest.id}))
        self.assertEqual(302, response.status_code)
        self.assertEqual(reverse('index'), response.url)
