from django.test import TestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from oioioi.test_settings import AUTHENTICATION_BACKENDS, MIDDLEWARE_CLASSES
import socket

@override_settings(AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS +
                   ('oioioi.ipdnsauth.backends.IpDnsBackend',))
@override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE_CLASSES +
                   ('oioioi.ipdnsauth.middleware.IpDnsAuthMiddleware',))
class TestIPAuthorization(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        self.test_user = User.objects.get(username='test_user')
        self.test_user2 = User.objects.get(username='test_user2')

    def test_ip_authentication(self):
        self.test_user.iptouser_set.create(ip_addr='127.0.0.1')
        self.test_user2.dnstouser_set.create(dns_name='localhost')
        response = self.client.get('/')
        self._assertBackend(response, self.test_user)

    def test_ipv4packing_authentication(self):
        self.test_user.iptouser_set.create(ip_addr='::ffff:127.0.0.1')
        response = self.client.get('/')
        self._assertBackend(response, self.test_user)

    def test_reverse_dns_authentication(self):
        self.test_user2.dnstouser_set.create(
                dns_name=socket.getfqdn('localhost'))
        response = self.client.get('/')
        self._assertBackend(response, self.test_user2)

    def _assertBackend(self, response, user):
        session = self.client.session
        self.assertEqual(session['_auth_user_id'], user.id)
        self.assertEqual(session['_auth_user_backend'],
                         'oioioi.ipdnsauth.backends.IpDnsBackend')
