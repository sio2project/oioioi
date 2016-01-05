import threading
import urllib
from contextlib import contextmanager

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, AnonymousUser
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
from django.template.loaders.cached import Loader as CachedLoader


class IgnorePasswordAuthBackend(object):
    """An authentication backend which accepts any password for an existing
       user.

       It's configured in ``settings_test.py`` and available for all tests.
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


def check_not_accessible(testcase, url_or_viewname, qs=None, *args, **kwargs):
    data = kwargs.pop('data', {})
    if url_or_viewname.startswith('/'):
        url = url_or_viewname
        assert not args
        assert not kwargs
    else:
        url = reverse(url_or_viewname, *args, **kwargs)
    if qs:
        url += '?' + urllib.urlencode(qs)
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


def clear_template_cache():
    from django.template.loader import template_source_loaders
    if template_source_loaders:
        for l in template_source_loaders:
            if isinstance(l, CachedLoader):
                l.reset()


class TestsUtilsMixin(object):
    def assertAllIn(self, elems, container, msg=None):
        """Checks that ``container`` contains all ``elems``."""
        for e in elems:
            self.assertIn(e, container, msg)

    def assertNoneIn(self, elems, container, msg=None):
        """Checks that ``container`` doesn't contain any of ``elems``."""
        for e in elems:
            self.assertNotIn(e, container, msg)
