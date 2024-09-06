from oioioi.base.tests import TestCase
from django.urls import reverse

from oioioi.welcomepage.models import WelcomePageMessage


class TestWelcomePage(TestCase):
    fixtures = ['test_users']

    def test_button_visibility(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(reverse('welcome_page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit message')

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(reverse('welcome_page'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Edit message')

        response = self.client.get(reverse('edit_welcome_page'))
        self.assertEqual(response.status_code, 403)

    def test_no_message(self):
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(reverse('welcome_page'))
        self.assertContains(response, 'There is no welcome message available')

    def test_message(self):
        self.assertTrue(self.client.login(username='test_user'))
        msgs = {
            'pl': 'Witaj na OIOIOI!',
            'en': 'Welcome to OIOIOI!'
        }
        for lang, msg in msgs.items():
            WelcomePageMessage.objects.create(language=lang, content=msg)

        for lang, msg in msgs.items():
            self.client.cookies['lang'] = lang
            response = self.client.get(reverse('welcome_page'))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, msg)
