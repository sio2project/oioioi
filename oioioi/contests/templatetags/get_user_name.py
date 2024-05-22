from django import template
from django.template import Node, TemplateSyntaxError, Variable
from django.template.loader import render_to_string

from oioioi.base.utils import get_user_display_name
from oioioi.contests.utils import can_see_personal_data, is_contest_basicadmin
from oioioi.forum.utils import is_forum_moderator
from django.utils.translation import gettext_lazy as _

register = template.Library()


class UserInfoLinkNode(Node):
    def __init__(self, target_user, asvar):
        self.target_user = Variable(target_user)
        self.asvar = asvar

    def _get_user_name(self, context, user):
        raise NotImplementedError

    def render(self, context):
        is_admin = context.get('is_admin', False) or is_contest_basicadmin(
            context['request']
        )
        personal_data = can_see_personal_data(context['request'])
        url = render_to_string(
            'contests/user_info_link.html',
            {
                'ctx': context,
                'target_user': self.target_user.resolve(context),
                'target_name': self._get_user_name(
                    context, self.target_user.resolve(context)
                ),
                'is_admin': is_admin,
                'can_see_personal_data': personal_data,
            },
        )

        if self.asvar:
            context[self.asvar] = url
            return ''
        else:
            return url


class PublicNameUserInfoLinkNode(UserInfoLinkNode):
    def _get_user_name(self, context, user):
        return context['request'].contest.controller.get_user_public_name(
            context['request'], user
        )


class FullNameUserInfoLinkNode(UserInfoLinkNode):
    def _get_user_name(self, context, user):
        return get_user_display_name(user)


def _get_name(parser, token, tag_name):
    bits = token.split_contents()
    if (len(bits) != 4 or bits[2] != 'as') and (len(bits) != 2):
        raise TemplateSyntaxError(
            "The tag should look like this: "
            "{%% %s <user_object>[ as <variable>] %%}" % tag_name
        )
    asvar = None
    if len(bits) == 4:
        asvar = bits[3]

    return (bits[1], asvar)


@register.tag
def public_name(parser, token):
    (user, asvar) = _get_name(parser, token, "public_name")
    return PublicNameUserInfoLinkNode(user, asvar)


@register.tag
def full_name(parser, token):
    (user, asvar) = _get_name(parser, token, "full_name")
    return FullNameUserInfoLinkNode(user, asvar)


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
