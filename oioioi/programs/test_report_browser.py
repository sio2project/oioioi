import os
from io import BytesIO
from itertools import product
from unittest import skipUnless

from django.urls import reverse

from oioioi.base.tests import StyledBrowserTestCase
from oioioi.programs.models import GroupReport, TestReport, UserOutGenStatus


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

        expand_all = loaded.locator(".test-feedback-expand-all")
        initial_width = expand_all.bounding_box()["width"]
        expand_all.click()
        expect(expand_all).to_have_accessible_name("Collapse all")
        self.assertEqual(expand_all.bounding_box()["width"], initial_width)
        for feedback in loaded.locator(".test-feedback-clip").all():
            expect(feedback).to_be_visible()
        for feedback in original.locator(".test-feedback-clip").all():
            expect(feedback).not_to_be_visible()
        expand_all.click()
        expect(expand_all).to_have_accessible_name("Expand all")
        self.assertEqual(expand_all.bounding_box()["width"], initial_width)
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
        self.assert_report_geometry(self.page.locator(".submission-report .table-report").first)
        for button in self.page.locator(".test-feedback-toggle, .test-feedback-expand-all").all():
            expect(button).not_to_be_visible()
        self.page.emulate_media(media="screen")
        expect(panels.first).to_be_visible()
        for panel in panels.all()[1:]:
            expect(panel).not_to_be_visible()
        self.assert_report_geometry(self.page.locator(".submission-report .table-report").first)

    def test_user_output_actions_show_on_hover_but_processing_stays_visible(self):
        from playwright.sync_api import expect

        download_url = reverse("download_user_output", kwargs={"contest_id": "oi", "testreport_id": 57})
        for status, label in ((None, "[generate out]"), ("OK", "usr-out"), ("?", "[processing]")):
            with self.subTest(status=status):
                with self.server_lock:
                    TestReport.objects.filter(pk=57).update(output_file="generated.out" if status == "OK" else "")
                    if status is not None:
                        UserOutGenStatus.objects.update_or_create(testreport_id=57, defaults={"status": status})
                self.page.reload()
                self.page.mouse.move(0, 0)
                report = self.page.locator(".submission-report").first
                cell = report.locator(".test-actions-toggler").filter(has=self.page.locator('[data-feedback-target$="-57"]'))
                action = cell.locator(".test-out-link")
                if status == "OK":
                    expect(action).to_have_count(0)
                    action = cell.locator(f'a[href="{download_url}"]')
                    expect(action).to_have_count(1)
                expect(action).to_have_text(label)
                if status == "?":
                    expect(action).to_be_visible()
                else:
                    expect(action).not_to_be_visible()
                initial_width = cell.bounding_box()["width"]
                cell.hover()
                expect(action).to_be_visible()
                self.assertEqual(cell.bounding_box()["width"], initial_width)
                self.page.mouse.move(0, 0)
                if status == "?":
                    expect(action).to_be_visible()
                else:
                    expect(action).not_to_be_visible()

        # An OK test without feedback still needs its existing usr-out link.
        with self.server_lock:
            TestReport.objects.filter(pk=57).update(
                status="OK", comment="", result_percentage_numerator=None, result_percentage_denominator=None, time_used=0, output_file="generated.out"
            )
            UserOutGenStatus.objects.filter(testreport_id=57).update(status="OK")
        self.page.reload()
        download = report.locator(f'a[href="{download_url}"]')
        expect(download).to_have_count(1)
        expect(download).to_have_text("usr-out")

    def test_scores_stay_on_one_line_with_long_feedback(self):
        from playwright.sync_api import expect

        with self.server_lock:
            TestReport.objects.filter(pk=57).update(comment="Dodatkowy kontekst. " * 4 + "https://example.invalid/" + "x" * 150)
            report_id = TestReport.objects.get(pk=57).submission_report_id
        report = self.page.locator(".submission-report").first
        toggle = report.locator(".test-feedback-toggle").first
        feedback = report.locator(".test-feedback").first

        for show_scores, show_memory, width in product((True, False), (False, True), (1280, 768, 400)):
            with self.subTest(scores=show_scores, memory=show_memory, width=width):
                with self.server_lock:
                    if not show_scores:
                        GroupReport.objects.filter(submission_report_id=report_id).update(score=None)
                    TestReport.objects.filter(pk=57).update(mem_used=2048 if show_memory else 0)
                self.page.set_viewport_size({"width": width, "height": 800})
                self.page.reload()
                columns = report.locator("thead th")
                closed_widths = columns.evaluate_all("cells => cells.map(cell => cell.getBoundingClientRect().width)")
                for expanded in (True, False):
                    toggle.click()
                    expect(toggle).to_have_attribute("aria-expanded", str(expanded).lower())
                    if expanded:
                        expect(feedback).to_be_visible()
                        feedback.evaluate("el => Promise.all(el.closest('.test-feedback-clip').getAnimations().map(animation => animation.finished))")
                        self.assertTrue(
                            feedback.evaluate("el => el.parentElement.clientHeight >= el.getBoundingClientRect().height - 1"),
                            "Feedback is clipped after expansion",
                        )
                        self.assertTrue(feedback.evaluate("el => el.scrollWidth <= el.clientWidth + 1"), "Feedback overflows its cell")
                        self.screenshot(self.page, f"report-widths-{self.browser_name}-{width}-memory-{show_memory}-scores-{show_scores}")
                    else:
                        expect(report.locator(".test-feedback-row").first).to_have_css("display", "none")
                    widths = columns.evaluate_all("cells => cells.map(cell => cell.getBoundingClientRect().width)")
                    for closed, current in zip(closed_widths, widths, strict=True):
                        self.assertAlmostEqual(closed, current, delta=1, msg=f"Column widths changed: {closed_widths} -> {widths}")
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
                    self.assertEqual(bool(scores), show_scores)
                    for score in scores:
                        self.assertEqual(score["lines"], 1, score)
                # Feedback rows must not change the layout relative to a table without them.
                report.locator(".test-feedback-row").evaluate_all("rows => rows.forEach(row => row.remove())")
                without_feedback = columns.evaluate_all("cells => cells.map(cell => cell.getBoundingClientRect().width)")
                for closed, current in zip(closed_widths, without_feedback, strict=True):
                    self.assertAlmostEqual(closed, current, delta=1)

    def assert_report_geometry(self, table):
        failures = table.evaluate(
            r"""table => {
                const failures = [];
                const visible = row => getComputedStyle(row).display !== 'none' &&
                    getComputedStyle(row).visibility !== 'collapse';
                const rows = [...table.querySelectorAll('tbody tr')];
                const near = (a, b, label) => {
                    if (Math.abs(a - b) > 1) failures.push(`${label}: ${a} != ${b}`);
                };
                for (const row of rows.filter(row => row.classList.contains('test-feedback-row'))) {
                    if (!visible(row)) {
                        near(row.getBoundingClientRect().height, 0, 'Closed feedback height');
                        continue;
                    }
                    const previous = row.previousElementSibling;
                    near(row.cells[0].getBoundingClientRect().left,
                         previous.cells[0].getBoundingClientRect().left, 'Left table edge');
                    near(row.cells[1].getBoundingClientRect().left,
                         previous.cells[1].getBoundingClientRect().left, 'Feedback column edge');
                    for (const cell of row.cells) {
                        const style = getComputedStyle(cell);
                        for (const edge of ['Right', 'Left']) {
                            if (parseFloat(style[`border${edge}Width`]) === 0) {
                                failures.push(`Missing ${edge} border on feedback cell`);
                            }
                        }
                    }
                    // Bootstrap paints horizontal borders on tr, vertical borders on td.
                    const rowStyle = getComputedStyle(row);
                    for (const edge of ['Top', 'Bottom']) {
                        if (parseFloat(rowStyle[`border${edge}Width`]) === 0) {
                            failures.push(`Missing ${edge} border on feedback row`);
                        }
                    }
                }
                for (const score of table.querySelectorAll('.group-score')) {
                    const groupClass = [...score.parentElement.classList].find(c => c.startsWith('test-row-'));
                    const groupRows = [...table.querySelectorAll(`tr.${groupClass}`)];
                    let last = groupRows.at(-1);
                    if (last.nextElementSibling?.classList.contains('test-feedback-row') && visible(last.nextElementSibling)) {
                        last = last.nextElementSibling;
                    }
                    near(score.getBoundingClientRect().bottom, last.getBoundingClientRect().bottom, 'Group score bottom');
                }
                const last = rows.filter(visible).at(-1);
                near(table.getBoundingClientRect().bottom, last.getBoundingClientRect().bottom, 'Bottom table edge');
                return failures;
            }"""
        )
        self.assertEqual(failures, [])

    def test_feedback_borders_after_repeated_and_rapid_toggling(self):
        from playwright.sync_api import expect

        with self.server_lock:
            report_id = TestReport.objects.get(pk=57).submission_report_id
            TestReport.objects.filter(submission_report_id=report_id, test_name="4").update(comment="Last test feedback. " * 8)

        for show_scores in (True, False):
            if not show_scores:
                with self.server_lock:
                    GroupReport.objects.filter(submission_report_id=report_id).update(score=None)
            for show_memory in (False, True):
                with self.server_lock:
                    TestReport.objects.filter(pk=57).update(mem_used=2048 if show_memory else 0)
                for width in (1280, 400):
                    with self.subTest(scores=show_scores, memory=show_memory, width=width):
                        self.page.set_viewport_size({"width": width, "height": 800})
                        self.page.reload()
                        report = self.page.locator(".submission-report").first
                        table = report.locator(".table-report")
                        self.assertEqual(table.locator("thead th").count(), 4 + show_memory + show_scores)
                        self.assert_report_geometry(table)
                        toggle = report.locator(".test-feedback-toggle").last
                        row = table.locator(".test-feedback-row").last
                        toggle.click()
                        expect(row.locator(".test-feedback")).to_be_visible()
                        self.assert_report_geometry(table)
                        toggle.click(click_count=3, delay=20)
                        expect(row).to_have_css("display", "none")
                        self.assert_report_geometry(table)
                        toggle.click(click_count=3, delay=20)
                        expect(row.locator(".test-feedback")).to_be_visible()
                        self.assert_report_geometry(table)
                        toggle.click()
                        expect(row).to_have_css("display", "none")

                        for _ in range(3):
                            report.locator(".test-feedback-expand-all").click()
                            expect(table.locator(".test-feedback-row.is-collapsed")).to_have_count(0)
                            self.assert_report_geometry(table)
                            report.locator(".test-feedback-expand-all").click()
                            expect(table.locator(".test-feedback-row:not(.is-collapsed)")).to_have_count(0)
                            self.assert_report_geometry(table)
                        self.screenshot(self.page, f"report-borders-{width}-memory-{show_memory}-scores-{show_scores}")

    def test_feedback_divider_is_continuous_at_different_pixel_scales(self):
        from PIL import Image, ImageColor
        from playwright.sync_api import expect

        for scale in (1, 1.25, 2):
            with self.subTest(scale=scale):
                context = self.new_browser_context("admin", viewport={"width": 1280, "height": 800}, device_scale_factor=scale)
                try:
                    page = context.new_page()
                    page.goto(self.live_server_url + reverse("submission", kwargs={"contest_id": "oi", "submission_id": 7}))
                    report = page.locator(".submission-report").first
                    report.locator(".test-feedback-toggle").first.click()
                    row = report.locator(".test-feedback-row").first
                    expect(row.locator(".test-feedback")).to_be_visible()
                    pixels = Image.open(BytesIO(row.screenshot())).convert("RGB")
                    divider = row.evaluate(
                        """row => {
                            const cell = row.cells[0];
                            return {
                                x: cell.getBoundingClientRect().right - row.getBoundingClientRect().left,
                                color: getComputedStyle(cell).borderRightColor
                            };
                        }"""
                    )
                    expected_color = ImageColor.getrgb(divider["color"])
                    x = round(divider["x"] * scale)
                    # A fractional device scale can antialias a 1px border across neighboring pixels.
                    for y in range(round(2 * scale), pixels.height - round(2 * scale)):
                        self.assertTrue(
                            any(
                                max(abs(a - b) for a, b in zip(pixels.getpixel((column, y)), expected_color, strict=True)) <= 18
                                for column in range(max(0, x - 2), min(pixels.width, x + 3))
                            ),
                            f"Gap in the feedback divider at scale {scale}, y={y}",
                        )
                    self.assert_report_geometry(report.locator(".table-report"))
                finally:
                    context.close()

    def assert_bottom_border_pixels(self, table, scale):
        from PIL import Image, ImageColor

        pixels = Image.open(BytesIO(table.screenshot())).convert("RGB")
        junction = table.evaluate(
            """table => {
                const score = [...table.querySelectorAll('.group-score')].at(-1);
                return {
                    x: score.getBoundingClientRect().left - table.getBoundingClientRect().left,
                    color: getComputedStyle(score).borderLeftColor
                };
            }"""
        )
        color = ImageColor.getrgb(junction["color"])
        x = round(junction["x"] * scale)
        checked_rows = 0
        for y in range(pixels.height - 3 * scale, pixels.height):
            reference = pixels.getpixel((x - 10 * scale, y))
            if max(abs(a - b) for a, b in zip(reference, color, strict=True)) > 18:
                continue
            checked_rows += 1
            for column in range(x - 2 * scale, x + 2 * scale + 1):
                pixel = pixels.getpixel((column, y))
                self.assertLessEqual(
                    max(a - b for a, b in zip(pixel, reference, strict=True)),
                    4,
                    f"Gap in bottom border at scale {scale}, x={column}, y={y}: {pixel} != {reference}",
                )
        self.assertGreater(checked_rows, 0, "The table has no bottom border")

    def test_bottom_border_at_score_junction(self):
        from playwright.sync_api import expect

        with self.server_lock:
            report_id = TestReport.objects.get(pk=57).submission_report_id
            last_test = TestReport.objects.get(submission_report_id=report_id, test_name="4")
            for index, letter in enumerate("abcdefgh"):
                if index:
                    last_test.pk = None
                last_test.test_name = f"4{letter}"
                last_test.comment = "Last group feedback." if index in (1, 2, 3, 5, 6, 7) else ""
                last_test.save()

        for width, scale in product((1280, 400), (1, 2, 4, 5)):
            with self.subTest(width=width, scale=scale):
                context = self.new_browser_context("admin", viewport={"width": width, "height": 800}, device_scale_factor=scale)
                try:
                    page = context.new_page()
                    page.goto(self.live_server_url + reverse("submission", kwargs={"contest_id": "oi", "submission_id": 7}))
                    report = page.locator(".submission-report").first
                    table = report.locator(".table-report")
                    toggle = report.locator(".test-feedback-toggle").last
                    row = table.locator(".test-feedback-row").last
                    self.assert_bottom_border_pixels(table, scale)
                    toggle.click()
                    expect(row.locator(".test-feedback")).to_be_visible()
                    toggle.click()
                    expect(row).to_have_css("display", "none")
                    self.assert_bottom_border_pixels(table, scale)
                finally:
                    context.close()


@skipUnless(os.environ.get("OIOIOI_TEST_FIREFOX") == "1", "Set OIOIOI_TEST_FIREFOX=1 to run the optional Firefox tests")
class TestReportFeedbackFirefox(TestReportFeedback):
    browser_name = "firefox"
