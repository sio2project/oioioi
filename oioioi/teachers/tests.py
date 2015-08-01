from django.core.urlresolvers import reverse
from django.test import TestCase


class TestProblemsetPermissions(TestCase):
    fixtures = ['test_users', 'teachers']

    def test_problemset_permissions(self):
        url_main = reverse('problemset_main')
        url_add = reverse('problemset_add_or_update')

        self.client.login(username='test_user')  # test_user is a teacher
        url_main = reverse('problemset_main')
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Add problem', response.content)
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 200)

        self.client.login(username='test_user2')  # test_user2 is not
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Add problem', response.content)
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 403)
