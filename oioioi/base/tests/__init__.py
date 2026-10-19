import importlib.util
import os
import sys
import threading
import urllib.parse
from contextlib import contextmanager
from unittest import SkipTest, mock

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders as staticfiles_finders
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import DEFAULT_DB_ALIAS, connections
from django.test import TestCase as DjangoTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

try:
    from unittest.mock import patch
except ImportError:
    from unittest.mock import patch


# Based on: https://github.com/revsys/django-test-plus/blob/master/test_plus/test.py#L30
class _AssertNumQueriesLessThanContext(CaptureQueriesContext):
    def __init__(self, test_case, num, connection):
        self.test_case = test_case
        self.num = num
        super().__init__(connection)

    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        if exc_type is not None:
            return
        executed = len(self)
        self.test_case.assertTrue(
            executed < self.num,
            f"{executed} queries executed, expected less than {self.num}",
        )


class TestCase(DjangoTestCase):
    def setUp(self):
        csrf_patch = mock.patch("django.middleware.csrf.get_token", mock.Mock(return_value="deterministicToken"))

        csrf_patch.start()
        self.addCleanup(csrf_patch.stop)

    # Based on: https://github.com/revsys/django-test-plus/blob/master/test_plus/test.py#L236
    def assertNumQueriesLessThan(self, num, *args, **kwargs):
        func = kwargs.pop("func", None)
        using = kwargs.pop("using", DEFAULT_DB_ALIAS)
        conn = connections[using]

        context = _AssertNumQueriesLessThanContext(self, num, conn)
        if func is None:
            return context

        with context:
            func(*args, **kwargs)

    def assertRegex(self, text, regex, msg=None):
        super(DjangoTestCase, self).assertRegex(text, regex, msg)

    def assertNotRegex(self, text, regex, msg=None):
        super(DjangoTestCase, self).assertNotRegex(text, regex, msg)


class IgnorePasswordAuthBackend:
    """An authentication backend which accepts any password for an existing
    user.

    It's configured in ``test_settings.py`` and available for all tests.
    """

    supports_authentication = True
    description = _("Testing backend")

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None
        if password:
            return None
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            raise AssertionError(
                f"Tried to log in as {username!r} without password, but such a user does not exist. Probably the test forgot to import a database fixture."
            )

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class FakeTimeMiddleware:
    _fake_timestamp = threading.local()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._process_request(request)

        return self.get_response(request)

    def _process_request(self, request):
        if not hasattr(request, "timestamp"):
            raise ImproperlyConfigured("FakeTimeMiddleware must go after TimestampingMiddleware")
        fake_timestamp = getattr(self._fake_timestamp, "value", None)
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
    with patch.object(timezone, "now", return_value=timestamp):
        with fake_time(timestamp):
            yield


def get_url(url_or_viewname, qs, *args, **kwargs):
    if url_or_viewname.startswith("/"):
        url = url_or_viewname
        assert not args
        assert not kwargs
    else:
        url = reverse(url_or_viewname, *args, **kwargs)
    if qs:
        url += "?" + urllib.parse.urlencode(qs)
    return url


def check_not_accessible(testcase, url_or_viewname, qs=None, *args, **kwargs):
    data = kwargs.pop("data", {})
    url = get_url(url_or_viewname, qs, *args, **kwargs)
    response = testcase.client.get(url, data=data, follow=True)
    testcase.assertIn(response.status_code, (403, 404, 200))
    if response.status_code == 200:
        testcase.assertIn("/login/", repr(response.redirect_chain))


def check_is_accessible(testcase, url_or_viewname, qs=None, *args, **kwargs):
    data = kwargs.pop("data", {})
    url = get_url(url_or_viewname, qs, *args, **kwargs)
    response = testcase.client.get(url, data=data, follow=True)
    testcase.assertNotIn(response.status_code, (403, 404))
    if response.status_code == 200:
        testcase.assertNotIn("/login/", repr(response.redirect_chain))


def check_ajax_not_accessible(testcase, url_or_viewname, *args, **kwargs):
    data = kwargs.pop("data", {})
    url = get_url(url_or_viewname, None, *args, **kwargs)
    response = testcase.client.get(url, data=data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
    testcase.assertIn(response.status_code, (403, 404))


class TestsUtilsMixin:
    def assertAllIn(self, elems, container, msg=None):
        """Checks that ``container`` contains all ``elems``."""
        for e in elems:
            self.assertIn(e, container, msg)

    def assertNoneIn(self, elems, container, msg=None):
        """Checks that ``container`` doesn't contain any of ``elems``."""
        for e in elems:
            self.assertNotIn(e, container, msg)


def needs_linux(fn):
    fn = pytest.mark.needs_linux(fn)
    return pytest.mark.skipif(sys.platform not in ("linux", "linux2"), reason="This test needs Linux")(fn)


class BrowserTestCase(StaticLiveServerTestCase):
    """Base class for tests that open pages of a live server in headless Chromium (Playwright).

    The tests are marked with ``browser`` (deselect them with ``-m "not browser"``). They are skipped when
    Playwright, the webpack bundles (``dist_webpack/``) or the browser is missing, unless
    ``OIOIOI_BROWSER_TESTS_REQUIRED`` is set (as in CI), in which case they fail.
    """

    pytestmark = pytest.mark.browser

    @classmethod
    def _skip(cls, reason):
        if os.environ.get("OIOIOI_BROWSER_TESTS_REQUIRED", "").lower() not in ("", "0", "false", "no"):
            raise AssertionError(f"{reason} (OIOIOI_BROWSER_TESTS_REQUIRED is set)")
        raise SkipTest(reason)

    @classmethod
    def setUpClass(cls):
        if importlib.util.find_spec("playwright") is None:
            cls._skip("Playwright is not installed (run `uv sync --group browser`)")
        for bundle in ("jquery.bundle.js", "index.bundle.js"):
            if staticfiles_finders.find(bundle) is None:
                cls._skip(f"{bundle} is missing (run `pnpm install --frozen-lockfile && pnpm run build`)")

        from playwright.sync_api import Error, sync_playwright

        cls._playwright = sync_playwright().start()
        try:
            cls.browser = cls._playwright.chromium.launch()
        except Error as e:
            cls._playwright.stop()
            cls._skip(f"Cannot launch Chromium (run `uv run playwright install --with-deps chromium`): {e}")

        # Playwright's sync API runs an event loop in this thread, so Django would refuse ORM calls
        # (SynchronousOnlyOperation) without this.
        cls._old_async_unsafe = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
        try:
            super().setUpClass()
        except Exception:
            cls._close_browser()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._close_browser()

    @classmethod
    def _close_browser(cls):
        try:
            try:
                cls.browser.close()
            finally:
                cls._playwright.stop()
        finally:
            if cls._old_async_unsafe is None:
                os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
            else:
                os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = cls._old_async_unsafe

    def new_browser_context(self, username=None):
        """Returns a new browser context, logged in as ``username`` if given."""
        context = self.browser.new_context()
        if username is not None:
            self.client.force_login(User.objects.get(username=username))
            session_cookie = self.client.cookies[settings.SESSION_COOKIE_NAME]
            context.add_cookies([{"name": session_cookie.key, "value": session_cookie.value, "url": self.live_server_url}])
        return context
