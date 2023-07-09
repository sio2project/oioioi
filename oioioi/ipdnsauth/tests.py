import os
import socket
from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.test.utils import override_settings

from oioioi.base.tests import TestCase, fake_time
from oioioi.contestexcl.models import ExclusivenessConfig
from oioioi.contests.models import Contest
from oioioi.ipdnsauth.management.commands.ipdnsauth import Command
from oioioi.ipdnsauth.models import DnsToUser, IpToUser
from oioioi.test_settings import AUTHENTICATION_BACKENDS, MIDDLEWARE


@override_settings(
    AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS
    + ('oioioi.ipdnsauth.backends.IpDnsBackend',)
)
@override_settings(
    MIDDLEWARE=MIDDLEWARE
    + (
        'oioioi.contestexcl.middleware.ExclusiveContestsMiddleware',
        'oioioi.ipdnsauth.middleware.IpDnsAuthMiddleware',
    )
)
class TestAutoAuthorization(TestCase):
    fixtures = ['test_users', 'test_two_empty_contests']

    def setUp(self):
        self.test_user = User.objects.get(username='test_user')
        self.test_user2 = User.objects.get(username='test_user2')

        ex_conf = ExclusivenessConfig()
        ex_conf.contest = Contest.objects.get(id='c1')
        ex_conf.start_date = datetime(2012, 1, 1, 10, tzinfo=timezone.utc)
        ex_conf.end_date = datetime(2012, 1, 1, 14, tzinfo=timezone.utc)
        ex_conf.save()

    def _assertBackend(self, user):
        with fake_time(datetime(2012, 1, 1, 11, tzinfo=timezone.utc)):
            self.client.get('/c/c1/id')
            session = self.client.session
            self.assertEqual(session['_auth_user_id'], str(user.id))
            self.assertEqual(
                session['_auth_user_backend'], 'oioioi.ipdnsauth.backends.IpDnsBackend'
            )

    def test_ip_authentication(self):
        self.test_user.iptouser_set.create(ip_addr='127.0.0.1')
        self.test_user2.dnstouser_set.create(dns_name='localhost')
        self._assertBackend(self.test_user)

    def test_ipv4packing_authentication(self):
        self.test_user.iptouser_set.create(ip_addr='::ffff:127.0.0.1')
        self._assertBackend(self.test_user)

    def test_reverse_dns_authentication(self):
        names = {socket.getfqdn('localhost'), 'localhost'}
        for name in names:
            self.test_user2.dnstouser_set.create(dns_name=name)
        self._assertBackend(self.test_user2)


def _test_filename(name):
    return os.path.join(os.path.dirname(__file__), 'files', name)


class TestIpDnsManagement(TestCase):
    fixtures = ['test_users']

    def test_ip_management(self):
        filename = _test_filename('ip_bindings.csv')
        manager = Command()
        manager.run_from_argv(['manage.py', 'ipdnsauth', 'ip', '--load', filename])
        self.assertTrue(
            User.objects.filter(username='test_user')
            .filter(iptouser__ip_addr='127.0.0.1')
            .exists()
        )

        loaded = manager.export_data('ip', IpToUser.objects)
        expected = (
            ('test_user', '127.0.0.1'),
            ('test_user', '127.0.0.3'),
            ('test_user2', 'fe80::762f:68ff:fedd:9bd8'),
        )
        self.assertCountEqual(expected, loaded)

        manager.clear('ip', IpToUser.objects)
        loaded = manager.export_data('ip', IpToUser.objects)
        self.assertEqual(len(loaded), 0)

    def test_dns_management(self):
        filename = _test_filename('dns_bindings.csv')
        manager = Command()
        manager.run_from_argv(['manage.py', 'ipdnsauth', 'dns', '--load', filename])
        self.assertTrue(
            User.objects.filter(username='test_user')
            .filter(dnstouser__dns_name='localhost')
            .exists()
        )

        loaded = manager.export_data('dns', DnsToUser.objects)
        expected = (
            ('test_user', 'localhost'),
            ('test_user2', 'some.dotted.domain'),
        )
        self.assertCountEqual(expected, loaded)

        manager.run_from_argv(['manage.py', 'ipdnsauth', 'dns', '--unload', filename])
        loaded = manager.export_data('dns', DnsToUser.objects)
        self.assertEqual(len(loaded), 0)
