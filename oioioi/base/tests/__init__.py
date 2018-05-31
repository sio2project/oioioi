import threading
from contextlib import contextmanager
from mock import patch
import sys

from django.db import connections, DEFAULT_DB_ALIAS
from django.utils import timezone
from django.test import TestCase as DjangoTestCase
from django.test.utils import CaptureQueriesContext
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from django.template.loaders.cached import Loader as CachedLoader
import six.moves.urllib.parse
import pytest


# Based on: https://github.com/revsys/django-test-plus/blob/master/test_plus/test.py#L30
class _AssertNumQueriesLessThanContext(CaptureQueriesContext):
    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        super(_AssertNumQueriesLessThanContext, self).__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super(_AssertNumQueriesLessThanContext, self). \
            __exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return
        executed = len(self)
        self.test_case.assertTrue(
            executed < self.num,
            "%d queries executed, expected less than %d" %
                (executed, self.num)
        )


class TestCase(DjangoTestCase):

    # Based on: https://github.com/revsys/django-test-plus/blob/master/test_plus/test.py#L236
    def assertNumQueriesLessThan(self, num, *args, **kwargs):
        func = kwargs.pop('func', None)
        using = kwargs.pop("using", DEFAULT_DB_ALIAS)
        conn = connections[using]

        context = _AssertNumQueriesLessThanContext(self, num, conn)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)


class IgnorePasswordAuthBackend(object):
    """An authentication backend which accepts any password for an existing
       user.

       It's configured in ``test_settings.py`` and available for all tests.
    """
    supports_authentication = True
    description = _("Testing backend")

    def authenticate(self, username=None, password=None):
        if not username:
            return None
        if password:
            return None
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise AssertionError('Tried to log in as %r without password, '
                    'but such a user does not exist. Probably the test '
                    'forgot to import a database fixture.' % (username,))

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class FakeTimeMiddleware(object):
    _fake_timestamp = threading.local()

    def process_request(self, request):
        if not hasattr(request, 'timestamp'):
            raise ImproperlyConfigured("FakeTimeMiddleware must go after "
                    "TimestampingMiddleware")
        fake_timestamp = getattr(self._fake_timestamp, 'value', None)
        if fake_timestamp:
            request.timestamp = fake_timestamp


@contextmanager
def fake_time(timestamp):
    """A context manager which causes all requests having the specified
       timestamp, regardless of the real wall clock time."""
    cache.clear()
    FakeTimeMiddleware._fake_timestamp.value = timestamp
    yield
    del FakeTimeMiddleware._fake_timestamp.value


@contextmanager
def fake_timezone_now(timestamp):
    with patch.object(timezone, 'now', return_value=timestamp):
        with fake_time(timestamp):
            yield


def check_not_accessible(testcase, url_or_viewname, qs=None, *args, **kwargs):
    data = kwargs.pop('data', {})
    if url_or_viewname.startswith('/'):
        url = url_or_viewname
        assert not args
        assert not kwargs
    else:
        url = reverse(url_or_viewname, *args, **kwargs)
    if qs:
        url += '?' + six.moves.urllib.parse.urlencode(qs)
    response = testcase.client.get(url, data=data, follow=True)
    testcase.assertIn(response.status_code, (403, 404, 200))
    if response.status_code == 200:
        testcase.assertIn('/login/', repr(response.redirect_chain))


def check_ajax_not_accessible(testcase, url_or_viewname, *args, **kwargs):
    data = kwargs.pop('data', {})
    if url_or_viewname.startswith('/'):
        url = url_or_viewname
        assert not args
        assert not kwargs
    else:
        url = reverse(url_or_viewname, *args, **kwargs)
    response = testcase.client.get(url, data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    testcase.assertIn(response.status_code, (403, 404))


class TestsUtilsMixin(object):
    def assertAllIn(self, elems, container, msg=None):
        """Checks that ``container`` contains all ``elems``."""
        for e in elems:
            self.assertIn(e, container, msg)

    def assertNoneIn(self, elems, container, msg=None):
        """Checks that ``container`` doesn't contain any of ``elems``."""
        for e in elems:
            self.assertNotIn(e, container, msg)


def needs_linux(fn):
    return pytest.mark.skip(sys.platform not in ('linux', 'linux2'),
            reason="This test needs Linux")(fn)


