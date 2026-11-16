"""Browser regression tests for typeahead / autocomplete inputs (#718).

Covers all three call sites:
1. ``oioioi/base/static/common/user_selection.js`` (``init_user_selection``)
2. ``oioioi/contests/static/common/contest_hints.js`` (``init_search_selection`` on ``/contest/``)
3. ``oioioi/problems/static/common/tag_selection.js`` (``init_search_selection`` on ``/problemset/``)

Run with ``./easy_toolbox.py exec ../oioioi/test.sh -m browser oioioi/base/tests/test_typeahead_browser.py``.
Set ``OIOIOI_SCREENSHOT_DIR`` as an optional debug flag to save step-by-step screenshots.
"""

import os
from urllib.parse import parse_qs, urlparse

from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import StyledBrowserTestCase
from oioioi.contests.current_contest import ContestMode
from oioioi.problems.models import (
    OriginInfoValue,
    OriginInfoValueLocalization,
    OriginTag,
    OriginTagLocalization,
    Problem,
)

VIEWPORT = {"width": 1280, "height": 800}


class TypeaheadBrowserTestCase(StyledBrowserTestCase):
    """Base class for testing typeahead/autocomplete widgets in Chromium."""

    def setUp(self):
        super().setUp()
        self.page_errors = []
        self._debug_step = 0
        self._last_page = None

    def _debug_screenshot(self, page, label):
        """Saves a step screenshot only when ``OIOIOI_SCREENSHOT_DIR`` is set for debugging."""
        directory = os.environ.get("OIOIOI_SCREENSHOT_DIR")
        if directory and page is not None:
            self._debug_step += 1
            path = os.path.join(directory, f"{self._testMethodName}-{self._debug_step:02d}-{label}.png")
            page.screenshot(path=path, full_page=True)

    def open(self, url, username=None, viewport=VIEWPORT):
        """Opens ``url`` in a new browser context and records any JS or console errors."""
        context = self.new_browser_context(username, viewport=viewport)
        self.addCleanup(context.close)
        page = context.new_page()
        self._last_page = page
        page.on("pageerror", lambda exc: self.page_errors.append(f"uncaught exception on {url}: {exc}"))
        page.on(
            "console",
            lambda msg: msg.type == "error" and self.page_errors.append(f"console.error on {url}: {msg.text}"),
        )
        response = page.goto(self.live_server_url + url, wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertLess(response.status, 400, url)
        return page

    def assertNoPageErrors(self):
        self._debug_screenshot(self._last_page, "end")
        self.assertEqual(self.page_errors, [])

    def dropdown_menu(self, page, input_selector):
        """Returns a locator for the typeahead dropdown menu attached to ``input_selector``."""
        return page.locator(f"{input_selector} ~ .dropdown-menu, {input_selector} + .dropdown-menu")

    def dropdown_items(self, page, input_selector):
        """Returns a locator for visible option items in the typeahead dropdown."""
        return self.dropdown_menu(page, input_selector).locator(".dropdown-item:visible, li:visible a")

    def type_query(self, page, input_selector, query, wait_for_hints=True):
        """Focuses ``input_selector``, enters ``query``, and optionally waits for the hints AJAX response."""
        locator = page.locator(input_selector)
        locator.focus()
        # Reset to empty first so bootstrap-3-typeahead updates its internal `this.value`
        # even when a previous selection's `updater` cleared the input to "".
        locator.fill("")
        locator.dispatch_event("input")
        if wait_for_hints:
            hints_url = locator.get_attribute("data-hints-url")
            with page.expect_response(lambda r: hints_url in r.url and r.status == 200):
                locator.fill(query)
        elif query:
            locator.fill(query)

    def wait_for_hints(self, page, input_selector):
        """Waits until the dropdown menu for ``input_selector`` is visible and returns its item texts."""
        menu = self.dropdown_menu(page, input_selector)
        menu.wait_for(state="visible")
        self._debug_screenshot(page, "hints")
        items = self.dropdown_items(page, input_selector)
        return [text.strip() for text in items.all_inner_texts()]

    def assert_dropdown_hidden(self, page, input_selector):
        """Asserts that the typeahead dropdown for ``input_selector`` is hidden or not in the DOM."""
        menu = self.dropdown_menu(page, input_selector)
        menu.wait_for(state="hidden")
        self.assertFalse(menu.is_visible())

    def click_hint(self, page, input_selector, text):
        """Clicks the visible dropdown item whose text matches ``text``."""
        menu = self.dropdown_menu(page, input_selector)
        menu.wait_for(state="visible")
        item = self.dropdown_items(page, input_selector).filter(has_text=text).first
        item.hover()
        item.click()
        self._debug_screenshot(page, "selected")


class TestUserSelectionTypeahead(TypeaheadBrowserTestCase):
    """Tests ``init_user_selection`` (``oioioi/base/static/common/user_selection.js``)."""

    fixtures = ["test_users", "test_contest"]

    def _open_admin_user_menu(self):
        page = self.open(reverse("contest_dashboard", kwargs={"contest_id": "c"}), username="test_admin")
        page.click("#navbar-username")
        page.wait_for_selector("#user-info", state="visible")
        return page

    def test_min_length_and_mouse_selection(self):
        page = self._open_admin_user_menu()

        # minLength is 2: a 1-character query must not open the dropdown.
        self.type_query(page, "#user-info", "t", wait_for_hints=False)
        self.assert_dropdown_hidden(page, "#user-info")

        # 2+ characters fetch hints from contest_user_hints and display matching users.
        self.type_query(page, "#user-info", "test_user")
        hints = self.wait_for_hints(page, "#user-info")
        self.assertIn("test_user (Test User)", hints)
        self.assertIn("test_user2 (Test User 2)", hints)

        # Clicking an item populates the input and closes the dropdown.
        self.click_hint(page, "#user-info", "test_user2 (Test User 2)")
        self.assertEqual(page.input_value("#user-info"), "test_user2 (Test User 2)")
        self.assert_dropdown_hidden(page, "#user-info")
        self.assertNoPageErrors()

    def test_keyboard_navigation_and_selection(self):
        page = self._open_admin_user_menu()

        self.type_query(page, "#su-username", "test_user")
        hints = self.wait_for_hints(page, "#su-username")
        self.assertGreaterEqual(len(hints), 2)

        # Navigate with ArrowDown and confirm selection with Enter.
        page.locator("#su-username").press("ArrowDown")
        page.locator("#su-username").press("Enter")
        self.assertIn(page.input_value("#su-username"), hints)
        self.assert_dropdown_hidden(page, "#su-username")
        self.assertNoPageErrors()

    @override_settings(NUM_HINTS=2)
    def test_num_hints_limit(self):
        page = self._open_admin_user_menu()

        self.type_query(page, "#user-info", "test_")
        hints = self.wait_for_hints(page, "#user-info")
        self.assertEqual(len(hints), 2)
        self.assertNoPageErrors()


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestContestHintsTypeahead(TypeaheadBrowserTestCase):
    """Tests ``init_search_selection`` in ``oioioi/contests/static/common/contest_hints.js``."""

    fixtures = ["test_contest_search", "test_contest", "test_extra_contests"]

    def test_hints_filtering_escape_and_mouse_selection(self):
        page = self.open(reverse("select_contest"))

        # 1 character does not trigger hints.
        self.type_query(page, "#filter_input", "A", wait_for_hints=False)
        self.assert_dropdown_hidden(page, "#filter_input")

        # 2+ characters show non-archived matching contests.
        self.type_query(page, "#filter_input", "AA")
        hints = self.wait_for_hints(page, "#filter_input")
        self.assertCountEqual(hints, ["AAAcontest", "AA contest"])

        # Escape closes the dropdown without clearing the input.
        page.locator("#filter_input").press("Escape")
        self.assert_dropdown_hidden(page, "#filter_input")
        self.assertEqual(page.input_value("#filter_input"), "AA")

        # Backspacing to empty hides the dropdown (matcher returns false on empty input).
        self.type_query(page, "#filter_input", "", wait_for_hints=False)
        self.assert_dropdown_hidden(page, "#filter_input")

        # Re-type and click a hint.
        self.type_query(page, "#filter_input", "AA")
        self.wait_for_hints(page, "#filter_input")
        self.click_hint(page, "#filter_input", "AAAcontest")

        expected_url = reverse("filter_contests", kwargs={"filter_value": "AAAcontest"})
        if urlparse(page.url).path != expected_url:
            # NOTE: npm's bootstrap-3-typeahead 4.0.2 ignores followLinkOnSelect/itemLink (#488)
            # and only updates the input value; once #718 is resolved it may navigate directly.
            self.assertEqual(page.input_value("#filter_input"), "AAAcontest")
            with page.expect_navigation():
                page.locator("#filter_form button[type=submit]").click()
        self.assertEqual(urlparse(page.url).path, expected_url)
        self.assertNoPageErrors()

    def test_autoselect_false_does_not_pick_first_hint_on_enter(self):
        """With autoSelect: false, pressing Enter without highlighting an item does not overwrite the input with a hint."""
        page = self.open(reverse("select_contest"))

        self.type_query(page, "#filter_input", "AA")
        self.wait_for_hints(page, "#filter_input")

        page.locator("#filter_input").press("Enter")
        expected_url = reverse("filter_contests", kwargs={"filter_value": "AA"})
        if urlparse(page.url).path != expected_url:
            self.assertEqual(page.input_value("#filter_input"), "AA")
            with page.expect_navigation():
                page.locator("#filter_form button[type=submit]").click()
        self.assertEqual(urlparse(page.url).path, expected_url)
        self.assertNoPageErrors()

    def test_keyboard_select_hint(self):
        page = self.open(reverse("select_contest"))

        self.type_query(page, "#filter_input", "DA")
        hints = self.wait_for_hints(page, "#filter_input")
        self.assertEqual(hints, ["DA contest"])

        page.locator("#filter_input").press("ArrowDown")
        page.locator("#filter_input").press("Enter")

        expected_url = reverse("filter_contests", kwargs={"filter_value": "DA contest"})
        if urlparse(page.url).path != expected_url:
            self.assertEqual(page.input_value("#filter_input"), "DA contest")
            with page.expect_navigation():
                page.locator("#filter_form button[type=submit]").click()
        self.assertEqual(urlparse(page.url).path, expected_url)
        self.assertNoPageErrors()


@override_settings(PROBLEM_TAGS_VISIBLE=True, LANGUAGE_CODE="en")
class TestProblemsetTagSelectionTypeahead(TypeaheadBrowserTestCase):
    """Tests ``init_search_selection`` in ``oioioi/problems/static/common/tag_selection.js``."""

    fixtures = [
        "test_problem_search",
        "test_origin_tags",
        "test_algorithm_tags",
        "test_difficulty_tags",
    ]

    def setUp(self):
        super().setUp()
        with self.server_lock:
            # test_origin_tags.json omits the language field on OriginInfoValueLocalization rows.
            OriginInfoValueLocalization.objects.filter(language="").update(language="en")

    def _active_tags(self, page):
        """Returns ``[name, value, text]`` lists for all active search tag badges in ``#tag-row``."""
        return page.eval_on_selector_all(
            "#tag-row .search-tag-root:has(input:not([disabled]))",
            """nodes => nodes.map(node => {
                const input = node.querySelector('input');
                const text = node.querySelector('.search-tag-text');
                return [input.name, input.value, text.textContent.trim()];
            })""",
        )

    def test_problem_hint_selection(self):
        page = self.open(reverse("problemset_main"))

        self.type_query(page, "#problemsite_search", "Zadan")
        hints = self.wait_for_hints(page, "#problemsite_search")
        self.assertIn("Zadanko", hints)

        self.click_hint(page, "#problemsite_search", "Zadanko")
        # Selecting a problem hint must not create any tag badges.
        self.assertEqual(self._active_tags(page), [])
        expected_url = reverse("problem_site", kwargs={"site_key": "1"})
        if urlparse(page.url).path != expected_url:
            self.assertEqual(page.input_value("#problemsite_search"), "Zadanko")
        self.assertNoPageErrors()

    def test_algorithm_and_difficulty_tags_deduplication_and_removal(self):
        page = self.open(reverse("problemset_main"))

        # Add an algorithm tag ("dp" -> badge text is the canonical value "dp").
        self.type_query(page, "#problemsite_search", "dp")
        self.wait_for_hints(page, "#problemsite_search")
        self.click_hint(page, "#problemsite_search", "Dynamic programming")

        self.assertEqual(page.input_value("#problemsite_search"), "")
        self.assertEqual(self._active_tags(page), [["algorithm", "dp", "dp"]])

        # Selecting the same algorithm tag again must not create a duplicate badge.
        self.type_query(page, "#problemsite_search", "dp")
        self.wait_for_hints(page, "#problemsite_search")
        self.click_hint(page, "#problemsite_search", "Dynamic programming")
        self.assertEqual(self._active_tags(page), [["algorithm", "dp", "dp"]])

        # Add a difficulty tag ("easy" -> badge text is the localized name "Easy").
        self.type_query(page, "#problemsite_search", "easy")
        self.wait_for_hints(page, "#problemsite_search")
        self.click_hint(page, "#problemsite_search", "Easy")

        self.assertEqual(page.input_value("#problemsite_search"), "")
        self.assertEqual(
            self._active_tags(page),
            [
                ["algorithm", "dp", "dp"],
                ["difficulty", "easy", "Easy"],
            ],
        )

        # Clicking the remove icon on the algorithm badge removes only that badge.
        page.locator("#tag-row .tag-label-algorithm .search-tag-remove").click()
        self.assertEqual(self._active_tags(page), [["difficulty", "easy", "Easy"]])
        self.assertNoPageErrors()

    def test_origin_category_drilldown_and_group_removal(self):
        """Selecting a category hint reloads the menu with values; selecting a value creates grouped badges."""
        page = self.open(reverse("problemset_main"))

        # Query matching a single OriginTag ("pa") returns both the tag and its categories ("category-menu").
        self.type_query(page, "#problemsite_search", "Potyczki")
        hints = self.wait_for_hints(page, "#problemsite_search")
        self.assertIn("Potyczki Algorytmiczne", hints)
        self.assertIn("Potyczki Algorytmiczne - Year", hints)
        self.assertIn("Potyczki Algorytmiczne - Round", hints)

        # Selecting "Potyczki Algorytmiczne - Year" switches source to get_origininfocategory_hints
        # and immediately reloads the dropdown with year values.
        with page.expect_response(lambda r: "get_origininfocategory_hints" in r.url and r.status == 200):
            self.click_hint(page, "#problemsite_search", "Potyczki Algorytmiczne - Year")

        self.assertEqual(page.input_value("#problemsite_search"), "Potyczki Algorytmiczne")
        self.assertEqual(self._active_tags(page), [])
        category_hints = self.wait_for_hints(page, "#problemsite_search")
        self.assertIn("Potyczki Algorytmiczne 2011", category_hints)

        # Selecting "Potyczki Algorytmiczne 2011" creates #origintag-group-pa with parent "pa" and child "2011",
        # clears the input, and resets the source back to default.
        self.click_hint(page, "#problemsite_search", "Potyczki Algorytmiczne 2011")
        self.assertEqual(page.input_value("#problemsite_search"), "")
        self.assertTrue(page.locator("#origintag-group-pa").is_visible())
        self.assertEqual(
            self._active_tags(page),
            [
                ["origin", "pa", "pa"],
                ["origin", "pa_2011", "2011"],
            ],
        )

        # Source is reset to default: typing "dp" now fetches normal search hints again.
        self.type_query(page, "#problemsite_search", "dp")
        hints = self.wait_for_hints(page, "#problemsite_search")
        self.assertIn("Dynamic programming", hints)
        page.locator("#problemsite_search").press("Escape")
        self.assert_dropdown_hidden(page, "#problemsite_search")

        # Clicking the parent origin badge ("pa") removes the entire #origintag-group-pa container.
        page.locator("#origintag-group-pa .search-tag-root").first.click()
        self.assertEqual(page.locator("#origintag-group-pa").count(), 0)
        self.assertEqual(self._active_tags(page), [])
        self.assertNoPageErrors()

    def test_multiple_origintags_drilldown_and_fallback_to_default_source(self):
        """When multiple OriginTags match, selecting one reloads the menu via ``get_selected_origintag_hints``."""
        with self.server_lock:
            OriginTagLocalization.objects.create(
                origin_tag_id=2,
                language="en",
                full_name="Olimpiada Informatyczna",
            )

        page = self.open(reverse("problemset_main"))

        # Both "Potyczki Algorytmiczne" and "Olimpiada Informatyczna" match "ty", so both have trigger="origintag-menu"
        # and category hints are NOT shown yet.
        self.type_query(page, "#problemsite_search", "ty")
        hints = self.wait_for_hints(page, "#problemsite_search")
        self.assertIn("Potyczki Algorytmiczne", hints)
        self.assertIn("Olimpiada Informatyczna", hints)
        self.assertNotIn("Potyczki Algorytmiczne - Year", hints)

        # Selecting "Potyczki Algorytmiczne" triggers get_selected_origintag_hints and reloads the menu
        # with the tag and its categories.
        with page.expect_response(lambda r: "get_selected_origintag_hints" in r.url and r.status == 200):
            self.click_hint(page, "#problemsite_search", "Potyczki Algorytmiczne")

        self.assertEqual(page.input_value("#problemsite_search"), "Potyczki Algorytmiczne")
        self.assertEqual(self._active_tags(page), [])
        reloaded_hints = self.wait_for_hints(page, "#problemsite_search")
        self.assertIn("Potyczki Algorytmiczne", reloaded_hints)
        self.assertIn("Potyczki Algorytmiczne - Year", reloaded_hints)
        self.assertIn("Potyczki Algorytmiczne - Round", reloaded_hints)

        # Editing the query so it no longer starts with "Potyczki Algorytmiczne" falls back to the default source.
        self.type_query(page, "#problemsite_search", "dp")
        fallback_hints = self.wait_for_hints(page, "#problemsite_search")
        self.assertIn("Dynamic programming", fallback_hints)
        self.assertNoPageErrors()

    def test_submit_search_form_with_selected_tags(self):
        with self.server_lock:
            pa = OriginTag.objects.get(name="pa")
            pa_2011 = OriginInfoValue.objects.get(parent_tag=pa, value="2011")
            pa_r1 = OriginInfoValue.objects.get(parent_tag=pa, value="r1")
            pa_r2 = OriginInfoValue.objects.get(parent_tag=pa, value="r2")

            p_match = Problem.objects.get(pk=6)  # "Potagowany"
            p_other = Problem.objects.get(pk=1)  # "Zadanko"
            pa.problems.add(p_match, p_other)
            pa_2011.problems.add(p_match, p_other)
            pa_r1.problems.add(p_match)
            pa_r2.problems.add(p_other)

        page = self.open(reverse("problemset_main"))

        # Add origin info tags "pa_2011" and "pa_r1" and submit the form.
        self.type_query(page, "#problemsite_search", "pa_2011")
        self.wait_for_hints(page, "#problemsite_search")
        self.click_hint(page, "#problemsite_search", "Potyczki Algorytmiczne 2011")

        self.type_query(page, "#problemsite_search", "pa_r1")
        self.wait_for_hints(page, "#problemsite_search")
        self.click_hint(page, "#problemsite_search", "Potyczki Algorytmiczne Round 1")

        with page.expect_navigation():
            page.locator("#problemsite_search-form button[type=submit]").click()

        query_params = parse_qs(urlparse(page.url).query)
        self.assertEqual(query_params.get("origin"), ["pa", "pa_2011", "pa_r1"])
        self.assertTrue(page.locator("td", has_text="Potagowany").is_visible())
        self.assertEqual(page.locator("td", has_text="Zadanko").count(), 0)
        self.assertNoPageErrors()
