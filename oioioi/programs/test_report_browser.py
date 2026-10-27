from django.urls import reverse

from oioioi.base.tests import StyledBrowserTestCase
from oioioi.programs.models import TestReport


class TestReportFeedback(StyledBrowserTestCase):
    fixtures = ["admin_admin", "test_users", "test_report_display_test"]

    def setUp(self):
        self.context = self.new_browser_context("admin")
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.page.goto(self.live_server_url + reverse("submission", kwargs={"contest_id": "oi", "submission_id": 7}))

    def test_feedback_in_loaded_copy_stays_in_that_report(self):
        from playwright.sync_api import expect

        with self.server_lock:
            report_id = TestReport.objects.get(pk=57).submission_report_id
        original = self.page.locator(".submission-report").filter(has=self.page.locator(".test-feedback-toggle")).first
        original_panel = original.locator(".test-feedback-clip").first
        original_id = original_panel.get_attribute("id")

        self.page.locator('[data-bs-target="#hidden-reports"]').click()
        self.page.locator(f'[data-bs-target="#hidden-report-{report_id}"]').click()
        loaded = self.page.locator(f"#hidden-report-{report_id} .submission-report")
        toggle = loaded.locator(".test-feedback-toggle").first
        panel = loaded.locator(".test-feedback-clip").first
        toggle.click()
        expect(panel).to_be_visible()
        expect(original_panel).not_to_be_visible()
        self.assertNotEqual(panel.get_attribute("id"), original_id)
        expect(toggle).to_have_attribute("aria-controls", panel.get_attribute("id"))

        loaded.locator(".test-feedback-expand-all").click()
        for feedback in loaded.locator(".test-feedback-clip").all():
            expect(feedback).to_be_visible()
        for feedback in original.locator(".test-feedback-clip").all():
            expect(feedback).not_to_be_visible()
        loaded.locator(".test-feedback-expand-all").click()
        for feedback in loaded.locator(".test-feedback-clip").all():
            expect(feedback).not_to_be_visible()

    def test_print_shows_collapsed_feedback(self):
        from playwright.sync_api import expect

        panels = self.page.locator(".test-feedback-clip")
        self.assertGreater(panels.count(), 0)
        for panel in panels.all():
            expect(panel).not_to_be_visible()
        self.page.emulate_media(media="print")
        for panel in panels.all():
            expect(panel).to_be_visible()
        for button in self.page.locator(".test-feedback-toggle, .test-feedback-expand-all").all():
            expect(button).not_to_be_visible()
        self.page.emulate_media(media="screen")
        for panel in panels.all():
            expect(panel).not_to_be_visible()
