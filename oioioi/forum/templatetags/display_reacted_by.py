from django import template
from django.conf import settings
from django.utils.translation import gettext as _

from oioioi.base.utils import get_user_display_name
from oioioi.forum.models import POST_REACTION_TO_COUNT_ATTR, POST_REACTION_TO_PREFETCH_ATTR

register = template.Library()


@register.simple_tag(takes_context=True)
def display_reacted_by(context, post, rtype):
    if rtype not in POST_REACTION_TO_PREFETCH_ATTR:
        raise ValueError("Invalid reaction type in template:" + rtype)

    request = context.get("request")
    if request and hasattr(request, "contest"):

        def get_name(user):
            return request.contest.controller.get_user_public_name(request, user)
    else:
        get_name = get_user_display_name

    output = ", ".join([get_name(reaction.author) for reaction in getattr(post, POST_REACTION_TO_PREFETCH_ATTR[rtype])])

    count = getattr(post, POST_REACTION_TO_COUNT_ATTR[rtype])
    max_count = getattr(settings, "FORUM_REACTIONS_TO_DISPLAY", 10)

    if count > max_count:
        output += " " + _("and others.")

    return output
