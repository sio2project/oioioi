from mistune import Renderer, InlineGrammar, InlineLexer, Markdown
from django.template.loader import render_to_string
import re


REGISTERED_WIDGETS = []


class PortalInlineGrammar(InlineGrammar):
    pass


class PortalRenderer(Renderer):
    pass


class PortalInlineLexer(InlineLexer):
    default_rules = InlineLexer.default_rules[:]

    def __init__(self, request, renderer, rules=None, **kwargs):
        self.request = request
        if rules is None:
            rules = PortalInlineGrammar()
        super(PortalInlineLexer, self).__init__(renderer, rules, **kwargs)


def render_panel(request, panel):
    renderer = PortalRenderer(escape=True)
    inline_lexer = PortalInlineLexer(request, renderer)
    portal_markdown = Markdown(renderer, inline=inline_lexer)
    return portal_markdown.render(panel)


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
        return render_to_string('portals/widgets/youtube.html',
                                {'youtube_url': youtube_url})


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


register_widget(YouTubeWidget())
register_widget(ProblemTableWidget())
