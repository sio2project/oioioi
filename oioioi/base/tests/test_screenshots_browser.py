"""Opens pages in headless Chromium with the real stylesheets and checks Bootstrap 5 behaviour.

Set ``OIOIOI_SCREENSHOT_DIR`` to save a full-page screenshot of every page; running the tests on two commits gives
before/after pairs taken from the same data at the same viewport size. Run with
``OIOIOI_SCREENSHOT_DIR=/tmp/shots ./test.sh -m browser oioioi/base/tests/test_screenshots_browser.py``; see
:class:`oioioi.base.tests.StyledBrowserTestCase` for the requirements.
"""

from django.contrib.auth.models import User
from django.urls import reverse

from oioioi.base.tests import StyledBrowserTestCase
from oioioi.contests.models import Contest, Submission
from oioioi.forum.models import Category, Post, Thread
from oioioi.forum.tests import get_contest_with_forum

VIEWPORT = {"width": 1280, "height": 800}


class ScreenshotTestCase(StyledBrowserTestCase):
    def setUp(self):
        super().setUp()
        self.page_errors = []

    def open(self, url, username=None, viewport=VIEWPORT):
        """Returns a page showing ``url``; it is closed together with its context at the end of the test.

        JavaScript errors from all pages opened in a test are collected in ``page_errors``.
        """
        context = self.new_browser_context(username, viewport=viewport)
        self.addCleanup(context.close)
        page = context.new_page()
        page.on("pageerror", lambda exc: self.page_errors.append(f"{url}: {exc}"))
        response = page.goto(self.live_server_url + url, wait_until="networkidle")
        self.assertLess(response.status, 400, url)
        return page

    def assertNoPageErrors(self):
        self.assertEqual(self.page_errors, [])


class TestContestPages(ScreenshotTestCase):
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

    def test_messages(self):
        page = self.open(reverse("contest_messages", kwargs={"contest_id": "c"}), "test_admin")
        self.screenshot(page, "questions-list")
        page = self.open(reverse("message", kwargs={"contest_id": "c", "message_id": 4}), "test_admin")
        self.screenshot(page, "questions-public-message")
        page = self.open(reverse("message", kwargs={"contest_id": "c", "message_id": 1}), "test_admin")
        self.screenshot(page, "questions-question")
        # The message pages poll for new answers (messages.js) once they load.
        self.assertNoPageErrors()

    def test_simpleui_contest_dashboard(self):
        page = self.open(reverse("simpleui_contest_dashboard", kwargs={"contest_id": "c"}), "test_admin")
        self.screenshot(page, "simpleui-contest-dashboard")

    def test_timeline(self):
        page = self.open(reverse("timeline_view", kwargs={"contest_id": "c"}), "test_admin")
        self.screenshot(page, "timeline")

    def test_language_picker(self):
        page = self.open(reverse("contest_dashboard", kwargs={"contest_id": "c"}))
        page.click(".lang-select >> xpath=ancestor::div[contains(@class, 'dropdown')]/a")
        self.screenshot(page, "language-picker")

    def test_navbar_login_form(self):
        page = self.open(reverse("contest_dashboard", kwargs={"contest_id": "c"}))
        page.click("#navbar-username")
        page.wait_for_selector("#navbar-login", state="visible")
        self.screenshot(page, "navbar-login-form")

    def test_navbar_admin_forms(self):
        page = self.open(reverse("contest_dashboard", kwargs={"contest_id": "c"}), "test_admin")
        page.click("#navbar-username")
        self.screenshot(page, "navbar-admin-user-menu")

    def test_pending_submission_status(self):
        Submission.objects.filter(id=1).update(status="?")
        page = self.open(reverse("problems_list", kwargs={"contest_id": "c"}), "test_user")
        self.screenshot(page, "status-pending")

    def test_add_message_datetimepicker(self):
        page = self.open(reverse("add_contest_message", kwargs={"contest_id": "c"}), "test_admin")
        self.screenshot(page, "add-message-datetimepicker")

    def test_delete_account(self):
        page = self.open(reverse("delete_account"), "test_user")
        self.screenshot(page, "delete-account")

    def test_markdown_editor(self):
        page = self.open(reverse("add_news"), "test_admin")
        page.wait_for_selector(".md-editor")
        page.locator(".md-editor > textarea").first.fill("Some **news** text.\nSecond line.")
        self.screenshot(page, "markdown-editor")

    def test_download_problems_packages(self):
        from django.core.files.base import ContentFile

        from oioioi.problems.models import Problem, ProblemPackage

        ProblemPackage.objects.create(
            problem=Problem.objects.get(id=1),
            contest=Contest.objects.get(id="c"),
            package_file=ContentFile(b"package", name="package.zip"),
            status="OK",
        )
        page = self.open(reverse("download_problems_packages", kwargs={"contest_id": "c"}) + "?ids=1", "test_admin")
        self.screenshot(page, "download-problems-packages")

    def test_navbar_breakpoints(self):
        for width in (800, 1100):
            page = self.open(reverse("contest_dashboard", kwargs={"contest_id": "c"}), "test_user", viewport={"width": width, "height": 600})
            self.screenshot(page, f"navbar-{width}px")


class TestForumPages(ScreenshotTestCase):
    fixtures = ["test_users", "test_contest"]

    def setUp(self):
        super().setUp()
        user = User.objects.get(username="test_user")
        category = Category.objects.create(forum=get_contest_with_forum().forum, name="Category")
        self.thread = Thread.objects.create(category=category, name="Thread")
        self.post = Post.objects.create(thread=self.thread, content="Reported post", author=user, reported=True, reported_by=user)

    def test_forum_reported_counter(self):
        page = self.open(reverse("forum", kwargs={"contest_id": "c"}), "test_admin")
        self.screenshot(page, "forum-reported-counter")

    def test_delete_post_confirmation(self):
        kwargs = {"contest_id": "c", "category_id": self.thread.category_id, "thread_id": self.thread.id, "post_id": self.post.id}
        page = self.open(reverse("forum_post_delete", kwargs=kwargs), "test_admin")
        self.screenshot(page, "simple-centered-confirmation")

    def test_ban_user(self):
        user = User.objects.get(username="test_user")
        page = self.open(reverse("forum_user_ban", kwargs={"contest_id": "c", "user_id": user.id}), "test_admin")
        self.screenshot(page, "forum-ban-user")


class TestAnonymousPages(ScreenshotTestCase):
    fixtures = ["test_users", "test_contest"]

    def test_sign_up_captcha(self):
        page = self.open(reverse("sign-up"))
        self.screenshot(page, "sign-up-captcha")

    def test_two_factor_backup_token_button(self):
        from django_otp.plugins.otp_static.models import StaticDevice
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.get(username="test_user")
        user.set_password("password")
        user.save()
        TOTPDevice.objects.create(user=user, name="default")
        StaticDevice.objects.create(user=user, name="backup").token_set.create(token="abcdef12")

        page = self.open(reverse("login"))
        page.fill("#id_auth-username", "test_user")
        page.fill("#id_auth-password", "password")
        page.click(".card-footer button[type=submit]")
        page.wait_for_selector("button[value=backup]")
        self.screenshot(page, "two-factor-token-step")


class TestTeacherPages(ScreenshotTestCase):
    fixtures = ["test_users", "teachers", "test_contest"]

    def test_members_input_group(self):
        from oioioi.teachers.utils import add_user_to_contest_as

        contest = Contest.objects.get(id="c")
        contest.controller_name = "oioioi.teachers.controllers.TeacherContestController"
        contest.save()
        add_user_to_contest_as(User.objects.get(username="test_user"), contest, "teacher")
        page = self.open(reverse("show_members", kwargs={"contest_id": "c", "member_type": "pupil"}), "test_user")
        self.screenshot(page, "teachers-members")


class TestBootstrapBehaviour(ScreenshotTestCase):
    """Checks Bootstrap 5 JavaScript behaviour that used to break silently (#874)."""

    fixtures = ["test_users", "test_contest", "test_full_package", "test_problem_instance", "test_submission"]

    def test_async_collapsible_toggles_after_load(self):
        page = self.open(reverse("submission", kwargs={"contest_id": "c", "submission_id": 1}), "test_admin")
        page.click("[data-bs-target='#hidden-reports']")
        page.wait_for_selector("#hidden-reports.show")
        button = page.locator("[data-bs-target^='#hidden-report-']").first
        icon_class = button.locator("i").get_attribute("class")
        target = page.locator(button.get_attribute("data-bs-target"))
        button.click()
        page.wait_for_function("el => el.classList.contains('show') && !el.classList.contains('collapsing')", arg=target.element_handle())
        # After loading, the button gets its icon back and behaves like any Bootstrap collapse trigger.
        self.assertEqual(button.locator("i").get_attribute("class"), icon_class)
        self.assertEqual(button.get_attribute("aria-expanded"), "true")
        button.click()
        page.wait_for_function("el => !el.classList.contains('show') && !el.classList.contains('collapsing')", arg=target.element_handle())
        self.assertEqual(button.get_attribute("aria-expanded"), "false")
        button.click()
        page.wait_for_function("el => el.classList.contains('show')", arg=target.element_handle())
        self.assertNoPageErrors()

    def test_admin_changelist_search_width(self):
        widths = {}
        # The search form takes the whole row only below 576px (media-breakpoint-down(sm)).
        for width in (400, 1000):
            page = self.open(reverse("oioioiadmin:auth_user_changelist"), "test_admin", viewport={"width": width, "height": 800})
            widths[width] = page.eval_on_selector("#changelist-search", "el => el.offsetWidth / el.parentElement.offsetWidth")
        self.assertGreater(widths[400], 0.95)
        self.assertLess(widths[1000], 0.95)

    def test_menu_reachable_at_every_width(self):
        # The side menu is shown from 992px up (d-lg-block); below that the navbar must show its menu button.
        for width in (600, 800, 1000):
            page = self.open(reverse("contest_dashboard", kwargs={"contest_id": "c"}), "test_user", viewport={"width": width, "height": 800})
            self.assertTrue(page.is_visible("#menu") or page.is_visible(".oioioi-navbar__menu"), f"no menu at {width}px")

    def test_pa_registration_hides_prize_fields(self):
        contest = Contest.objects.get(id="c")
        contest.controller_name = "oioioi.pa.controllers.PAContestController"
        contest.save()
        page = self.open(reverse("participants_register", kwargs={"contest_id": "c"}), "test_user")
        page.check("#id_no_prizes")
        for field_id in ("id_address", "id_postal_code", "id_city", "id_t_shirt_size"):
            self.assertFalse(page.is_visible(f"#{field_id}"), field_id)
        page.uncheck("#id_no_prizes")
        self.assertTrue(page.is_visible("#id_address"))

        # The fields are also hidden when the form is shown with the box already checked (e.g. after a form error).
        page.check("#id_no_prizes")
        page.eval_on_selector("#id_no_prizes", "el => { el.form.noValidate = true; }")
        with page.expect_navigation():
            page.click("form button[type=submit]")
        page.wait_for_load_state("networkidle")
        self.assertTrue(page.is_visible(".invalid-feedback, .is-invalid, .alert-danger"))
        self.assertTrue(page.is_checked("#id_no_prizes"))
        self.assertFalse(page.is_visible("#id_address"))
        self.assertNoPageErrors()


class TestAddSchoolForm(ScreenshotTestCase):
    fixtures = ["test_users", "test_contest", "test_schools"]

    def test_similar_schools_check(self):
        contest = Contest.objects.get(id="c")
        contest.controller_name = "oioioi.oi.controllers.OIContestController"
        contest.save()
        page = self.open(reverse("add_school"), "test_user")
        page.fill("#id_city", "Warszawa")
        page.eval_on_selector("#add-school-form", "form => { form.noValidate = true; }")
        page.click("#add-school-button")
        # Submitting first looks for similar schools and asks for confirmation instead of posting the form.
        page.wait_for_selector("#confirm-modal.show")
        self.assertFalse(page.is_disabled("#add-school-button"))
        self.assertNoPageErrors()


class TestTaskArchiveBehaviour(ScreenshotTestCase):
    fixtures = ["test_task_archive", "test_users", "admin_admin", "test_task_archive_progress_labels"]

    def test_copy_link_tooltip(self):
        page = self.open(reverse("task_archive_tag", args=("oi",)))
        self.screenshot(page, "task-archive-tag")
        link = page.locator(".link-getter").first
        title = link.get_attribute("data-bs-original-title")
        link.click()
        page.wait_for_selector(".tooltip-inner:has-text('Copied link!')")
        # When the tooltip closes, the link gets its original title back.
        page.mouse.move(0, 0)
        page.wait_for_selector(".tooltip", state="detached")
        self.assertEqual(link.get_attribute("data-bs-original-title"), title)
        self.assertNoPageErrors()
