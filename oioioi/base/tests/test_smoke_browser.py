"""Opens key pages in headless Chromium and fails on JavaScript errors.

Unit tests never run a browser, so a library upgrade or a broken ``common/`` script can break every page without
failing any of them. Run with ``./test.sh -m browser``; see :class:`oioioi.base.tests.BrowserTestCase` for the
requirements.
"""

import re
from urllib.parse import urlparse

from django.contrib.admin.utils import quote
from django.core.cache import cache
from django.urls import reverse

from oioioi.base.tests import BrowserTestCase
from oioioi.workers import views as workers_views
from oioioi.workers.tests import TestServer

# Regexes of console.error messages that are not bugs. Keep it short and explain each entry.
ALLOWED_CONSOLE_ERRORS = []


class TestBrowserSmoke(BrowserTestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_submission",
        "test_extra_rounds",
    ]

    def setUp(self):
        cache.clear()
        # The workers view asks sioworkersd over XML-RPC. The live server runs in this process, so it sees the patch.
        self._old_workers_server = workers_views.server
        workers_views.server = TestServer()

    def tearDown(self):
        workers_views.server = self._old_workers_server

    def _check_pages(self, urls, username=None):
        """Opens each url and fails with all JavaScript errors found on all pages."""
        context = self.new_browser_context(username)
        failures = []
        try:
            for url in urls:
                errors = []
                page = context.new_page()
                page.on("pageerror", lambda exc, errors=errors: errors.append(f"uncaught exception: {exc}"))
                page.on(
                    "console",
                    lambda msg, errors=errors: (
                        msg.type == "error"
                        and not any(re.search(pattern, msg.text) for pattern in ALLOWED_CONSOLE_ERRORS)
                        and errors.append(f"console.error: {msg.text} ({msg.location.get('url')}:{msg.location.get('lineNumber')})")
                    ),
                )
                response = page.goto(self.live_server_url + url, wait_until="load")
                if response is None or response.status >= 400:
                    errors.append(f"HTTP status {response.status if response else None}")
                if username is not None and urlparse(page.url).path.endswith("/login/"):
                    errors.append(f"redirected to the login page: {page.url}")
                page.close()
                if errors:
                    failures.append(f"{url} (user: {username}):\n" + "\n".join(f"    {e}" for e in errors))
        finally:
            context.close()
        if failures:
            self.fail("JavaScript errors:\n" + "\n".join(failures))

    def test_anonymous_pages(self):
        self._check_pages(
            [
                reverse("index"),
                reverse("problemset_main"),
                reverse("task_archive"),
                reverse("login"),
            ]
        )

    def test_user_pages(self):
        kwargs = {"contest_id": "c"}
        self._check_pages(
            [
                reverse("contest_dashboard", kwargs=kwargs),
                reverse("problems_list", kwargs=kwargs),
                reverse("submit", kwargs=kwargs),
                reverse("my_submissions", kwargs=kwargs),
                reverse("default_ranking", kwargs=kwargs),
            ],
            username="test_user",
        )

    def test_admin_pages(self):
        kwargs = {"contest_id": "c"}
        self._check_pages(
            [
                reverse("oioioiadmin:contests_contest_change", args=(quote("c"),)),
                reverse("statistics_main", kwargs=kwargs),
                reverse("show_workers"),
                reverse("timeline_view", kwargs=kwargs),
            ],
            username="test_admin",
        )
