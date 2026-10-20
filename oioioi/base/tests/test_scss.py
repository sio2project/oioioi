"""Compiles key stylesheets with the production SCSS compiler and checks the output.

Importing all of Bootstrap in a partial that is itself imported after Bootstrap compiles without an error, but
includes Bootstrap twice; the second copy overrides the rules in between. See #874.

The stylesheets import Bootstrap from ``node_modules``, so the test needs ``pnpm install``. It carries the
``browser`` marker because the CI job that runs browser tests installs the JS dependencies. #867 extends this
to all stylesheets and moves it to its own job.
"""

import os
import re

import pytest
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase

from oioioi.base.tests import BrowserTestCase

STYLESHEETS = [
    "scss/style.scss",
    "simpleui/contest/contest.scss",
]


class TestCompiledStylesheets(SimpleTestCase):
    pytestmark = pytest.mark.browser

    def test_bootstrap_included_once(self):
        import django_libsass

        if finders.find("bootstrap/scss/bootstrap.scss") is None:
            BrowserTestCase._skip("Bootstrap is missing (run `pnpm install --frozen-lockfile`)")

        for path in STYLESHEETS:
            with self.subTest(path=path):
                filename = finders.find(path)
                self.assertIsNotNone(filename)
                css = django_libsass.compile(filename=os.fspath(filename))
                self.assertLessEqual(len(re.findall(r"Bootstrap\s+v5", css)), 1, "Bootstrap is included more than once")
