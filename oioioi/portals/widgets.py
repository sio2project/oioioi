import re

from mistune import Renderer, InlineGrammar, InlineLexer, Markdown, BlockLexer
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from oioioi.contests.utils import visible_contests
from oioioi.contests.processors import recent_contests
from oioioi.teachers.models import Teacher


REGISTERED_WIDGETS = []


class PortalInlineGrammar(InlineGrammar):
    pass


class PortalRenderer(Renderer):
    def block_center(self, text):
        return render_to_string('portals/widgets/block_center.html',
                                {'content': mark_safe(text)})


class PortalInlineLexer(InlineLexer):
    default_rules = InlineLexer.default_rules[:]

    def __init__(self, request, renderer, rules=None, **kwargs):
        self.request = request
        if rules is None:
            rules = PortalInlineGrammar()
        super(PortalInlineLexer, self).__init__(renderer, rules, **kwargs)


class PortalBlockLexer(BlockLexer):
    def __init__(self, *args, **kwargs):
        super(PortalBlockLexer, self).__init__(*args, **kwargs)
        self.rules.block_center = re.compile(r'^ *->(.*?)<-', re.DOTALL)
        # Insert before 'block_code'
        if 'block_center' not in self.default_rules:
            self.default_rules.insert(self.default_rules.index('block_code'),
                                      'block_center')

    def parse_block_center(self, m):
        self.tokens.append({
            'type': 'block_center',
            'text': m.group(1),
        })


class PortalMarkdown(Markdown):
    def __init__(self, request):
        renderer = PortalRenderer(escape=True)
        inline_lexer = PortalInlineLexer(request, renderer)
        block_lexer = PortalBlockLexer()
        super(PortalMarkdown, self).__init__(renderer, inline=inline_lexer,
                                             block=block_lexer)

    def output_block_center(self):
        return self.renderer.block_center(self.inline(self.token['text']))


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
        raise ValueError('Inline tag for widget named %s has already been '
                         'registered.' % widget.name)
    PortalInlineLexer.default_rules.insert(0, widget.name)
    setattr(PortalInlineGrammar, widget.name, widget.compiled_tag_regex)

    def func(self, m):
        return widget.render(self.request, m)
    setattr(PortalInlineLexer, 'output_' + widget.name, func)

    REGISTERED_WIDGETS.append(widget)


class YouTubeWidget(object):
    name = 'youtube'
    compiled_tag_regex = re.compile(
        r'\[\['                   # [[
        r'YouTube\|([\s\S]+?)'   # YouTube|<url>
        r'\]\](?!\])'             # ]]
    )

    def render(self, request, m):
        youtube_url = m.group(1).split('|')[-1].strip()
        # We must use the embed player, so if user just copies link
        # from the browser when he is on YT, we must transform
        # the link in order to be able to play the movie
        youtube_url = youtube_url.replace('watch?v=', 'embed/')
        return render_to_string('portals/widgets/youtube.html',
                                {'youtube_url': youtube_url})
register_widget(YouTubeWidget())


class ProblemTableWidget(object):
    name = 'problem_table'
    compiled_tag_regex = re.compile(
        r'\[\['                   # [[
        r'ProblemTable\|(;?[0-9]+(;[0-9]+)*;?)'   # ProblemTable|id1;id2;..
        r'\]\](?!\])'             # ]]
    )

    def get_problem_ids(self, m):
        ids_str = m.group(1).split('|')[-1].strip(' ;')
        return ids_str.split(';') if ids_str else []

    def render(self, request, m):
        problem_ids = self.get_problem_ids(m)
        return render_to_string('portals/widgets/problem_table.html',
                                {'problem_ids': problem_ids})
register_widget(ProblemTableWidget())


class ContestSelectionWidget(object):
    name = 'contest_selection'
    compiled_tag_regex = re.compile(r'\[\[ContestSelection\]\]')
    TO_SHOW = 9

    def render(self, request, m):
        contests = list(visible_contests(request)[:self.TO_SHOW])
        rcontests = recent_contests(request)
        contests = rcontests + [c for c in contests if c not in rcontests]

        default_contest = None
        if rcontests:
            default_contest = rcontests[0]
        elif contests:
            default_contest = contests[0]

        context = {
            'contests': contests[:self.TO_SHOW-1],
            'default_contest': default_contest,
            'more_contests': len(contests) > self.TO_SHOW-1,
            'is_teacher': request.user.has_perm('teachers.teacher'),
            'is_inactive_teacher': request.user.is_authenticated() and
                    bool(Teacher.objects.filter(user=request.user,
                         is_active=False)),
        }
        return render_to_string('portals/widgets/contest_selection.html',
                                RequestContext(request, context))
register_widget(ContestSelectionWidget())
