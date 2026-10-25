"""Compiles key stylesheets with the production SCSS compiler and checks the output.

Some mistakes compile without an error (see #874):

- importing all of Bootstrap in a partial that is itself imported after Bootstrap includes Bootstrap twice; the
  second copy overrides the rules in between;
- libsass writes calls to unknown functions, such as Bootstrap 4's ``theme-color()``, into the CSS as text, and
  browsers drop the declaration.

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
    "common/messages.scss",
    "timeline/timeline.scss",
]

# Bootstrap 4 functions removed in Bootstrap 5.
REMOVED_FUNCTIONS = re.compile(r"\b(theme-color|theme-color-level|color-yiq|gray)\(")


class TestCompiledStylesheets(SimpleTestCase):
    pytestmark = pytest.mark.browser

    def test_compiled_stylesheets(self):
        import django_libsass

        if finders.find("bootstrap/scss/bootstrap.scss") is None:
            BrowserTestCase._skip("Bootstrap is missing (run `pnpm install --frozen-lockfile`)")

        for path in STYLESHEETS:
            with self.subTest(path=path):
                filename = finders.find(path)
                self.assertIsNotNone(filename)
                css = django_libsass.compile(filename=os.fspath(filename))
                self.assertLessEqual(len(re.findall(r"Bootstrap\s+v5", css)), 1, "Bootstrap is included more than once")
                self.assertIsNone(REMOVED_FUNCTIONS.search(css), "calls a function that doesn't exist")
