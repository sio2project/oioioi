from django.test import TestCase
from django.core.urlresolvers import reverse


class TestWorkersInfo(TestCase):
    fixtures = ['test_users']

    def test_admin_can_see(self):
        self.client.login(username='test_admin')
        url = reverse('show_workers')
        response = self.client.get(url)
        self.assertIn('Komp4', response.content)

    def test_mundane_user_cant_see(self):
        self.client.login(username='test_user')
        url = reverse('show_workers')
        response = self.client.get(url)
        self.assertNotIn('Komp4', response.content)
