"""Compiles every stylesheet with the production SCSS compiler, checks the output and renders a few pages with it.

Tests use ``COMPRESS_PRECOMPILERS = ()``, so a broken stylesheet (undefined variable, missing import, syntax
error) would otherwise only show up as a server error on the page that loads it (#867).

Some mistakes compile without an error (see #874):

- importing all of Bootstrap in a partial that is itself imported after Bootstrap includes Bootstrap twice; the
  second copy overrides the rules in between;
- libsass writes calls to unknown functions, such as Bootstrap 4's ``theme-color()``, into the CSS as text, and
  browsers drop the declaration.

The stylesheets import Bootstrap from ``node_modules``, so the tests need ``pnpm install --frozen-lockfile``.
Without it they are skipped, unless ``OIOIOI_SCSS_TESTS_REQUIRED`` is set (as in the ``scss.yml`` CI job), in
which case they fail. ``pytest.yml`` doesn't install the JS dependencies, so ``scss.yml`` runs them.
"""

import os
import re
import tempfile
from pathlib import Path
from unittest import SkipTest

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase

OIOIOI_DIR = Path(__file__).resolve().parents[2]

# Partials (``_*.scss``) are only compiled as part of the stylesheets that import them.
STYLESHEETS = sorted(path.relative_to(OIOIOI_DIR).as_posix() for path in OIOIOI_DIR.glob("**/static/**/*.scss") if not path.name.startswith("_"))

# Bootstrap 4 functions removed in Bootstrap 5.
REMOVED_FUNCTIONS = re.compile(r"\b(theme-color|theme-color-level|color-yiq|gray)\(")


def _require_bootstrap():
    if finders.find("bootstrap/scss/bootstrap.scss") is None:
        reason = "Bootstrap is missing (run `pnpm install --frozen-lockfile`)"
        if os.environ.get("OIOIOI_SCSS_TESTS_REQUIRED", "").lower() not in ("", "0", "false", "no"):
            raise AssertionError(f"{reason} (OIOIOI_SCSS_TESTS_REQUIRED is set)")
        raise SkipTest(reason)


class TestCompiledStylesheets(SimpleTestCase):
    """One test per stylesheet, generated below (``pytest.ini`` collects only ``TestCase`` methods)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _require_bootstrap()

    def test_stylesheets_found(self):
        self.assertIn("base/static/scss/style.scss", STYLESHEETS)

    def check_stylesheet(self, path):
        import django_libsass

        # Same include paths (the staticfiles finders, so Bootstrap comes from node_modules) as in production.
        css = django_libsass.compile(filename=os.fspath(OIOIOI_DIR / path))
        self.assertLessEqual(len(re.findall(r"Bootstrap\s+v5", css)), 1, "Bootstrap is included more than once")
        self.assertIsNone(REMOVED_FUNCTIONS.search(css), "calls a function that doesn't exist")


for _path in STYLESHEETS:
    _name = "test_" + re.sub(r"\W", "_", _path.removesuffix(".scss"))
    setattr(TestCompiledStylesheets, _name, lambda self, path=_path: self.check_stylesheet(path))


class TestPagesWithCompressedStylesheets(TestCase):
    """Renders pages with ``{% compress %}`` and the SCSS precompiler on, as in production.

    This also catches broken ``{% compress %}`` blocks and wrong paths to stylesheets in templates.
    """

    fixtures = ["test_users", "test_contest", "test_full_package", "test_problem_instance"]

    def setUp(self):
        _require_bootstrap()
        self.enterContext(
            override_settings(
                COMPRESS_ENABLED=True,
                COMPRESS_PRECOMPILERS=(("text/x-scss", "django_libsass.SassCompiler"),),
                COMPRESS_ROOT=self.enterContext(tempfile.TemporaryDirectory()),
            )
        )

    def test_pages(self):
        self.assertTrue(self.client.login(username="test_admin"))
        urls = [
            reverse("index"),
            reverse("contest_dashboard", kwargs={"contest_id": "c"}),
            reverse("problems_list", kwargs={"contest_id": "c"}),
            reverse("contest_messages", kwargs={"contest_id": "c"}),
            reverse("timeline_view", kwargs={"contest_id": "c"}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'type="text/x-scss"')
