import re

import urllib.parse
from django.conf import settings
from django.http import Http404
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from mistune import BlockLexer, InlineGrammar, InlineLexer, Markdown, Renderer

from oioioi.contests.models import UserResultForProblem
from oioioi.portals.conditions import is_portal_admin
from oioioi.problems.models import Problem

REGISTERED_WIDGETS = []
_block_spoiler_leading_pattern = re.compile(r'^ *>! ?', flags=re.M)


class PortalInlineGrammar(InlineGrammar):
    pass


class PortalRenderer(Renderer):
    def block_center(self, text):
        return render_to_string(
            'portals/widgets/block-center.html', {'content': mark_safe(text)}
        )

    def block_spoiler(self, summary, body):
        return render_to_string(
            'portals/widgets/block-spoiler.html',
            {'summary': summary, 'body': mark_safe(body)},
        )

    def table(self, header, body):
        """Rendering table element. Wrap header and body in it.

        :param header: header part of the table.
        :param body: body part of the table.
        """
        return render_to_string(
            'portals/widgets/table.html',
            {'header': mark_safe(header), 'body': mark_safe(body)},
        )


class PortalInlineLexer(InlineLexer):
    default_rules = InlineLexer.default_rules[:]

    def __init__(self, request, renderer, rules=None, **kwargs):
        self.request = request
        if rules is None:
            rules = PortalInlineGrammar()
        super(PortalInlineLexer, self).__init__(renderer, rules, **kwargs)


class PortalBlockLexer(BlockLexer):
    default_rules = BlockLexer.default_rules[:]

    def __init__(self, *args, **kwargs):
        super(PortalBlockLexer, self).__init__(*args, **kwargs)
        self._blockspoiler_depth = 0

        self.rules.block_spoiler = re.compile(
            r'^ *>!\[([^\n]*)\] *((?:\n *>![^\n]*)+)',
            flags=re.DOTALL | re.M,
        )
        self.rules.block_center = re.compile(r'^ *->(.*?)<-', re.DOTALL)
        # Insert before 'block_code'
        if 'block_center' not in self.default_rules:
            self.default_rules.insert(
                self.default_rules.index('block_code'), 'block_center'
            )
        if 'block_spoiler' not in self.default_rules:
            self.default_rules.insert(0, 'block_spoiler')

    def parse_block_center(self, m):
        self.tokens.append(
            {
                'type': 'block_center',
                'text': m.group(1),
            }
        )

    def parse_block_spoiler(self, m):
        self._blockspoiler_depth += 1

        if self._blockspoiler_depth > self._max_recursive_depth:
            self.parse_text(m)
        else:
            self.tokens.append({'type': 'block_spoiler', 'summary': m.group(1)})
            # Clean leading >!
            content = _block_spoiler_leading_pattern.sub("", m.group(2))
            self.parse(content)
            self.tokens.append({'type': 'block_spoiler_end'})

        self._blockspoiler_depth -= 1


class PortalMarkdown(Markdown):
    def __init__(self, request):
        renderer = PortalRenderer(escape=True)
        inline_lexer = PortalInlineLexer(request, renderer)
        block_lexer = PortalBlockLexer()
        super(PortalMarkdown, self).__init__(
            renderer, inline=inline_lexer, block=block_lexer
        )

    def output_block_center(self):
        return self.renderer.block_center(self.inline(self.token['text']))

    def output_block_spoiler(self):
        spoiler_summary = self.token['summary']
        body = self.renderer.placeholder()
        while self.pop()['type'] != 'block_spoiler_end':
            body += self.tok()
        return self.renderer.block_spoiler(spoiler_summary, body)


def render_panel(request, panel):
    return PortalMarkdown(request).render(panel)


def register_widget(widget):
    """
    Register markdown tag for a portal widget.
    See ``mistune`` docs for more info.

    :type widget: object containing the following:
        * :attr:`widget.name` - name of the widget
        * :attr:`widget.compiled_tag_regex` - compiled regular expression
            pattern used for identifying markdown tag
        * :meth:`widget.render` - method (or just function) accepting
            corresponding :class:`re.MatchObject` instance as the only
            parameter (named 'm').  Should return a string (rendered widget).
    """
    if hasattr(PortalInlineGrammar, widget.name):
        raise ValueError(
            'Inline tag for widget named %s has already been '
            'registered.' % widget.name
        )
    PortalInlineLexer.default_rules.insert(0, widget.name)
    setattr(PortalInlineGrammar, widget.name, widget.compiled_tag_regex)

    def func(self, m):
        return widget.render(self.request, m)

    setattr(PortalInlineLexer, 'output_' + widget.name, func)

    REGISTERED_WIDGETS.append(widget)


class YouTubeWidget(object):
    name = 'youtube'
    compiled_tag_regex = re.compile(
        r'\[\[' r'YouTube\|([\s\S]+?)' r'\]\](?!\])'  # [[  # YouTube|<url>  # ]]
    )

    def render(self, request, m):
        # 'https://www.youtube.com/watch?v=dVDk7PXNXB8'
        youtube_url = m.group(1).split('|')[-1].strip()
        # We must use the embed player, so if user just copies link
        # from the browser when he is on YT, we must transform
        # the link in order to be able to play the movie
        parsed = urllib.parse.urlparse(youtube_url)
        try:
            video_id = urllib.parse.parse_qs(parsed.query)['v'][0]
        except KeyError:
            return ''
        # 'https://www.youtube.com/embed/dVDk7PXNXB8'
        youtube_embed_url = 'https://www.youtube.com/embed/%s' % video_id
        return render_to_string(
            'portals/widgets/youtube.html', {'youtube_embed_url': youtube_embed_url}
        )


register_widget(YouTubeWidget())


class ProblemTableWidget(object):
    name = 'problem_table'
    compiled_tag_regex = re.compile(
        r'\[\['  # [[
        # ProblemTable|... or ProblemTable:<Header>|...
        r'ProblemTable(:.*)?\|(.*)'
        r'\]\](?!\])'  # ]]
    )

    @staticmethod
    def site_key_from_link(link):
        if '//' in link:
            link = link.split('//')[1]
        if '/' not in link:
            return None
        rel_path = '/' + link.split('/', 1)[1]
        try:
            resolved = resolve(rel_path)
        except Http404:
            return None
        if 'site_key' not in resolved.kwargs:
            return None
        return resolved.kwargs['site_key']

    @staticmethod
    def parse_problems(m):
        links = [link.strip() for link in m.group(2).split(';') if link.strip()]
        keys = [
            ProblemTableWidget.site_key_from_link(link)
            for link in links
            if ProblemTableWidget.site_key_from_link(link) is not None
        ]
        problems = (
            Problem.objects.filter(problemsite__url_key__in=keys)
            .select_related('problemsite')
            .prefetch_related('names')
        )
        problem_map = {pr.problemsite.url_key: pr for pr in problems}
        problems = [problem_map[key] for key in keys if key in problem_map]
        return problems

    def get_problem_ids(self, m):
        return [problem.id for problem in self.parse_problems(m)]

    def render(self, request, m):
        if not m.group(2).strip(' ;'):
            return ''

        problems = self.parse_problems(m)

        rows = []

        for problem in problems:
            row = {
                'url': reverse(
                    'problem_site', kwargs={'site_key': problem.problemsite.url_key}
                ),
                'name': problem.name,
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
                row_['score'] = str(result.score.to_int())
                row_['submission_url'] = reverse(
                    'submission',
                    kwargs={'submission_id': result.submission_report.submission_id},
                )
                return True

            row['score_exists'] = fill_row_with_score(row, problem)
            rows.append(row)

        header = _("Problem Name")
        if m.group(1):
            header = m.group(1)[1:]

        return render_to_string(
            'portals/widgets/problem-table.html', {'problems': rows, 'header': header}
        )


register_widget(ProblemTableWidget())


class RedirectWidget(object):
    name = 'redirect'
    compiled_tag_regex = re.compile(
        r'\[\[' r'Redirect\|(.*)' r'\]\]'  # [[  # Redirect|<url>  # ]]
    )

    @staticmethod
    def render(request, match):
        redirect_url = match.group(1).strip()
        if urllib.parse.urlparse(redirect_url).netloc:
            return "[[Redirect: only relative URLs allowed]]"

        return render_to_string(
            'portals/widgets/redirect.html',
            {'redirect_url': redirect_url, 'is_portal_admin': is_portal_admin(request)},
        )


register_widget(RedirectWidget())
