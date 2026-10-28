import re
import urllib.parse
from typing import Protocol, runtime_checkable

import mistune
from django.http import Http404
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from mistune.plugins.table import (
    NP_TABLE_PATTERN,
    TABLE_PATTERN,
    render_table_body,
    render_table_cell,
    render_table_head,
    render_table_row,
    table_in_quote,
)
from mistune.util import safe_entity, unescape

from oioioi.contests.models import UserResultForProblem
from oioioi.portals.conditions import is_portal_admin
from oioioi.problems.models import Problem

REGISTERED_WIDGETS = []
_block_spoiler_leading_pattern = re.compile(r"^ *>! ?", flags=re.M)
_block_center_close_pattern = re.compile(r"<-")
# A centered block may span blank lines, but not a code fence.
_block_center_boundary_pattern = re.compile(r"^[ \t]*(?:```|~~~)", flags=re.M)
_block_center_trailing_pattern = re.compile(r"(?:[ \t]*\n)?")
# Same limit as mistune 0.8 had for nested blocks.
_max_spoiler_depth = 6
_table_aligns = [
    ("center", re.compile(r"^ *:-+: *$")),
    ("left", re.compile(r"^ *:-+ *$")),
    ("right", re.compile(r"^ *-+: *$")),
    (None, re.compile(r"^ *-* *$")),
]
_link_pattern = re.compile(mistune.InlineParser.SPECIFICATION["link"])
_tag_closing_brackets_pattern = re.compile(r"\]\]")


class WidgetError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@runtime_checkable
class Widget(Protocol):
    name: str
    param_regex: re.Pattern[str]

    def render(self, request, match: re.Match[str], /) -> str: ...


class PortalRenderer(mistune.HTMLRenderer):
    def __init__(self, request):
        super().__init__(escape=True)
        self.request = request
        # Since we don't associate the renderer with our parser we have to manually
        # add these renderer functions instead of using the table plugin.
        self.register("table_head", render_table_head)
        self.register("table_body", render_table_body)
        self.register("table_row", render_table_row)
        self.register("table_cell", render_table_cell)

    def text(self, text):
        # Keep HTML entities written by authors (e.g. &nbsp;) working, as in mistune 0.8.
        return safe_entity(text)

    def block_center(self, text):
        return render_to_string("portals/widgets/block-center.html", {"content": mark_safe(text)})

    def block_spoiler(self, text, summary):
        return render_to_string(
            "portals/widgets/block-spoiler.html",
            # The template escapes the summary, so decode entities first
            # to keep them working like in the body text.
            {"summary": unescape(summary), "body": mark_safe(text)},
        )

    def table(self, text):
        """Rendering table element. Wrap the header and body in it.

        :param text: rendered ``<thead>`` and ``<tbody>`` of the table.
        """
        return render_to_string("portals/widgets/table.html", {"content": mark_safe(text)})

    def portal_widget(self, _text, widget: Widget, match: re.Match[str]):
        try:
            return widget.render(self.request, match)
        except WidgetError as e:
            return f'<span class="text-danger">[[{widget.name}: {mistune.escape(e.message)}]]</span>'


def _search_cached(state, pattern, pos):
    """Return the start of the first match of ``pattern`` in ``state.src`` at or after ``pos``,
    or ``len(state.src)`` if there is none.

    The parser only moves forward, so the last result is reused while ``pos`` hasn't
    passed it. Without that, every unclosed ``->`` line would rescan the rest of the input.
    """
    cache = state.__dict__.setdefault("portal_search_cache", {})
    searched_from, found_at = cache.get(pattern, (None, None))
    if searched_from is None or not searched_from <= pos <= found_at:
        match = pattern.search(state.src, pos)
        found_at = match.start() if match else len(state.src)
        cache[pattern] = (pos, found_at)
    return found_at


def parse_block_center(block, m, state):
    last_token = state.last_token()
    if last_token and last_token["type"] == "paragraph":
        # Like in mistune 0.8, a centered block doesn't interrupt a paragraph.
        return None
    close = _search_cached(state, _block_center_close_pattern, m.end())
    if close >= _search_cached(state, _block_center_boundary_pattern, m.end()):
        return None
    state.append_token({"type": "block_center", "text": state.src[m.end() : close]})
    return _block_center_trailing_pattern.match(state.src, close + 2).end()


def _spoiler_depth(state):
    depth = 0
    while state:
        depth += getattr(state, "portal_spoiler", False)
        state = state.parent
    return depth


def parse_block_spoiler(block, m, state):
    # Count only spoilers, not list items or block quotes, like mistune 0.8.
    if _spoiler_depth(state) >= _max_spoiler_depth:
        # Too deeply nested, render the whole spoiler as plain text.
        state.add_paragraph(m.group(0))
        return m.end()
    # Clean leading >!
    content = _block_spoiler_leading_pattern.sub("", m.group("spoiler_body")).lstrip("\n") + "\n"
    child = state.child_state(content)
    child.portal_spoiler = True
    block.parse(child)
    state.append_token(
        {
            "type": "block_spoiler",
            "attrs": {"summary": m.group("spoiler_summary")},
            "children": child.tokens,
        }
    )
    return m.end()


def _is_valid_widget_name(text: str):
    return all(c.isalnum() or c in "_-" for c in text)


def _split_table_cells(text: str):
    """Split a table row at ``|``, except escaped ones and ones inside widget tags like ``[[YouTube|...]]``."""
    cells = []
    start = pos = 0
    next_tag_end = -1

    while pos < len(text):
        if next_tag_end is not None and text.startswith("[[", pos):
            if next_tag_end < pos:
                next_tag_end = text.find("]]", pos + 2)
                if next_tag_end == -1:
                    next_tag_end = None
                    continue

            pos = next_tag_end + 2
        elif text[pos] == "\\":
            pos += 2
        elif text[pos] == "|":
            cells.append(text[start:pos].strip())
            start = pos + 1
            pos += 1
        else:
            pos += 1

    cells.append(text[start:].strip())
    return cells


def _strip_pipe_table_row(line):
    text = line.strip(" \t\n")
    if len(text) < 2 or not text.startswith("|") or not text.endswith("|"):
        return None
    return text[1:-1]


def _strip_nptable_row(line):
    text = line.rstrip(" \t\n")
    if "|" not in text:
        return None
    return text


def _table_cells(cells, aligns, head):
    return [{"type": "table_cell", "text": text, "attrs": {"align": aligns[i] if i < len(aligns) else None, "head": head}} for i, text in enumerate(cells)]


def _make_table_parser(strip_row):
    def parse(block, m, state):
        header = strip_row(m.group(0))
        pos = m.end()
        delimiter_line = state.get_line(pos)
        delimiter = strip_row(delimiter_line)
        if header is None or delimiter is None:
            return None
        headers = _split_table_cells(header)
        aligns = []
        for cell in _split_table_cells(delimiter):
            align = next((align for align, pattern in _table_aligns if pattern.match(cell)), False)
            if align is False:
                return None
            aligns.append(align)
        if len(aligns) != len(headers):
            return None
        pos += len(delimiter_line)

        rows = []
        while pos < state.cursor_max:
            line = state.get_line(pos)
            row = strip_row(line)
            if row is None:
                break
            cells = _split_table_cells(row)
            # Like mistune 0.8, a row with too few or too many cells still belongs to the table.
            cells += [""] * (len(aligns) - len(cells))
            rows.append({"type": "table_row", "children": _table_cells(cells, aligns, head=False)})
            pos += len(line)

        head = {"type": "table_head", "children": _table_cells(headers, aligns, head=True)}
        state.append_token({"type": "table", "children": [head, {"type": "table_body", "children": rows}]})
        return pos

    return parse


def table_plugin(md):
    """mistune's table plugin, but with rows parsed like in mistune 0.8 and widget tags kept in one cell.

    mistune 3 drops the whole table when a row has a different number of cells than the header.
    """
    md.block.register("table", TABLE_PATTERN, _make_table_parser(_strip_pipe_table_row))
    md.block.register("nptable", NP_TABLE_PATTERN, _make_table_parser(_strip_nptable_row))
    table_in_quote(md)


_markdown = mistune.create_markdown(
    renderer=None,
    plugins=["strikethrough", "footnotes", table_plugin, "url"],
)
_block_rules = {
    "block_spoiler": (
        r"^ {0,3}>!\[(?P<spoiler_summary>[^\n]*)\] *(?P<spoiler_body>(?:\n *>![^\n]*)+)(?:[ \t]*\n)?",
        parse_block_spoiler,
    ),
    # Only the opening, parse_block_center finds the closing <-.
    "block_center": (r"^ {0,3}->", parse_block_center),
}
for _name, (_pattern, _func) in _block_rules.items():
    _markdown.block.register(_name, _pattern, _func, before="fenced_code")
    # Block quotes and list items are parsed with their own rule lists.
    _markdown.block.insert_rule(_markdown.block.block_quote_rules, _name, before="fenced_code")
    _markdown.block.insert_rule(_markdown.block.list_rules, _name, before="fenced_code")


def render_panel(request, panel):
    tokens, state = _markdown.parse(panel)
    assert isinstance(tokens, list)
    html = PortalRenderer(request).render_tokens(tokens, state)
    return html


def register_widget(widget: Widget):
    """
    Register markdown tag for a portal widget.
    The tag is added as an inline rule of the ``mistune`` 3 parser
    and takes precedence over links and the other inline rules.

    :type widget: object containing the following:
        * :attr:`widget.name` - name of the widget, unique among inline rules.
            Will be used as the keyword when looking for matching tags.
        * :attr:`widget.param_regex` - compiled regular expression
            pattern used for parsing tag contents.
        * :meth:`widget.render` - method (or just function) accepting
            the current request and the corresponding :class:`re.Match`
            instance (named 'm').  Should return a string (rendered widget).
            May throw WidgetError to show a simple user-visible error.
    """
    if not isinstance(widget, Widget):
        raise ValueError("Widget has incorrect shape")
    if not _is_valid_widget_name(widget.name):
        raise ValueError(f"Invalid widget name {widget.name}")
    if any(widget.name == w.name for w in REGISTERED_WIDGETS):
        raise ValueError(f"Widget named {widget.name} has already been registered")

    def parse(inline, m, state):
        end = _search_cached(state, _tag_closing_brackets_pattern, m.end())

        # Fallback to parsing as a link if this does not look like a valid tag.
        if end == len(state.src) or not (match := widget.param_regex.fullmatch(state.src, m.start() + 2, end)):
            return inline.parse_link(_link_pattern.match(state.src, m.start()), state)

        state.append_token({"type": "portal_widget", "attrs": {"widget": widget, "match": match}, "raw": state.src[m.start() + 2 : end]})
        return end + 2

    pattern = rf"\[\[{widget.name}"
    parser_name = f"portal_widget{len(REGISTERED_WIDGETS)}"
    _markdown.inline.register(parser_name, pattern, parse, before="link")

    REGISTERED_WIDGETS.append(widget)


class YouTubeWidget:
    name = "YouTube"
    # YouTube|<url> or YouTube|<title>|<url>
    param_regex = re.compile(r"YouTube\|(?:[^|\n]*\|)?([^\n]*)")

    def render(self, _request, m):
        # 'https://www.youtube.com/watch?v=dVDk7PXNXB8'
        youtube_url = m.group(1)
        # We must use the embed player, so if user just copies link
        # from the browser when he is on YT, we must transform
        # the link in order to be able to play the movie
        parsed = urllib.parse.urlparse(youtube_url)
        try:
            video_id = urllib.parse.parse_qs(parsed.query)["v"][0]
        except KeyError:
            return ""
        # 'https://www.youtube.com/embed/dVDk7PXNXB8'
        youtube_embed_url = f"https://www.youtube.com/embed/{video_id}"
        return render_to_string("portals/widgets/youtube.html", {"youtube_embed_url": youtube_embed_url})


register_widget(YouTubeWidget())


class ProblemTableWidget:
    name = "ProblemTable"
    # ProblemTable|... or ProblemTable:<Header>|...
    param_regex = re.compile(r"ProblemTable(:[^|\n]*)?\|([^\n]*)")

    @staticmethod
    def site_key_from_link(link):
        if "//" in link:
            link = link.split("//")[1]
        if "/" not in link:
            return None
        rel_path = "/" + link.split("/", 1)[1]
        try:
            resolved = resolve(rel_path)
        except Http404:
            return None
        if "site_key" not in resolved.kwargs:
            return None
        return resolved.kwargs["site_key"]

    @staticmethod
    def parse_problems(m):
        links = [link.strip() for link in m.group(2).split(";") if link.strip()]
        keys = [ProblemTableWidget.site_key_from_link(link) for link in links if ProblemTableWidget.site_key_from_link(link) is not None]
        problems = Problem.objects.filter(problemsite__url_key__in=keys).select_related("problemsite").prefetch_related("names")
        problem_map = {pr.problemsite.url_key: pr for pr in problems}
        problems = [problem_map[key] for key in keys if key in problem_map]
        return problems

    def get_problem_ids(self, m):
        return [problem.id for problem in self.parse_problems(m)]

    def render(self, request, m):
        if not m.group(2).strip(" ;"):
            return ""

        problems = self.parse_problems(m)

        rows = []

        for problem in problems:
            row = {
                "url": reverse("problem_site", kwargs={"site_key": problem.problemsite.url_key}),
                "name": problem.name,
            }

            def fill_row_with_score(row_, problem_):
                if not request.user.is_authenticated:
                    return False
                result = UserResultForProblem.objects.filter(
                    user=request.user,
                    problem_instance=problem_.main_problem_instance,
                    submission_report__isnull=False,
                ).first()
                if result is None:
                    return False
                row_["score"] = str(result.score.to_int())
                row_["submission_url"] = reverse(
                    "submission",
                    kwargs={"submission_id": result.submission_report.submission.id},
                )
                return True

            row["score_exists"] = fill_row_with_score(row, problem)
            rows.append(row)

        header = _("Problem Name")
        if m.group(1):
            header = m.group(1)[1:]

        return render_to_string("portals/widgets/problem-table.html", {"problems": rows, "header": header})


register_widget(ProblemTableWidget())


def collect_problems(panel):
    """Parse panel content and return a list of accessible problems."""

    tokens, _ = _markdown.parse(panel)
    assert isinstance(tokens, list)

    def walk_tokens(tokens, result):
        for token in tokens:
            if token["type"] == "portal_widget" and hasattr(widget := token["attrs"]["widget"], "get_problem_ids"):
                match = token["attrs"]["match"]
                result += widget.get_problem_ids(match)
            elif children := token.get("children", None):
                walk_tokens(children, result)

    result = []
    walk_tokens(tokens, result)

    return result


class RedirectWidget:
    name = "Redirect"
    # Redirect|<url>
    param_regex = re.compile(r"Redirect\|([^\n]*)")

    @staticmethod
    def render(request, match):
        redirect_url = match.group(1).strip()
        # Rejects other hosts (also "//host" and "/\host") and schemes such as javascript:.
        if not url_has_allowed_host_and_scheme(redirect_url, allowed_hosts=None):
            raise WidgetError("only relative URLs allowed")

        return render_to_string(
            "portals/widgets/redirect.html",
            {"redirect_url": redirect_url, "is_portal_admin": is_portal_admin(request)},
        )


register_widget(RedirectWidget())
