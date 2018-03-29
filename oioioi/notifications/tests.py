import json

from django.core.urlresolvers import reverse_lazy

from oioioi.base.tests import TestCase
from oioioi.notifications.processors import get_notifications_session
from oioioi.notifications.views import notifications_authenticate_view


class TestNotifications(TestCase):
    fixtures = ['test_users']

    def test_notifications(self):
        self.client.login(username='test_user')
        url = reverse_lazy(notifications_authenticate_view)
        response = self.client.post(url, {
            'nsid': get_notifications_session(self.client.session).uid
        })
        resp_obj = json.loads(response.content)
        self.assertEqual(resp_obj['status'], 'OK')
        self.assertEqual(resp_obj['user'], u'1001')
        self.client.logout()
        response = self.client.post(url, {
            'nsid': '123123122'
        })
        resp_obj = json.loads(response.content)
        self.assertEqual(resp_obj['status'], 'UNAUTHORIZED')
