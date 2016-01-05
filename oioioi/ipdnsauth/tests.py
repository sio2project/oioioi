from django.test import TestCase
from django.contrib.auth.models import User
from django.test.utils import override_settings
from oioioi.test_settings import AUTHENTICATION_BACKENDS, MIDDLEWARE_CLASSES
from oioioi.ipdnsauth.management.commands.ipdnsauth import Command
from oioioi.ipdnsauth.models import IpToUser, DnsToUser
import socket
import os

@override_settings(AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS +
                   ('oioioi.ipdnsauth.backends.IpDnsBackend',))
@override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE_CLASSES +
                   ('oioioi.ipdnsauth.middleware.IpDnsAuthMiddleware',))
class TestAutoAuthorization(TestCase):
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


def _test_filename(name):
    return os.path.join(os.path.dirname(__file__), 'files', name)


@override_settings(AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS +
                   ('oioioi.ipdnsauth.backends.IpDnsBackend',))
@override_settings(MIDDLEWARE_CLASSES=MIDDLEWARE_CLASSES +
                   ('oioioi.ipdnsauth.middleware.IpDnsAuthMiddleware',))
class TestIpDnsManagement(TestCase):
    fixtures = ['test_users']

    def test_ip_management(self):
        filename = _test_filename('ip_bindings.csv')
        manager = Command()
        manager.run_from_argv(['manage.py', 'ipdnsauth', 'ip',
                                '--load', filename])
        self.assertTrue(User.objects
                            .filter(username='test_user')
                            .filter(iptouser__ip_addr='127.0.0.1')
                            .exists())

        loaded = manager.export_data('ip', IpToUser.objects)
        expected = (('test_user', '127.0.0.1'),
                    ('test_user', '127.0.0.3'),
                    ('test_user2', 'fe80::762f:68ff:fedd:9bd8'),
                    )
        self.assertItemsEqual(expected, loaded)

        manager.clear('ip', IpToUser.objects)
        loaded = manager.export_data('ip', IpToUser.objects)
        self.assertEquals(len(loaded), 0)

    def test_dns_management(self):
        filename = _test_filename('dns_bindings.csv')
        manager = Command()
        manager.run_from_argv(['manage.py', 'ipdnsauth', 'dns',
                                '--load', filename])
        self.assertTrue(User.objects
                            .filter(username='test_user')
                            .filter(dnstouser__dns_name='localhost')
                            .exists())

        loaded = manager.export_data('dns', DnsToUser.objects)
        expected = (('test_user', 'localhost'),
                    ('test_user2', 'some.dotted.domain'),
                    )
        self.assertItemsEqual(expected, loaded)

        manager.run_from_argv(['manage.py', 'ipdnsauth', 'dns',
                                '--unload', filename])
        loaded = manager.export_data('dns', DnsToUser.objects)
        self.assertEquals(len(loaded), 0)
