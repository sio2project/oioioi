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

    def test_print_shows_open_and_collapsed_feedback(self):
        from playwright.sync_api import expect

        panels = self.page.locator(".test-feedback-clip")
        self.assertGreater(panels.count(), 1)
        for panel in panels.all():
            expect(panel).not_to_be_visible()
        self.page.locator(".test-feedback-toggle").first.click()
        expect(panels.first).to_be_visible()
        for panel in panels.all()[1:]:
            expect(panel).not_to_be_visible()
        self.page.emulate_media(media="print")
        for panel in panels.all():
            expect(panel).to_be_visible()
        for button in self.page.locator(".test-feedback-toggle, .test-feedback-expand-all").all():
            expect(button).not_to_be_visible()
        self.page.emulate_media(media="screen")
        expect(panels.first).to_be_visible()
        for panel in panels.all()[1:]:
            expect(panel).not_to_be_visible()

    def test_scores_stay_on_one_line_with_long_feedback(self):
        from playwright.sync_api import expect

        with self.server_lock:
            TestReport.objects.filter(pk=57).update(comment="Dodatkowy kontekst. " * 4 + "https://example.invalid/" + "x" * 150)
        report = self.page.locator(".submission-report").first
        toggle = report.locator(".test-feedback-toggle").first
        feedback = report.locator(".test-feedback").first

        for width in (1280, 400):
            with self.subTest(width=width):
                self.page.set_viewport_size({"width": width, "height": 800})
                self.page.reload()
                for expanded in (True, False):
                    toggle.click()
                    expect(toggle).to_have_attribute("aria-expanded", str(expanded).lower())
                    if expanded:
                        expect(feedback).to_be_visible()
                        self.assertTrue(feedback.evaluate("el => el.scrollWidth <= el.clientWidth + 1"), "Feedback overflows its cell")
                    # Count the actual rendered lines of the score, rather than checking a CSS declaration.
                    scores = report.locator(".group-score").evaluate_all(
                        r"""cells => cells.map(cell => {
                            const node = [...cell.childNodes].find(node =>
                                node.nodeType === Node.TEXT_NODE && node.textContent.includes('/'));
                            const range = document.createRange();
                            range.setStart(node, node.textContent.search(/\S/));
                            range.setEnd(node, node.textContent.trimEnd().length);
                            return {text: node.textContent.trim(), lines: range.getClientRects().length};
                        })"""
                    )
                    self.assertTrue(scores)
                    for score in scores:
                        self.assertEqual(score["lines"], 1, score)
