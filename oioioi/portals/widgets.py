import re

import urllib.parse
from django.conf import settings
from django.http import Http404
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from mistune import BlockParser, InlineParser, HTMLRenderer, Markdown
from mistune.plugins import PLUGINS

from oioioi.contests.models import UserResultForProblem
from oioioi.portals.conditions import is_portal_admin
from oioioi.problems.models import Problem

REGISTERED_WIDGETS = set()
_block_spoiler_leading_pattern = re.compile(r'^ *>! ?', flags=re.M)


def plugin_portal(md: Markdown, request):
    BLOCK_SPOILER_MAX_DEPTH = 6

    def parse_block_center(block, m, state):
        return {
            'type': 'block_center',
            'text': m.group(1),
        }

    def parse_block_spoiler(block: BlockParser, m, state):
        block._blockspoiler_depth += 1

        if block._blockspoiler_depth > BLOCK_SPOILER_MAX_DEPTH:
            return block.parse_text(m, state)
        else:
            content = _block_spoiler_leading_pattern.sub('', m.group(2))
            content_parsed = block.parse(content, state)
            content_parsed.insert(0, {'type': 'block_spoiler', 'summary': m.group(1)})
            content_parsed.append({'type': 'block_spoiler_end'})
            block._blockspoiler_depth -= 1
            return {
                'type': 'block_spoiler',
                'children': content_parsed,
                'params': (m.group(1),)
            }

    def render_block_center(text):
        return render_to_string(
            'portals/widgets/block-center.html', {'content': mark_safe(text)}
        )

    def render_block_spoiler(text, summary):
        return render_to_string(
            'portals/widgets/block-spoiler.html',
            {'summary': summary, 'body': mark_safe(text)},
        )

    # Ugly hack incoming: next 3 methods
    # Although ugly, it is correct
    def render_table(self, content):
        """Rendering table element. Wrap header and body in it.

        :param header: header part of the table.
        :param body: body part of the table.
        """
        header, body = content
        return render_to_string(
            'portals/widgets/table.html',
            {'header': mark_safe(header), 'body': mark_safe(body)},
        )

    def render_table_body(text):
        return (text,)

    def render_table_head(text):
        return (text,)

    md.block.register_rule(
        'block_center',
        r'^ *->(.*?)<-',
        parse_block_center
    )
    md.block.rules.insert(
        md.block.rules.index('block_code'),
        'block_center'
    )
    md.block.register_rule(
        'block_spoiler'
        r'^ *>!\[([^\n]*)\] *((?:\n *>![^\n]*)+)',
        parse_block_spoiler
    )
    md.block.rules.insert(0, 'block_spoiler')

    renderer: HTMLRenderer = md.renderer
    renderer.register('block_center', render_block_center)
    renderer.register('block_spoiler', render_block_spoiler)
    # Override table rendering
    renderer.register('table', render_table)
    renderer.register('table_body', render_table_body)
    renderer.register('table_head', render_table_head)

    for widget in REGISTERED_WIDGETS:
        def parse_func(inline: InlineParser, m, state):
            return 'block_text', widget.render(request, m)

        md.inline.register_rule(widget.name, widget.compiled_tag_regex.pattern,
                                parse_func)



def render_panel(request, panel):
    return Markdown(HTMLRenderer(), plugins=[
        # Standard plugins
        PLUGINS['strikethrough'],
        PLUGINS['footnotes'],
        PLUGINS['table'],

        # Custom plugins
        lambda md: plugin_portal(md, request),
    ]).render(panel)


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
    if widget in REGISTERED_WIDGETS:
        raise ValueError(
            'Inline tag for widget named %s has already been '
            'registered.' % widget.name
        )

    REGISTERED_WIDGETS.add(widget)


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
                    kwargs={'submission_id': result.submission_report.submission.id},
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
