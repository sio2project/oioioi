from django import template
from django.template import Node, Variable
from django.utils.translation import gettext_lazy as _

from oioioi.contests.templatetags.get_user_name import _get_name
from oioioi.forum.utils import is_forum_moderator

register = template.Library()


class BadgeNode(Node):
    '''
    Returns a badge for a user if they are a moderator.
    '''

    def __init__(self, target_user, asvar):
        self.target_user = Variable(target_user)
        self.asvar = asvar

    def render(self, context):
        user = self.target_user.resolve(context)
        if is_forum_moderator(context['request'], user):
            badge = _(" (moderator)")
        else:
            badge = ""

        if self.asvar:
            context[self.asvar] = str(badge)
            return ""
        else:
            return str(badge)


@register.tag
def user_badge(parser, token):
    (user, asvar) = _get_name(parser, token, "user_badge")
    return BadgeNode(user, asvar)
