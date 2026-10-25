import html
import re
import urllib.parse

import mistune
from django.http import Http404
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from mistune.util import safe_entity

from oioioi.contests.models import UserResultForProblem
from oioioi.portals.conditions import is_portal_admin
from oioioi.problems.models import Problem

REGISTERED_WIDGETS = []
_block_spoiler_leading_pattern = re.compile(r"^ *>! ?", flags=re.M)
# Same limit as mistune 0.8 had for nested blocks.
_max_spoiler_depth = 6


class PortalRenderer(mistune.HTMLRenderer):
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
            {"summary": html.unescape(summary), "body": mark_safe(text)},
        )

    def table(self, text):
        """Rendering table element. Wrap the header and body in it.

        :param text: rendered ``<thead>`` and ``<tbody>`` of the table.
        """
        return render_to_string("portals/widgets/table.html", {"content": mark_safe(text)})

    def portal_widget(self, text):
        # Already rendered by the widget, must not be escaped.
        return text


def parse_block_center(block, m, state):
    last_token = state.last_token()
    if last_token and last_token["type"] == "paragraph":
        # Like in mistune 0.8, a centered block doesn't interrupt a paragraph.
        return None
    state.append_token({"type": "block_center", "text": m.group("center_text")})
    return m.end()


def parse_block_spoiler(block, m, state):
    if state.depth() >= _max_spoiler_depth:
        # Too deeply nested, render the whole spoiler as plain text.
        state.add_paragraph(m.group(0))
        return m.end()
    # Clean leading >!
    content = _block_spoiler_leading_pattern.sub("", m.group("spoiler_body")).lstrip("\n") + "\n"
    child = state.child_state(content)
    block.parse(child)
    state.append_token(
        {
            "type": "block_spoiler",
            "attrs": {"summary": m.group("spoiler_summary")},
            "children": child.tokens,
        }
    )
    return m.end()


_markdown = mistune.create_markdown(
    renderer=PortalRenderer(escape=True),
    plugins=["strikethrough", "footnotes", "table", "url"],
)
_block_rules = {
    "block_spoiler": (
        r"^ *>!\[(?P<spoiler_summary>[^\n]*)\] *(?P<spoiler_body>(?:\n *>![^\n]*)+)(?:[ \t]*\n)?",
        parse_block_spoiler,
    ),
    # The centered text may span several lines, but not a blank line or a code fence.
    "block_center": (
        r"^ *->(?P<center_text>(?:[^\n]|\n(?![ \t]*(?:$|```|~~~)))*?)<-(?:[ \t]*\n)?",
        parse_block_center,
    ),
}
for _name, (_pattern, _func) in _block_rules.items():
    _markdown.block.register(_name, _pattern, _func, before="fenced_code")
    # Block quotes and list items are parsed with their own rule lists.
    _markdown.block.insert_rule(_markdown.block.block_quote_rules, _name, before="fenced_code")
    _markdown.block.insert_rule(_markdown.block.list_rules, _name, before="fenced_code")


def render_panel(request, panel):
    state = _markdown.block.state_cls()
    state.env["request"] = request
    html, _ = _markdown.parse(panel, state)
    return html


def register_widget(widget):
    """
    Register markdown tag for a portal widget.
    The tag is added as an inline rule of the ``mistune`` 3 parser
    and takes precedence over links and the other inline rules.

    :type widget: object containing the following:
        * :attr:`widget.name` - name of the widget, unique among inline rules
        * :attr:`widget.compiled_tag_regex` - compiled regular expression
            pattern used for identifying markdown tag.  Its pattern is
            embedded into ``mistune``'s combined regex, so it must not use
            ``^`` anchors, inline flags or named groups.
        * :meth:`widget.render` - method (or just function) accepting
            the current request and the corresponding :class:`re.Match`
            instance (named 'm').  Should return a string (rendered widget).
    """
    if widget.name in _markdown.inline.rules or any(w.name == widget.name for w in REGISTERED_WIDGETS):
        raise ValueError(f"Inline tag for widget named {widget.name} has already been registered.")

    # Fail here rather than on every later render if the pattern can't be
    # embedded into the combined regex (see compile_sc in mistune).
    inline = _markdown.inline
    patterns = {**inline.specification, widget.name: widget.compiled_tag_regex.pattern}
    try:
        re.compile("|".join(f"(?P<{name}>{patterns[name]})" for name in [*inline.rules, widget.name]), inline.sc_flag)
    except re.error as e:
        raise ValueError(f"Invalid inline tag for widget named {widget.name}: {e}") from e

    def parse(inline, m, state):
        # Match again on its own, so that group numbers are the widget's
        # and not the ones from the combined regex.
        widget_match = widget.compiled_tag_regex.match(state.src, m.start())
        if widget_match is None:
            return None
        state.append_token({"type": "portal_widget", "raw": widget.render(state.env["request"], widget_match)})
        return widget_match.end()

    _markdown.inline.register(widget.name, widget.compiled_tag_regex.pattern, parse, before="link")

    REGISTERED_WIDGETS.append(widget)


class YouTubeWidget:
    name = "youtube"
    compiled_tag_regex = re.compile(
        r"\[\[" r"YouTube\|([\s\S]+?)" r"\]\](?!\])"  # [[  # YouTube|<url>  # ]]
    )

    def render(self, request, m):
        # 'https://www.youtube.com/watch?v=dVDk7PXNXB8'
        youtube_url = m.group(1).split("|")[-1].strip()
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
    name = "problem_table"
    compiled_tag_regex = re.compile(
        r"\[\["  # [[
        # ProblemTable|... or ProblemTable:<Header>|...
        r"ProblemTable(:.*)?\|(.*)"
        r"\]\](?!\])"  # ]]
    )

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


class RedirectWidget:
    name = "redirect"
    compiled_tag_regex = re.compile(
        r"\[\[" r"Redirect\|(.*)" r"\]\]"  # [[  # Redirect|<url>  # ]]
    )

    @staticmethod
    def render(request, match):
        redirect_url = match.group(1).strip()
        if urllib.parse.urlparse(redirect_url).netloc:
            return "[[Redirect: only relative URLs allowed]]"

        return render_to_string(
            "portals/widgets/redirect.html",
            {"redirect_url": redirect_url, "is_portal_admin": is_portal_admin(request)},
        )


register_widget(RedirectWidget())
