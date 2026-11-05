"""Screenshots of the main pages, to compare the overall layout before and after stylesheet changes.

Run with ``OIOIOI_SCREENSHOT_DIR=/tmp/shots ./test.sh -m browser oioioi/base/tests/test_screenshots_layout_browser.py``;
see :class:`oioioi.base.tests.StyledBrowserTestCase`.
"""

from django.contrib.admin.utils import quote
from django.urls import reverse

from oioioi.base.tests.test_screenshots_browser import ScreenshotTestCase


class TestLayoutScreenshots(ScreenshotTestCase):
    fixtures = [
        "test_users",
        "test_contest",
        "test_full_package",
        "test_problem_instance",
        "test_submission",
        "test_messages",
        "test_templates",
        "test_extra_rounds",
    ]

    def _pages(self, pages, users=(None, "test_admin"), widths=(1280,)):
        for user in users:
            for name, url in pages:
                for width in widths:
                    page = self.open(url, user, viewport={"width": width, "height": 800})
                    suffix = "" if width == 1280 else f"-{width}px"
                    self.screenshot(page, f"{name}-{user or 'anonymous'}{suffix}")
        self.assertNoPageErrors()

    def test_public_pages(self):
        self._pages(
            [
                ("index", reverse("index")),
                ("contest-dashboard", reverse("contest_dashboard", kwargs={"contest_id": "c"})),
                ("problemset", reverse("problemset_main")),
            ],
            widths=(1280, 800, 400),
        )

    def test_logged_in_pages(self):
        self._pages(
            [
                ("submission", reverse("submission", kwargs={"contest_id": "c", "submission_id": 1})),
                ("admin-contest-changelist", reverse("oioioiadmin:contests_contest_changelist")),
                ("admin-contest-change", reverse("oioioiadmin:contests_contest_change", args=(quote("c"),))),
                ("simpleui-contest", reverse("simpleui_contest_dashboard", kwargs={"contest_id": "c"})),
            ],
            users=("test_admin",),
            widths=(1280, 800, 400),
        )
        self._pages([("submission", reverse("submission", kwargs={"contest_id": "c", "submission_id": 1}))], users=("test_user",))
