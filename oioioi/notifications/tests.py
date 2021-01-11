from django.core.urlresolvers import reverse_lazy

from oioioi.base.tests import TestCase
from oioioi.notifications.processors import get_notifications_session


class TestNotifications(TestCase):
    fixtures = ['test_users']

    def test_notifications(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse_lazy('notifications_authenticate')
        response = self.client.post(
            url, {'nsid': get_notifications_session(self.client.session).uid}
        )
        resp_obj = response.json()
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['user'], u'1001')
        self.client.logout()
        response = self.client.post(url, {'nsid': '123123122'})
        resp_obj = response.json()
        self.assertEqual(resp_obj['status'], 'UNAUTHORIZED')
