from django.urls import reverse_lazy

from oioioi.base.tests import TestCase
from oioioi.notifications.processors import get_notifications_session


class TestNotifications(TestCase):
    fixtures = ['test_users']

    def test_authenticate_success(self):
        self.assertTrue(self.client.login(username='test_user'))
        
        url = reverse_lazy('notifications_authenticate')
        response = self.client.post(
            url, {'nsid': get_notifications_session(self.client.session).uid}
        )
        
        self.assertEqual(response.status_code, 200)
        resp_obj = response.json()
        self.assertEqual(resp_obj['user'], '1001')

    def test_authenticate_failure(self):
        url = reverse_lazy('notifications_authenticate')

        # Test with invalid session ID        
        response = self.client.post(url, {'nsid': '123123122'})
        self.assertEqual(response.status_code, 401)

        # Test with missing nsid parameter
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 400)
