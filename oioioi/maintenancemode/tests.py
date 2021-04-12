from django.urls import reverse
from django.test.utils import override_settings

from oioioi.base.tests import TestCase
from oioioi.maintenancemode.models import get_maintenance_mode, set_maintenance_mode


class TestMaintenanceMode(TestCase):
    fixtures = ['test_users']

    def test_set_maintenance(self):
        set_maintenance_mode(True, 'test')
        info = get_maintenance_mode()
        self.assertEqual('test', info['message'])
        self.assertEqual(True, info['state'])
        set_maintenance_mode(False)
        info = get_maintenance_mode()
        self.assertEqual('', info['message'])
        self.assertEqual(False, info['state'])

    def test_not_logged_redirect(self):
        set_maintenance_mode(True, 'test message')
        response = self.client.get('/', follow=True)
        self.assertRedirects(response, reverse('maintenance'))
        self.assertEqual(response.context['message'], 'test message')
        self.assertContains(response, 'test message')
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_logged_user_redirect(self):
        set_maintenance_mode(True, 'test message')
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get('/', follow=True)
        self.assertRedirects(response, reverse('maintenance'))
        self.assertContains(response, 'test message')
        response = self.client.post(
            reverse('logout'),
            {
                'user': 'test_user',
                'backend': 'django.contrib.auth.backends.ModelBackend',
            },
        )
        self.assertEqual(response.status_code, 302)

    @override_settings(DEFAULT_GLOBAL_PORTAL_AS_MAIN_PAGE=False)
    def test_logged_admin_no_redirect(self):
        set_maintenance_mode(True, 'test message')
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    @override_settings(DEFAULT_GLOBAL_PORTAL_AS_MAIN_PAGE=False)
    def test_maintenance_off(self):
        set_maintenance_mode(False)
        response = self.client.get(reverse('maintenance'))
        self.assertRedirects(response, '/')

    @override_settings(DEFAULT_GLOBAL_PORTAL_AS_MAIN_PAGE=False)
    def test_su_no_redirect(self):
        set_maintenance_mode(True, 'test message')
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.post(
            reverse('su'),
            {
                'user': 'test_user',
                'backend': 'django.contrib.auth.backends.ModelBackend',
            },
        )
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_admin_change_message(self):
        set_maintenance_mode(False)
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.post(
            reverse('set_maintenance_mode'),
            {
                'message': 'new test message',
                'set_button': 1,
            },
        )
        info = get_maintenance_mode()
        self.assertEqual('new test message', info['message'])
        self.assertEqual(True, info['state'])
        self.client.post(
            reverse('set_maintenance_mode'),
            {
                'turn_off_button': 1,
            },
        )
        info = get_maintenance_mode()
        self.assertEqual(False, info['state'])
