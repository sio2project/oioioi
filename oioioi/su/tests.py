# pylint: disable=maybe-no-member
import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.client import RequestFactory
from django.test.utils import override_settings

from oioioi.base.tests import TestCase
from oioioi.su import SU_UID_SESSION_KEY, SU_BACKEND_SESSION_KEY
from oioioi.su.utils import get_user, su_to_user
from oioioi.contests.current_contest import ContestMode


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestSwitchingUsers(TestCase):
    fixtures = ['test_users']

    def test_switching_users(self):
        test_user = User.objects.get(username='test_user')
        self.client.login(username='test_admin')
        response = self.client.get(reverse('su'))
        self.assertEquals(405, response.status_code)

        response = self.client.post(reverse('su'), {
            'user': 'test_user',
            'backend': 'django.contrib.auth.backends.ModelBackend',
        })
        self.assertEquals(302, response.status_code)
        session = self.client.session
        self.assertEquals(test_user.id, session[SU_UID_SESSION_KEY])
        self.assertEquals('django.contrib.auth.backends.ModelBackend',
            session[SU_BACKEND_SESSION_KEY])

        response = self.client.get(reverse('index'), follow=True)
        self.assertContains(response, 'test_user')
        self.assertContains(response, 'Back to admin')
        self.assertEquals('test_user', response.context['user'].username)
        self.assertEquals('django.contrib.auth.backends.ModelBackend',
            response.context['user'].backend)
        self.assertEquals('test_admin', response.context['real_user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend)

        # Being superuser at real privileges isn't enough
        response = self.client.post(reverse('su'), {
            'user': 'test_user2',
            'backend': 'django.contrib.auth.backends.ModelBackend',
        })
        self.assertEquals(403, response.status_code)
        self.assertEquals('test_user', response.context['user'].username)
        self.assertEquals('django.contrib.auth.backends.ModelBackend',
            response.context['user'].backend)
        self.assertEquals('test_admin', response.context['real_user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend)

        response = self.client.post(reverse('su_reset'))
        self.assertEquals(302, response.status_code)
        session = self.client.session
        self.assertNotIn(SU_UID_SESSION_KEY, session)
        self.assertNotIn(SU_BACKEND_SESSION_KEY, session)

        response = self.client.get(reverse('index'), follow=True)
        self.assertContains(response,
            'django.contrib.auth.backends.ModelBackend')
        self.assertEquals('test_admin', response.context['user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['user'].backend)
        self.assertEquals('test_admin', response.context['real_user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend)
        self.assertContains(response, 'Login as user')

    def test_forbidden_su(self):
        self.client.login(username='test_admin')
        response = self.client.post(reverse('su'), {'user': 'test_admin2'})
        self.assertEquals(200, response.status_code)
        self.assertEquals('test_admin', response.context['user'].username)

        response = self.client.post(reverse('su'),
            data={'user': 'test_user', 'next': 'http://enemy.example.com/'})
        self.assertEquals(302, response.status_code)
        self.assertNotIn('enemy', response['Location'])

        self.client.login(username='test_user')
        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEquals(403, response.status_code)
        self.assertEquals('test_user', response.context['user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['user'].backend)
        self.assertEquals('test_user', response.context['real_user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['real_user'].backend)

    def test_su_redirection(self):
        self.client.login(username='test_admin')
        response = self.client.post(reverse('su'), {
            'user': 'test_user',
            'backend': 'django.contrib.auth.backends.ModelBackend',
        })
        self.assertEquals(302, response.status_code)

        response = self.client.get(reverse('index'), follow=True)
        self.assertEquals(200, response.status_code)
        self.client.post(reverse('su_reset'))

        response = self.client.post(reverse('su'), {
            'user': 'test_user',
            'backend': 'django.contrib.auth.backends.ModelBackend',
        })
        self.assertEquals(302, response.status_code)

        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEquals(302, response.status_code)
        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEquals(403, response.status_code)
        self.client.post(reverse('su_reset'))

        response = self.client.post(reverse('su'), {
            'user': 'test_user',
            'backend': 'django.contrib.auth.backends.ModelBackend',
            'next_page': reverse('su'),
        }, follow=True)
        self.assertEquals(200, response.status_code)
        response = self.client.post(reverse('su'), {'user': 'test_admin'})
        self.assertEquals(403, response.status_code)

    def test_inheriting_backend(self):
        test_user = User.objects.get(username='test_user')
        test_user2 = User.objects.get(username='test_user2')
        factory = RequestFactory()
        request = factory.get('/su')
        request.user = get_user(request, test_user.id,
            'oioioi.base.tests.IgnorePasswordAuthBackend')
        request.session = {}
        su_to_user(request, test_user2)

        self.assertEquals('test_user2', request.user.username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            request.user.backend)

    def test_users_list(self):
        self.client.login(username='test_admin')
        response = self.client.get(reverse('get_suable_users'), {'substr': ''})
        self.assertEquals(404, response.status_code)
        response = self.client.get(reverse('get_suable_users'))
        self.assertEquals(404, response.status_code)

        response = self.client.get(reverse('get_suable_users'),
                {'substr': 'te'})
        response = json.loads(response.content)
        self.assertListEqual(
                ['test_user (Test User)', 'test_user2 (Test User 2)',
                 'test_user3 (Test User 3)'],
                response)

        response = self.client.post(reverse('su'),
            {'user': 'test_user'}, follow=True)
        self.assertEquals(200, response.status_code)
        response = self.client.get(reverse('get_suable_users'),
            {'substr': 'te'})
        self.assertEquals(403, response.status_code)

    def test_su_status(self):
        self.client.login(username='test_admin')
        response = json.loads(self.client.get(reverse('get_status')).content)
        self.assertEquals(False, response['is_under_su'])
        self.assertEquals(True, response['is_real_superuser'])
        self.assertEquals('test_admin', response['real_user'])

        self.client.post(reverse('su'), {'user': 'test_user'})
        response = json.loads(self.client.get(reverse('get_status')).content)
        self.assertEquals(True, response['is_under_su'])
        self.assertEquals(True, response['is_real_superuser'])
        self.assertEquals(False, response['is_superuser'])
        self.assertEquals('test_admin', response['real_user'])
        self.assertEquals('test_user', response['user'])
